# BinMaster

A Python library for serializing and deserializing binary data using JSON format definitions.

## Features

- Convert between JSON data and binary files
- Support for basic types: integers, floats, strings, arrays
- Support for complex structures and nested data
- Little/big endian byte order support
- Dynamic field references using context

## Supported Types

**Basic**: `int8`, `int16`, `int32`, `int64`, `uint8`, `uint16`, `uint32`, `uint64`, `float32`, `float64`  
**Complex**: `string`, `array`, `struct`, `union`

## Quick Start

### 1. Define your binary format in JSON:

```json
{
  "endianness": "little",
  "fields": [
    {"name": "magic", "type": "uint32"},
    {"name": "count", "type": "uint16"},
    {
      "name": "items",
      "type": "array",
      "length_field": "context['count']",
      "element_type": "uint32"
    }
  ]
}
```

### 2. Use the handler:

```python
from binary_format_handler import BinaryFormatHandler

# Initialize with format definition
handler = BinaryFormatHandler('format.json')  # From file
# or
handler = BinaryFormatHandler(format_dict)    # From dict
# or  
handler = BinaryFormatHandler('{"fields":[...]}')  # From JSON string

# Serialize JSON to binary
data = {
    "magic": 0x12345678,
    "count": 3,
    "items": [100, 200, 300]
}
binary_data = handler.serialize_to_binary(data)

# Deserialize binary to JSON
restored_data = handler.deserialize_from_binary(binary_data)
# or from file
restored_data = handler.deserialize_from_binary('data.bin')
```

## Array with Length Field

Use `length_field` to reference other fields for dynamic sizing:

```json
{
  "name": "payload",
  "type": "array", 
  "element_type": "uint8",
  "length_field": "context['data_size']"
}
```

## Testing

Run the test suite:

```bash
pytest tests/
```

Run benchmarks:

```bash
pytest tests/test_benchmark.py -v -s
```

## Examples

Check the `examples/` directory for real-world format examples including CN map data structures.
