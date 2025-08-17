#!/usr/bin/env python3
"""
Binary Format Handler

This script reads a custom binary format definition from JSON and provides
serialization/deserialization between JSON data and binary files.

Supports:
- Basic numeric types (int8, int16, int32, int64, uint8, uint16, uint32, uint64, float32, float64)
- Arrays with fixed or variable length
- Nested structures
- String types with encoding support
"""

import json
import struct
import os
import io
import crcmod
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union, BinaryIO
from dataclasses import dataclass



class BinaryFormatError(Exception):
    """Custom exception for binary format errors."""
    pass


@dataclass
class FieldDefinition:
    """Represents a field definition from the format specification."""
    name: str
    type: str
    size: int = None
    encoding: str = 'utf-8'
    length_field: str = None  # For variable-length arrays
    fields: List['FieldDefinition'] = None  # For nested structures
    condition: str = None  # Condition for optional fields
    function: str = None  # Function to calculate field value (e.g., "crc32")
    function_scope: str = None  # Scope for function calculation
    function_scope_start: str = None  # Starting field for range scope
    function_scope_end: str = None  # Ending field for range scope
    function_parameters: Dict[str, Any] = None  # Parameters for the function
    discriminator_field:str = None
    union_variants: Dict[str,List[Dict[str,Any]]] = None

class ScopeResolver:
    """Resolves different types of scopes for calculated fields."""
    
    def __init__(self, field_offsets: Dict[str, int], field_sizes: Dict[str, int]):
        self.field_offsets = field_offsets
        self.field_sizes = field_sizes
    
    def get_scope_data(self, data: bytes, scope_type: str, 
                      scope_start: str = None, scope_end: str = None,
                      current_offset: int = 0) -> bytes:
        """Get data based on scope definition."""
        
        if scope_type == "all_previous":
            return data[:current_offset]
        
        elif scope_type == "entire_file":
            return data
        
        elif scope_type == "from_start":
            return data[:current_offset]
        
        elif scope_type == "field_range":
            if not scope_start or not scope_end:
                raise BinaryFormatError("field_range scope requires both scope_start and scope_end")
            
            start_offset = self.field_offsets.get(scope_start)
            end_offset = self.field_offsets.get(scope_end)
            
            if start_offset is None:
                raise BinaryFormatError(f"Start field '{scope_start}' not found")
            if end_offset is None:
                raise BinaryFormatError(f"End field '{scope_end}' not found")
            
            # Include the end field in the range
            end_field_size = self.field_sizes.get(scope_end, 0)
            return data[start_offset:end_offset + end_field_size]
        
        elif scope_type == "from_field":
            if not scope_start:
                raise BinaryFormatError("from_field scope requires scope_start")
            
            start_offset = self.field_offsets.get(scope_start)
            if start_offset is None:
                raise BinaryFormatError(f"Start field '{scope_start}' not found")
            
            return data[start_offset:current_offset]
        
        elif scope_type == "to_field":
            if not scope_end:
                raise BinaryFormatError("to_field scope requires scope_end")
            
            end_offset = self.field_offsets.get(scope_end)
            if end_offset is None:
                raise BinaryFormatError(f"End field '{scope_end}' not found")
            
            # Include the end field
            end_field_size = self.field_sizes.get(scope_end, 0)
            return data[:end_offset + end_field_size]
        
        elif scope_type == "after_field":
            if not scope_start:
                raise BinaryFormatError("after_field scope requires scope_start")
            
            start_offset = self.field_offsets.get(scope_start)
            start_field_size = self.field_sizes.get(scope_start, 0)
            
            if start_offset is None:
                raise BinaryFormatError(f"Start field '{scope_start}' not found")
            
            return data[start_offset + start_field_size:current_offset]
        
        elif scope_type == "last_n_bytes":
            # Get last N bytes before current position
            n_bytes = int(scope_start) if scope_start else 100
            start_pos = max(0, current_offset - n_bytes)
            return data[start_pos:current_offset]
        
        elif scope_type == "specific_bytes":
            # Get specific byte range: "start:end" format in scope_start
            if not scope_start:
                raise BinaryFormatError("specific_bytes scope requires range in scope_start (format: start:end)")
            
            try:
                if ':' in scope_start:
                    start_byte, end_byte = map(int, scope_start.split(':'))
                    return data[start_byte:end_byte]
                else:
                    # Single byte position
                    byte_pos = int(scope_start)
                    return data[byte_pos:byte_pos + 1]
            except ValueError:
                raise BinaryFormatError(f"Invalid byte range format: {scope_start}")
        
        else:
            raise BinaryFormatError(f"Unknown scope type: {scope_type}")


