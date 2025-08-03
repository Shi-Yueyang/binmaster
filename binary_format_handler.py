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
import zlib
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


class EnhancedTwoPhaseSerializer:
    """Enhanced two-phase serialization with flexible scoping."""
    
    def __init__(self, handler: 'BinaryFormatHandler'):
        self.handler = handler
        self.calculated_fields: List[FieldDefinition] = []
        self.field_offsets: Dict[str, int] = {}
        self.field_sizes: Dict[str, int] = {}
        self.scope_resolver = None
    
    def serialize(self, data: Dict[str, Any], output_file: str) -> None:
        """Serialize data using enhanced two-phase approach."""
        # Phase 1: Serialize structure with placeholders for calculated fields
        buffer = io.BytesIO()
        self._serialize_phase1(buffer, self.handler.format_definition['fields'], data)
        
        # Initialize scope resolver with collected offsets
        self.scope_resolver = ScopeResolver(self.field_offsets, self.field_sizes)
        
        # Phase 2: Calculate and update calculated fields
        final_data = self._serialize_phase2(buffer.getvalue(), data)
        
        # Write final data
        with open(output_file, 'wb') as f:
            f.write(final_data)
    
    def _serialize_phase1(self, f: BinaryIO, field_defs: List[Dict[str, Any]], data: Dict[str, Any]) -> None:
        """Phase 1: Serialize structure with placeholders."""
        for field_def in field_defs:
            field = self.handler._parse_field_definition(field_def)
            
            # Check conditions
            if not self.handler._evaluate_condition(field.condition, data):
                continue
            
            # Record offset and mark start position
            start_offset = f.tell()
            self.field_offsets[field.name] = start_offset
            
            # Handle calculated fields
            if field.function:
                self.calculated_fields.append(field)
                # Write placeholder
                if field.type in self.handler.TYPE_MAP:
                    format_str = self.handler.endian_char + self.handler.TYPE_MAP[field.type]
                    f.write(struct.pack(format_str, 0))
                    self.field_sizes[field.name] = struct.calcsize(format_str)
                continue
            
            # Regular field serialization
            if field.name in data:
                value = data[field.name]
                self.handler._serialize_field(f, field, value, data)
                # Record field size
                end_offset = f.tell()
                self.field_sizes[field.name] = end_offset - start_offset
            else:
                raise BinaryFormatError(f"Missing field in data: {field.name}")
    
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
            if field.type in self.handler.TYPE_MAP:
                format_str = self.handler.endian_char + self.handler.TYPE_MAP[field.type]
                struct.pack_into(format_str, data_array, offset, value)
        
        return bytes(data_array)
    
    def _calculate_function_value(self, field: FieldDefinition, data: bytes, context: Dict[str, Any]) -> Any:
        """Calculate function value with parameters."""
        params = field.function_parameters or {}
        
        if field.function == "crc32":
            initial_value = params.get('initial_value', 0)
            return zlib.crc32(data, initial_value) & 0xffffffff
        
        elif field.function == "crc16":
            polynomial = params.get('polynomial', 0xA001)
            initial_value = params.get('initial_value', 0xFFFF)
            
            crc = initial_value
            for byte in data:
                crc ^= byte
                for _ in range(8):
                    if crc & 1:
                        crc = (crc >> 1) ^ polynomial
                    else:
                        crc >>= 1
            return crc
        
        elif field.function == "checksum":
            algorithm = params.get('algorithm', 'sum')
            modulo = params.get('modulo', 256)
            
            if algorithm == 'sum':
                return sum(data) % modulo
            elif algorithm == 'xor':
                result = 0
                for byte in data:
                    result ^= byte
                return result % modulo
            else:
                raise BinaryFormatError(f"Unknown checksum algorithm: {algorithm}")
        
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
    
    def __init__(self, format_file: str):
        """
        Initialize the handler with a format definition file.
        
        Args:
            format_file: Path to JSON file containing format definition
        """
        self.format_definition = self._load_format_definition(format_file)
        self.endianness = self.format_definition.get('endianness', 'little')
        self.endian_char = '<' if self.endianness == 'little' else '>'
        
    def _load_format_definition(self, format_file: str) -> Dict[str, Any]:
        """Load and validate format definition from JSON file."""
        try:
            with open(format_file, 'r', encoding='utf-8') as f:
                format_def = json.load(f)
                
            if 'fields' not in format_def:
                raise BinaryFormatError("Format definition must contain 'fields' key")
                
            return format_def
            
        except FileNotFoundError:
            raise BinaryFormatError(f"Format file not found: {format_file}")
        except json.JSONDecodeError as e:
            raise BinaryFormatError(f"Invalid JSON in format file: {e}")
    
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
            function_parameters=field_def.get('function_parameters', {})
        )
        
        # Handle nested structures
        if field.type == 'struct' and 'fields' in field_def:
            field.fields = [self._parse_field_definition(f) for f in field_def['fields']]
        elif field.type == 'array' and 'element_type' in field_def:
            # For arrays, create a virtual field representing the element type
            element_def = {
                'name': 'element',
                'type': field_def['element_type']
            }
            if 'element_fields' in field_def:
                element_def['fields'] = field_def['element_fields']
            field.fields = [self._parse_field_definition(element_def)]
            
        return field
    
    def serialize_to_binary(self, data: Dict[str, Any], output_file: str) -> None:
        """
        Serialize JSON data to binary file according to format definition.
        
        Args:
            data: Dictionary containing the data to serialize
            output_file: Path to output binary file
        """
        try:
            # Check if we have any calculated fields (functions)
            has_calculated_fields = any(
                field_def.get('function') 
                for field_def in self.format_definition['fields']
            )
            
            if has_calculated_fields:
                # Use enhanced two-phase serialization for calculated fields
                serializer = EnhancedTwoPhaseSerializer(self)
                serializer.serialize(data, output_file)
            else:
                # Use simple serialization for non-calculated fields
                with open(output_file, 'wb') as f:
                    fields = [self._parse_field_definition(field_def) 
                             for field_def in self.format_definition['fields']]
                    self._serialize_fields(f, fields, data)
                
        except Exception as e:
            raise BinaryFormatError(f"Serialization failed: {e}")
    
    def _serialize_fields(self, f: BinaryIO, fields: List[FieldDefinition], data: Dict[str, Any]) -> None:
        """Serialize a list of fields to binary stream."""
        for field in fields:
            # Check if field should be included based on condition
            if not self._evaluate_condition(field.condition, data):
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
            self._serialize_field(f, field, value, data)
    
    def _serialize_field(self, f: BinaryIO, field: FieldDefinition, value: Any, context: Dict[str, Any]) -> None:
        """Serialize a single field to binary stream."""
        if field.type in self.TYPE_MAP:
            # Basic numeric type
            format_str = self.endian_char + self.TYPE_MAP[field.type]
            f.write(struct.pack(format_str, value))
            
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
                array_length = self._get_nested_value(context, field.length_field)
                if array_length is None:
                    array_length = len(value)
            elif field.size:
                # Fixed size array
                array_length = field.size
            else:
                # Variable length array - write length first
                length_format = self.endian_char + 'I'
                f.write(struct.pack(length_format, len(value)))
                array_length = len(value)
            
            # Serialize array elements
            element_field = field.fields[0] if field.fields else None
            for i in range(array_length):
                if i < len(value):
                    self._serialize_field(f, element_field, value[i], context)
                else:
                    # Pad with zeros for fixed-size arrays
                    self._serialize_field(f, element_field, 0, context)
                    
        elif field.type == 'struct':
            # Nested structure
            if not isinstance(value, dict):
                raise BinaryFormatError(f"Expected dict for struct field {field.name}")
            self._serialize_fields(f, field.fields, value)
            
        else:
            raise BinaryFormatError(f"Unsupported field type: {field.type}")
    
    def deserialize_from_binary(self, input_file: str) -> Dict[str, Any]:
        """
        Deserialize binary file to JSON data according to format definition.
        
        Args:
            input_file: Path to input binary file
            
        Returns:
            Dictionary containing the deserialized data
        """
        try:
            with open(input_file, 'rb') as f:
                fields = [self._parse_field_definition(field_def) 
                         for field_def in self.format_definition['fields']]
                return self._deserialize_fields(f, fields)
                
        except Exception as e:
            raise BinaryFormatError(f"Deserialization failed: {e}")
    
    def _deserialize_fields(self, f: BinaryIO, fields: List[FieldDefinition]) -> Dict[str, Any]:
        """Deserialize a list of fields from binary stream."""
        result = {}
        for field in fields:
            # Check if field should be included based on condition
            if not self._evaluate_condition(field.condition, result):
                continue
                
            result[field.name] = self._deserialize_field(f, field, result)
        return result
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get a value from nested dictionary using dot notation."""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition string against the current context."""
        if not condition:
            return True
            
        # Simple condition parsing for expressions like "field > 0"
        # You can extend this to support more complex conditions
        operators = ['>=', '<=', '==', '!=', '>', '<']  # Order matters for proper parsing
        
        for op in operators:
            if op in condition:
                left, right = condition.split(op, 1)
                left = left.strip()
                right = right.strip()
                
                # Get left value from context
                left_value = self._get_nested_value(context, left)
                if left_value is None:
                    return False
                
                # Parse right value (could be number or another field)
                try:
                    right_value = int(right)
                except ValueError:
                    try:
                        right_value = float(right)
                    except ValueError:
                        # Assume it's a field reference
                        right_value = self._get_nested_value(context, right)
                        if right_value is None:
                            return False
                
                # Evaluate condition
                if op == '>':
                    return left_value > right_value
                elif op == '<':
                    return left_value < right_value
                elif op == '>=':
                    return left_value >= right_value
                elif op == '<=':
                    return left_value <= right_value
                elif op == '==':
                    return left_value == right_value
                elif op == '!=':
                    return left_value != right_value
                    
        return True
    
    def _deserialize_field(self, f: BinaryIO, field: FieldDefinition, context: Dict[str, Any]) -> Any:
        """Deserialize a single field from binary stream."""
        if field.type in self.TYPE_MAP:
            # Basic numeric type
            format_str = self.endian_char + self.TYPE_MAP[field.type]
            size = struct.calcsize(format_str)
            data = f.read(size)
            if len(data) < size:
                raise BinaryFormatError(f"Unexpected end of file reading {field.name}")
            return struct.unpack(format_str, data)[0]
            
        elif field.type == 'string':
            # String type
            if field.size:
                # Fixed-size string
                data = f.read(field.size)
                if len(data) < field.size:
                    raise BinaryFormatError(f"Unexpected end of file reading {field.name}")
                # Remove null padding
                return data.rstrip(b'\x00').decode(field.encoding, errors='replace')
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
                return data.decode(field.encoding, errors='replace')
                
        elif field.type == 'array':
            # Array type
            if field.length_field:
                # Length is determined by another field (support dot notation)
                array_length = self._get_nested_value(context, field.length_field)
                if array_length is None:
                    raise BinaryFormatError(f"Length field {field.length_field} not found for array {field.name}")
            elif field.size:
                # Fixed size array
                array_length = field.size
            else:
                # Variable length array - read length first
                length_format = self.endian_char + 'I'
                length_size = struct.calcsize(length_format)
                length_data = f.read(length_size)
                if len(length_data) < length_size:
                    raise BinaryFormatError(f"Unexpected end of file reading {field.name} length")
                array_length = struct.unpack(length_format, length_data)[0]
            
            # Deserialize array elements
            result = []
            element_field = field.fields[0] if field.fields else None
            for _ in range(array_length):
                element = self._deserialize_field(f, element_field, context)
                result.append(element)
            return result
            
        elif field.type == 'struct':
            # Nested structure
            return self._deserialize_fields(f, field.fields)
            
        else:
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
