# BinMaster

A Python library for converting between JSON data and binary files using custom format definitions.

## Features

- Define binary formats with JSON
- Support for integers, floats, strings, arrays, and nested structures
- Little-endian and big-endian byte order
- Variable and fixed-length fields
- Conditional fields and calculated values (CRC, checksums)

## Supported Types

**Basic**: `int8`, `int16`, `int32`, `int64`, `uint8`, `uint16`, `uint32`, `uint64`, `float32`, `float64`, `char`  
**Complex**: `string`, `array`, `struct`

## Quick Start

Create a format definition file:

```json
{
  "endianness": "little",
  "fields": [
    {
      "name": "header",
      "type": "struct",
      "fields": [
        {"name": "magic", "type": "uint32"},
        {"name": "version", "type": "uint16"}
      ]
    },
    {"name": "count", "type": "uint32"},
    {
      "name": "data",
      "type": "array",
      "length_field": "count",
      "element_type": "float32"
    }
  ]
}
```

Use the handler:

```python
from binary_format_handler import BinaryFormatHandler

handler = BinaryFormatHandler('format.json')

# JSON to binary
data = {
    "header": {"magic": 0x12345678, "version": 1},
    "count": 3,
    "data": [1.0, 2.5, 3.14]
}
handler.serialize_to_binary(data, 'output.bin')

# Binary to JSON
restored = handler.deserialize_from_binary('output.bin')
```

## Field Types

### Arrays
```json
// Fixed size
{"name": "coords", "type": "array", "size": 3, "element_type": "float32"}

// Variable size with length field
{"name": "items", "type": "array", "length_field": "count", "element_type": "uint32"}
```

### Strings
```json
// Fixed size
{"name": "name", "type": "string", "size": 32, "encoding": "utf-8"}

// Variable size
{"name": "text", "type": "string", "encoding": "utf-8"}
```

### Conditional Fields
```json
{"name": "optional_data", "type": "uint32", "condition": "flags > 0"}
```

### Calculated Fields
```json
{"name": "checksum", "type": "uint32", "function": "crc32", "function_scope": "all_previous"}
```

## Examples

Check the `examples/` directory for complete examples:
- Simple message format
- 3D model with vertices and materials
- Network packet with checksums
- CN map format with conditional fields

Run examples:
```bash
cd examples/01_simple_message && python simple_message_example.py
cd examples/02_3d_model && python model_example.py
cd examples/03_custom_format && python custom_format_example.py
```

## Installation

```bash
pip install crcmod  # Required dependency
```