class BinaryFormatHandler:
    """Handles serialization and deserialization of custom binary formats."""
    
    # Type mapping for struct format strings
    TYPE_MAP = {
        'int8': 'b',
        'uint8': 'B',
        'int16': 'h',
        'uint16': 'H',
        'int32': 'i',
        'uint32': 'I',
        'int64': 'q',
        'uint64': 'Q',
        'float32': 'f',
        'float64': 'd',
        'char': 'c'
    }
    
    def __init__(self, format_source: Union[str, Dict[str, Any]]):
        """
        Initialize the handler with a format definition.
        
        Args:
            format_source: Can be one of:
                - Path to JSON file containing format definition
                - JSON string containing format definition
                - Dictionary containing format definition
        """
        self.format_json_dict = self._load_format_definition(format_source)
        self.endianness = self.format_json_dict.get('endianness', 'little')
        self.endian_char = '<' if self.endianness == 'little' else '>'
        self.calculated_fields: List[FieldDefinition] = []
        self.field_offsets: Dict[str, int] = {}
        self.field_sizes: Dict[str, int] = {}
        self.scope_resolver = None
        
    def _load_format_definition(self, format_source: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Load and validate format definition from various sources."""
        try:
            # If it's already a dictionary, use it directly
            if isinstance(format_source, dict):
                format_def = format_source
            elif isinstance(format_source, str):
                # Check if it's a JSON string or file path
                format_source = format_source.strip()
                if format_source.startswith('{') and format_source.endswith('}'):
                    # It's a JSON string
                    format_def = json.loads(format_source)
                else:
                    # It's a file path
                    with open(format_source, 'r', encoding='utf-8') as f:
                        format_def = json.load(f)
            else:
                raise BinaryFormatError(f"Unsupported format_source type: {type(format_source)}")
            
            # Validate the format definition
            if 'fields' not in format_def:
                raise BinaryFormatError("Format definition must contain 'fields' key")
                
            return format_def
            
        except FileNotFoundError:
            raise BinaryFormatError(f"Format file not found: {format_source}")
        except json.JSONDecodeError as e:
            raise BinaryFormatError(f"Invalid JSON in format definition: {e}")
        except Exception as e:
            raise BinaryFormatError(f"Error loading format definition: {e}")
    
    def _parse_field_definition(self, field_def: Dict[str, Any]) -> FieldDefinition:
        """Parse a field definition from the JSON format."""
        field = FieldDefinition(
            name=field_def['name'],
            type=field_def['type'],
            size=field_def.get('size'),
            encoding=field_def.get('encoding', 'utf-8'),
            length_field=field_def.get('length_field'),
            fields=None,
            condition=field_def.get('condition'),
            function=field_def.get('function'),
            function_scope=field_def.get('function_scope', 'all_previous'),
            function_scope_start=field_def.get('function_scope_start'),
            function_scope_end=field_def.get('function_scope_end'),
            function_parameters=field_def.get('function_parameters', {}),
            discriminator_field=field_def.get('discriminator_field'),
            union_variants=field_def.get('union_variants', {})
        )
        
        # Handle nested structures
        if field.type == 'struct' and 'fields' in field_def:
            field.fields = [self._parse_field_definition(f) for f in field_def['fields']]
        elif field.type == 'array' and 'element_type' in field_def:
            # For arrays, create a virtual field representing the element type
            element_def = {
                'name': '#',
                'type': field_def['element_type']
            }
            if 'element_fields' in field_def:
                element_def['fields'] = field_def['element_fields']
            if 'discriminator_field' in field_def:
                element_def['discriminator_field'] = field_def['discriminator_field']
            if 'union_variants' in field_def:
                element_def['union_variants'] = field_def['union_variants']
                
            
            field.fields = [self._parse_field_definition(element_def)]
            
        elif field.type == 'union':
            parsed_variants = {}
            for variant_key, variant_fields in field.union_variants.items():
                parsed_variants[variant_key] = [self._parse_field_definition(f) for f in variant_fields]
        return field
    
    

    def serialize_to_binary(self, data: Dict[str, Any], output_file: str = None) -> bytes:
        try:
            buffer = io.BytesIO()
            self._serialize_phase1(buffer, self.format_json_dict['fields'], data)
            
            # Initialize scope resolver with collected offsets
            self.scope_resolver = ScopeResolver(self.field_offsets, self.field_sizes)
            
            # Phase 2: Calculate and update calculated fields
            final_data = self._serialize_phase2(buffer.getvalue(), data)
            
            # Write final data
            if output_file is not None:
                with open(output_file, 'wb') as f:
                    f.write(final_data)            

            return final_data
        
        except Exception as e:
            raise BinaryFormatError(f"Serialization failed: {e}")
        
    def _serialize_phase1(self, f: BinaryIO, field_defs: List[Dict[str, Any]], context: Dict[str, Any]) -> None:
        """Phase 1: Serialize structure with placeholders."""
        for field_def in field_defs:
            field = self._parse_field_definition(field_def)
 
            # Check conditions
            if field.condition is not None and not eval(field.condition, {}, {'context': context, 'data': context}):
                continue
            
            if field.name not in context:
                raise BinaryFormatError(f"Missing field in data: {field.name}")
            if field.type not in self.TYPE_MAP and field.type not in ['uint24','int24','string', 'array', 'struct','union']:
                raise BinaryFormatError(f"Unsupported field type: {field.type}")

            value = context[field.name]
            start_offset = f.tell()
            self.field_offsets[field.name] = start_offset
            
            # Handle calculated fields
            if field.function and value == "auto":
                self.calculated_fields.append(field)
                format_str = self.endian_char + self.TYPE_MAP[field.type]
                f.write(struct.pack(format_str, 0))
                self.field_sizes[field.name] = struct.calcsize(format_str)
            # Regular field serialization
            else:
                value = context[field.name]
                self._serialize_field(f, field, value, context)
                # Record field size
                end_offset = f.tell()
                self.field_sizes[field.name] = end_offset - start_offset

    def _serialize_phase2(self, data: bytes, context: Dict[str, Any]) -> bytes:
        """Phase 2: Calculate and update calculated fields."""
        data_array = bytearray(data)
        
        for field in self.calculated_fields:
            offset = self.field_offsets.get(field.name)
            if offset is None:
                continue
            
            # Get scope data based on field definition
            scope_data = self.scope_resolver.get_scope_data(
                data, 
                field.function_scope or "all_previous",
                field.function_scope_start,
                field.function_scope_end,
                offset
            )
            
            # Calculate value based on function
            value = self._calculate_function_value(field, scope_data, context)
            
            # Update the data
            if field.type in self.TYPE_MAP:
                format_str = self.endian_char + self.TYPE_MAP[field.type]
                struct.pack_into(format_str, data_array, offset, value)
        
        return bytes(data_array)
    
    def _calculate_function_value(self, field: FieldDefinition, data: bytes, context: Dict[str, Any]) -> Any:
        """Calculate function value with parameters."""
        params = field.function_parameters or {}
        
        if field.function == "crc32":
            polynomial = params.get('polynomial', 0x104C11DB7)  # CRC-32 polynomial
            initial_value = params.get('initial_value', 0xFFFFFFFF)
            reverse = params.get('reverse', True)
            xor_out = params.get('xor_out', 0xFFFFFFFF)
            
            # Create CRC function using crcmod
            crc_func = crcmod.mkCrcFun(polynomial, initCrc=initial_value, rev=reverse, xorOut=xor_out)
            return crc_func(data)
        elif field.function == "crc16":
            # Enhanced CRC16 with configurable parameters
            polynomial = params.get('polynomial', 0x18005)  # CRC-16-CCITT polynomial
            initial_value = params.get('initial_value', 0xFFFF)
            reverse = params.get('reverse', True)
            xor_out = params.get('xor_out', 0x0000)
            
            # Create CRC function using crcmod
            crc_func = crcmod.mkCrcFun(polynomial, initCrc=initial_value, rev=reverse, xorOut=xor_out)
            return crc_func(data)
        elif field.function == "count":
            key = params.get("key", "")
            if not key:
                return 0
            list_to_count = context.get(key, [])
            if not isinstance(list_to_count, list):
                return 0
            return len(list_to_count)

        elif field.function == "length":
            offset = params.get('offset', 0)
            multiplier = params.get('multiplier', 1)
            return (len(data) * multiplier) + offset
        
        elif field.function == "file_size":
            # Get total file size including this field
            total_size = len(data) + self.field_sizes.get(field.name, 0)
            return total_size
        
        else:
            raise BinaryFormatError(f"Unknown function: {field.function}")

    def _serialize_fields(self, f: BinaryIO, fields: List[FieldDefinition], data: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Serialize a list of fields to binary stream."""
        for field in fields:
            # Check if field should be included based on condition
            if field.condition is not None:
                pass
            if field.condition and not eval(field.condition, {}, {'context': context,'data': data}):
                continue
            
            # Skip functional fields in simple serialization - they should use two-phase
            if field.function:
                # Write placeholder for functional fields
                if field.type in self.TYPE_MAP:
                    format_str = self.endian_char + self.TYPE_MAP[field.type]
                    f.write(struct.pack(format_str, 0))
                continue
                
            if field.name not in data:
                raise BinaryFormatError(f"Missing field in data: {field.name}")
                
            value = data[field.name]
            self._serialize_field(f, field, value, context)
    
    def _serialize_field(self, f: BinaryIO, field: FieldDefinition, value: Any, context: Dict[str, Any]) -> None:
        """Serialize a single field to binary stream."""
        if field.type in self.TYPE_MAP:
            # Basic numeric type
            format_str = self.endian_char + self.TYPE_MAP[field.type]
            f.write(struct.pack(format_str, value))
        elif field.type == 'int24':
            if not (-8388608 <= value <= 8388607):
                raise BinaryFormatError(f"Value out of range for int24: {value}")
            packed = struct.pack(self.endian_char + 'i', value)[0:3]
            f.write(packed)
        elif field.type == 'string':
            # String type
            encoded = value.encode(field.encoding)
            if field.size:
                # Fixed-size string
                encoded = encoded[:field.size].ljust(field.size, b'\x00')
                f.write(encoded)
            else:
                # Variable-size string (write length first)
                length_format = self.endian_char + 'I'
                f.write(struct.pack(length_format, len(encoded)))
                f.write(encoded)
                
        elif field.type == 'array':
            # Array type
            if not isinstance(value, list):
                raise BinaryFormatError(f"Expected list for array field {field.name}")
                
            # Write array length if not fixed
            if field.length_field:
                # Length is determined by another field (support dot notation)
                array_length = eval(field.length_field, {}, {'context': context})
                if array_length is None:
                    raise BinaryFormatError(f"Length field {field.length_field} not found for array {field.name}")
            elif field.size:
                if(field.size < 0):
                    array_length = len(value)
                else:
                    array_length = field.size
            else:
                raise BinaryFormatError(f"Array field {field.name} must have either size or length_field defined")
            
            # Serialize array elements
            element_fields = field.fields[0] if field.fields else None
            for i in range(array_length):
                if i < len(value):
                    self._serialize_field(f, element_fields, value[i], context)
                else:
                    # Pad with zeros for fixed-size arrays
                    self._serialize_field(f, element_fields, 0, context)
                    
        elif field.type == 'struct':
            # Nested structure
            if not isinstance(value, dict):
                raise BinaryFormatError(f"Expected dict for struct field {field.name}")
            self._serialize_fields(f, field.fields, value, context)
        elif field.type == 'union':
            if not isinstance(value,dict):
                raise BinaryFormatError(f"Expected dict for union field {field.name}")
            discriminator_value = self._get_nested_value(context, field.discriminator_field)
            if discriminator_value is None:
                raise BinaryFormatError(f"Discriminator field '{field.discriminator_field}' not found for union {field.name}")
            variant_key = str(discriminator_value)
            if variant_key not in field.union_variants:
                raise BinaryFormatError(f"Unknown union variant '{variant_key}' for field {field.name}")
            variant_fields = field.union_variants[variant_key]
            self._serialize_fields(f,variant_fields,value,context)
            
        else:
            raise BinaryFormatError(f"Unsupported field type: {field.type}")
    
    def deserialize_from_binary(self, input_source: Union[str, bytes]) -> Dict[str, Any]:
        """
        Deserialize binary data to JSON data according to format definition.
        
        Args:
            input_source: Can be one of:
                - Path to binary file
                - Bytes object containing binary data
            
        Returns:
            Dictionary containing the deserialized data
        """
        try:
            if isinstance(input_source, str):
                # File path
                with open(input_source, 'rb') as f:
                    fields = [self._parse_field_definition(field_def) for field_def in self.format_json_dict['fields']]
                    result = {}
                    self._deserialize_fields(f, fields, result, '')
                    return result
            elif isinstance(input_source, (bytes, bytearray)):
                # Bytes object
                with io.BytesIO(input_source) as f:
                    fields = [self._parse_field_definition(field_def) for field_def in self.format_json_dict['fields']]
                    result = {}
                    self._deserialize_fields(f, fields, result, '')
                    return result
            else:
                raise BinaryFormatError(f"Unsupported input_source type: {type(input_source)}. Must be str (file path) or bytes.")
                
        except Exception as e:
            raise BinaryFormatError(f"Deserialization failed: {e}")
    
    def _deserialize_fields(self, f: BinaryIO, fields: List[FieldDefinition], context:Dict[str,Any]=None,path: str = '') -> Dict[str, Any]:
        """Deserialize a list of fields from binary stream."""
        for field in fields:
            # Check if field should be included based on condition
            if field.condition is not None:
                pass
            data = self._get_nested_value(context, path)
            if field.condition and not eval(field.condition,{}, {'context': context,'data': data}):
                continue
            self._deserialize_field(f, field, context,path)
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get a value from nested dictionary using dot notation."""
        parts = path.split('.')
        parts = [part.strip() for part in parts if part.strip()]  # Remove empty parts
        value = data
        for part in parts:
            if '[' in part and part.endswith(']'):
                field_name = part[:part.index('[')]
                index_part = part[part.index('[')+1:-1]
                if isinstance(value,dict) and field_name in value:
                    array_value = value[field_name]
                else:
                    return None
                
                if not isinstance(array_value, list):
                    return None
                
                index = int(index_part)
                try:
                    value = array_value[index]
                except IndexError:
                    value = None

            else:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
        return value

    def _write_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set a value in a nested dictionary using dot notation."""
        parts = path.split('.')
        parts = [part for part in parts if part]  # Remove empty parts
        current = data
        for i,part in enumerate(parts):
            if '[' in part and part.endswith(']'):
                field_name = part[:part.index('[')]
                index_part = part[part.index('[')+1:-1]
                if field_name not in current or not isinstance(current[field_name], list):
                    current[field_name] = []
                    
                index = int(index_part)
                if i == len(parts) - 1:
                    while len(current[field_name]) <= index:
                        current[field_name].append(None)
                    current[field_name][index] = value
                    return
                else:
                    while len(current[field_name]) <= index:
                        current[field_name].append({})
                    current = current[field_name][index]
            else:
                if i == len(parts) - 1:
                    current[part] = value
                    return
                if part not in current or not isinstance(current[part], dict):
                    current[part] = {}
                current = current[part]
        
    
    def _deserialize_field(self, f: BinaryIO, field: FieldDefinition, context: Dict[str, Any], path: str = '') -> Any:
        """Deserialize a single field from binary stream."""
        if field.type in self.TYPE_MAP:
            # Basic numeric type
            if field.name != '#':
                path += field.name
            format_str = self.endian_char + self.TYPE_MAP[field.type]
            size = struct.calcsize(format_str)
            data = f.read(size)
            if len(data) < size:
                raise BinaryFormatError(f"Unexpected end of file reading {field.name}")
            result = struct.unpack(format_str, data)[0]
            self._write_nested_value(context, path, result)
            
        elif field.type == 'int24':
            # Read 3 bytes for int24
            path += field.name
            data = f.read(3)
            if len(data) < 3:
                raise BinaryFormatError(f"Unexpected end of file reading {field.name}")
            
            result =  struct.unpack(self.endian_char + 'i', data + b'\x00')[0]
            self._write_nested_value(context, path, result)
            
        elif field.type == 'uint24':
            # Read 3 bytes for uint24
            path += field.name
            data = f.read(3)
            if len(data) < 3:
                raise BinaryFormatError(f"Unexpected end of file reading {field.name}")
            result = struct.unpack(self.endian_char + 'I', data + b'\x00')[0]
            self._write_nested_value(context, path, result)
            
        elif field.type == 'string':
            # String type
            path += field.name
            if field.size:
                # Fixed-size string
                data = f.read(field.size)
                if len(data) < field.size:
                    raise BinaryFormatError(f"Unexpected end of file reading {field.name}")
                # Remove null padding
                result = data.rstrip(b'\x00').decode(field.encoding, errors='replace')
                self._write_nested_value(context, path, result)
                
            else:
                # Variable-size string (read length first)
                length_format = self.endian_char + 'I'
                length_size = struct.calcsize(length_format)
                length_data = f.read(length_size)
                if len(length_data) < length_size:
                    raise BinaryFormatError(f"Unexpected end of file reading {field.name} length")
                length = struct.unpack(length_format, length_data)[0]
                
                data = f.read(length)
                if len(data) < length:
                    raise BinaryFormatError(f"Unexpected end of file reading {field.name}")
                result = data.decode(field.encoding, errors='replace')
                self._write_nested_value(context, path, result)
                
        elif field.type == 'array':
            # Array type
            if field.length_field:
                # Length is determined by another field (support dot notation)
                
                array_length = eval(field.length_field, {}, {'context': context})
                if array_length is None:
                    raise BinaryFormatError(f"Length field {field.length_field} not found for array {field.name}")
            elif field.size:
                array_length = field.size
            else:
                raise BinaryFormatError(f"Array field {field.name} must have either size or length_field defined")
            # Deserialize array elements
            element_field = field.fields[0] if field.fields else None
            if array_length >= 0:
                for i in range(array_length):
                    self._deserialize_field(f, element_field, context,path+field.name+f"[{i}]")
            else:
                i = 0
                while True:
                    i += 1
                    try:
                        self._deserialize_field(f, element_field, context, path + field.name + f"[{i}]")
                    except BinaryFormatError:
                        print(f"Warning: Unexpected end of file while reading array {field.name}")
                        print(f"file size: {f.tell()}, real size: {f.seek(0, io.SEEK_END)}")
                        break
        
        elif field.type == 'struct':
            # Nested structure
            if field.name != '#':
                self._deserialize_fields(f, field.fields, context, path + '.' + field.name + '.')
            else:
                self._deserialize_fields(f, field.fields, context, path + '.')
                
        elif field.type == 'union':
            first_key = next(iter(field.union_variants))
            first_union_variant = field.union_variants[first_key]
            discriminator_type = first_union_variant[0].get('type', 'uint8')
            
            if discriminator_type not in self.TYPE_MAP:
                print("Warning: Unsupported discriminator type:", discriminator_type)
                raise BinaryFormatError(f"Unsupported discriminator type: {discriminator_type}")
            discriminator_format = self.endian_char + self.TYPE_MAP[discriminator_type]
            discriminator_size = struct.calcsize(discriminator_format)
            discriminator_data = f.read(discriminator_size)
            if len(discriminator_data) < discriminator_size:
                print("Warning: Unexpected end of file while reading discriminator for union", field.name)
                raise BinaryFormatError(f"Unexpected end of file reading discriminator for union {field.name}")
            discriminator_value = struct.unpack(discriminator_format, discriminator_data)[0]
            f.seek(-discriminator_size, io.SEEK_CUR)  # Rewind to read union variant
            struct_fields = field.union_variants.get(str(discriminator_value), None)
            if struct_fields is None:
                print("Warning: No matching union variant found for discriminator value:", discriminator_value)
                raise BinaryFormatError(f"Unknown union variant '{discriminator_value}' for field {field.name}")
            
            struct_field = self._parse_field_definition({
                'name': field.name,
                'type': 'struct',
                'fields': struct_fields
            })
            if discriminator_value == 51:
                pass
            self._deserialize_field(f, struct_field, context, path)
            
        else:
            print("Warning: Unsupported field type:", field.type)
            raise BinaryFormatError(f"Unsupported field type: {field.type}")
    
def main():
    """Example usage of the BinaryFormatHandler."""
    # Example format definition
    example_format = {
        "endianness": "little",
        "description": "Example binary format with various data types",
        "fields": [
            {
                "name": "header",
                "type": "struct",
                "fields": [
                    {"name": "magic", "type": "uint32"},
                    {"name": "version", "type": "uint16"},
                    {"name": "flags", "type": "uint16"}
                ]
            },
            {
                "name": "name",
                "type": "string",
                "size": 32,
                "encoding": "utf-8"
            },
            {
                "name": "data_count",
                "type": "uint32"
            },
            {
                "name": "data_array",
                "type": "array",
                "length_field": "data_count",
                "element_type": "float32"
            },
            {
                "name": "nested_data",
                "type": "array",
                "size": 2,
                "element_type": "struct",
                "element_fields": [
                    {"name": "id", "type": "uint32"},
                    {"name": "value", "type": "float64"}
                ]
            }
        ]
    }
    
    # Save example format
    with open('example_format.json', 'w') as f:
        json.dump(example_format, f, indent=2)
    
    # Example data
    example_data = {
        "header": {
            "magic": 0x12345678,
            "version": 1,
            "flags": 0x0001
        },
        "name": "Test File",
        "data_count": 3,
        "data_array": [1.0, 2.5, 3.14],
        "nested_data": [
            {"id": 100, "value": 10.5},
            {"id": 200, "value": 20.7}
        ]
    }
    
    # Create handler and test serialization/deserialization
    try:
        handler = BinaryFormatHandler('example_format.json')
        
        # Serialize to binary
        print("Serializing data to binary file...")
        handler.serialize_to_binary(example_data, 'example_data.bin')
        
        # Deserialize from binary
        print("Deserializing data from binary file...")
        restored_data = handler.deserialize_from_binary('example_data.bin')
        
        # Compare results
        print("\nOriginal data:")
        print(json.dumps(example_data, indent=2))
        print("\nRestored data:")
        print(json.dumps(restored_data, indent=2))
        
        # Verify they match
        if example_data == restored_data:
            print("\n✓ Serialization/deserialization successful!")
        else:
            print("\n✗ Data mismatch after round-trip!")
            
    except BinaryFormatError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
