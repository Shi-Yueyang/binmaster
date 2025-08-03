# Binary Format Handler

A Python library for reading custom binary format definitions from JSON and performing serialization/deserialization between JSON data and binary files.

## Features

- **Flexible Format Definition**: Define complex binary formats using JSON
- **Multiple Data Types**: Support for integers, floats, strings, arrays, and nested structures
- **Endianness Control**: Little-endian and big-endian byte order support
- **Variable Length Fields**: Arrays and strings with dynamic sizing
- **Nested Structures**: Support for complex hierarchical data
- **Schema Validation**: JSON schema for format definition validation

## Supported Data Types

### Basic Types
- `int8`, `int16`, `int32`, `int64` - Signed integers
- `uint8`, `uint16`, `uint32`, `uint64` - Unsigned integers  
- `float32`, `float64` - Floating point numbers
- `char` - Single character

### Complex Types
- `string` - Text strings with encoding support
- `array` - Arrays of any supported type
- `struct` - Nested structures containing multiple fields

## Quick Start

### 1. Define Your Binary Format

Create a JSON file describing your binary format:

```json
{
  "endianness": "little",
  "description": "Example format",
  "fields": [
    {
      "name": "header",
      "type": "struct",
      "fields": [
        {"name": "magic", "type": "uint32"},
        {"name": "version", "type": "uint16"}
      ]
    },
    {
      "name": "data_count",
      "type": "uint32"
    },
    {
      "name": "data",
      "type": "array",
      "length_field": "data_count",
      "element_type": "float32"
    }
  ]
}
```

### 2. Use the Handler

```python
from binary_format_handler import BinaryFormatHandler

# Create handler
handler = BinaryFormatHandler('your_format.json')

# Your data
data = {
    "header": {"magic": 0x12345678, "version": 1},
    "data_count": 3,
    "data": [1.0, 2.5, 3.14]
}

# Serialize to binary
handler.serialize_to_binary(data, 'output.bin')

# Deserialize from binary
restored_data = handler.deserialize_from_binary('output.bin')
```

## Format Definition Reference

### Root Object Properties

- `endianness` (optional): `"little"` or `"big"` - default is `"little"`
- `description` (optional): Human-readable description
- `version` (optional): Format version string
- `fields` (required): Array of field definitions

### Field Definition Properties

#### Required Properties
- `name`: Field name (string)
- `type`: Data type (see supported types above)

#### Optional Properties
- `size`: Size in bytes (for fixed strings) or element count (for fixed arrays)
- `encoding`: Text encoding for strings (default: `"utf-8"`)
- `length_field`: Name of field containing length for variable arrays
- `fields`: Nested field definitions for struct types
- `element_type`: Type of array elements
- `element_fields`: Field definitions for struct array elements
- `description`: Human-readable description

### Field Type Details

#### Strings
```json
{
  "name": "fixed_string",
  "type": "string",
  "size": 32,
  "encoding": "utf-8"
}
```

```json
{
  "name": "variable_string",
  "type": "string",
  "encoding": "utf-8"
}
```

#### Arrays
Fixed-size array:
```json
{
  "name": "coordinates",
  "type": "array",
  "size": 3,
  "element_type": "float32"
}
```

Variable-size array with length field:
```json
{
  "name": "items",
  "type": "array",
  "length_field": "item_count",
  "element_type": "uint32"
}
```

Array of structures:
```json
{
  "name": "points",
  "type": "array",
  "size": 10,
  "element_type": "struct",
  "element_fields": [
    {"name": "x", "type": "float32"},
    {"name": "y", "type": "float32"}
  ]
}
```

#### Nested Structures
```json
{
  "name": "header",
  "type": "struct",
  "fields": [
    {"name": "id", "type": "uint32"},
    {"name": "flags", "type": "uint16"},
    {"name": "timestamp", "type": "uint64"}
  ]
}
```

## Examples

The `examples.py` file contains several complete examples:

1. **Simple Message Format**: Basic packet with header and payload
2. **3D Model Format**: Complex format with vertices, faces, and materials
3. **Custom Packet Format**: Network packet with addresses and checksums

Run the examples:

```bash
python examples.py
```

## File Structure

```
scripts/
├── binary_format_handler.py    # Main library
├── format_schema.json          # JSON schema for validation
├── examples.py                 # Usage examples
└── examples/
    ├── message_format.json     # Simple message format
    └── model_format.json       # 3D model format
```

## Error Handling

The library raises `BinaryFormatError` exceptions for:
- Invalid format definitions
- Missing required fields in data
- Unexpected end of file during deserialization
- Type mismatches
- Unsupported field types

## Best Practices

1. **Always specify endianness** in your format definition
2. **Use descriptive field names** and include descriptions
3. **Validate your format** against the provided JSON schema
4. **Test round-trip serialization** to ensure data integrity
5. **Handle variable-length fields carefully** - ensure length fields are serialized before the arrays they describe
6. **Use appropriate numeric types** - don't use larger types than necessary
7. **Consider alignment** for performance-critical applications

## Advanced Usage

### Custom Length Fields

You can reference length fields using dot notation for nested structures:

```json
{
  "name": "payload",
  "type": "array",
  "length_field": "header.payload_size",
  "element_type": "uint8"
}
```

### Multiple Encoding Support

Different string fields can use different encodings:

```json
[
  {
    "name": "ascii_field",
    "type": "string",
    "size": 32,
    "encoding": "ascii"
  },
  {
    "name": "utf16_field", 
    "type": "string",
    "encoding": "utf-16"
  }
]
```

### Complex Nested Structures

You can nest structures arbitrarily deep:

```json
{
  "name": "scene",
  "type": "struct",
  "fields": [
    {
      "name": "objects",
      "type": "array",
      "size": 10,
      "element_type": "struct",
      "element_fields": [
        {
          "name": "transform",
          "type": "struct", 
          "fields": [
            {"name": "position", "type": "struct", "fields": [...]},
            {"name": "rotation", "type": "struct", "fields": [...]}
          ]
        }
      ]
    }
  ]
}
```

## License

This project is released under the MIT License.
