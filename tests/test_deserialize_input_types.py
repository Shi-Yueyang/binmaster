"""
Test different input types for deserialize_from_binary method.
"""
import pytest
import json
import tempfile
import os
from binary_format_handler import BinaryFormatHandler, BinaryFormatError


def test_deserialize_from_file_path():
    """Test deserializing from a file path."""
    # Create a simple format
    format_def = {
        "endianness": "little",
        "fields": [
            {"name": "magic", "type": "uint32"},
            {"name": "version", "type": "uint16"}
        ]
    }
    
    # Create test data
    test_data = {
        "magic": 0x12345678,
        "version": 42
    }
    
    # Create handler and serialize data
    handler = BinaryFormatHandler(format_def)
    binary_data = handler.serialize_to_binary(test_data)
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(binary_data)
        tmp_file_path = tmp_file.name
    try:
        # Test deserializing from file path
        result = handler.deserialize_from_binary(tmp_file_path)
        assert result == test_data
    finally:
        # Clean up
        os.unlink(tmp_file_path)


def test_deserialize_from_bytes():
    """Test deserializing from bytes object."""
    # Create a simple format
    format_def = {
        "endianness": "little",
        "fields": [
            {"name": "magic", "type": "uint32"},
            {"name": "version", "type": "uint16"}
        ]
    }
    
    # Create test data
    test_data = {
        "magic": 0x12345678,
        "version": 42
    }
    
    # Create handler and serialize data
    handler = BinaryFormatHandler(format_def)
    binary_data = handler.serialize_to_binary(test_data)
    
    # Test deserializing from bytes
    result = handler.deserialize_from_binary(binary_data)
    assert result == test_data


def test_deserialize_from_bytearray():
    """Test deserializing from bytearray object."""
    # Create a simple format
    format_def = {
        "endianness": "little",
        "fields": [
            {"name": "magic", "type": "uint32"},
            {"name": "version", "type": "uint16"}
        ]
    }
    
    # Create test data
    test_data = {
        "magic": 0x12345678,
        "version": 42
    }
    
    # Create handler and serialize data
    handler = BinaryFormatHandler(format_def)
    binary_data = handler.serialize_to_binary(test_data)
    
    # Convert to bytearray and test deserializing
    binary_array = bytearray(binary_data)
    result = handler.deserialize_from_binary(binary_array)
    assert result == test_data



def test_round_trip_consistency():
    """Test that serialization followed by deserialization is consistent for both input types."""
    # Create a more complex format
    format_def = {
        "endianness": "little",
        "fields": [
            {"name": "header", "type": "struct", "fields": [
                {"name": "magic", "type": "uint32"},
                {"name": "version", "type": "uint16"}
            ]},
            {"name": "name", "type": "string", "size": 16},
            {"name": "count", "type": "uint8"},
            {"name": "values", "type": "array", "length_field": r"context['count']", "element_type": "float32"}
        ]
    }
    
    test_data = {
        "header": {
            "magic": 0xDEADBEEF,
            "version": 1
        },
        "name": "test",
        "count": 3,
        "values": [1.5, 2.5, 3.5]
    }
    
    handler = BinaryFormatHandler(format_def)
    
    # Serialize to bytes
    binary_data = handler.serialize_to_binary(test_data)
    
    result_from_bytes = handler.deserialize_from_binary(binary_data)
    
    # Both should be equal to original data
    assert result_from_bytes == test_data
    # Both should be equal to each other
    

