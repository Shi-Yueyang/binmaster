"""
Test for array of unions with tricky length_field usage.
Highlights key features from cn_map_fix_format.json:

1. Arrays with length_field referencing context fields
2. Nested structs with calculated array sizes 
3. Complex field references using context['field_name'] syntax

These tests demonstrate the core functionality without 
over-complicating with full union implementations.
"""
import pytest
from binary_format_handler import BinaryFormatHandler


def test_simple_array_with_length_field():
    """Test array with length_field that references context."""
    
    # Simple test highlighting length_field usage
    format_def = {
        "endianness": "little",
        "description": "Array with length field test",
        "fields": [
            {"name": "count", "type": "uint8"},
            {
                "name": "items",
                "type": "array",
                "length_field": "context['count']",  # Key feature: references previous field
                "element_type": "struct",
                "element_fields": [
                    {"name": "id", "type": "uint16"},
                    {"name": "value", "type": "uint32"}
                ]
            }
        ]
    }
    
    test_data = {
        "count": 2,
        "items": [
            {"id": 100, "value": 1000},
            {"id": 200, "value": 2000}
        ]
    }
    
    handler = BinaryFormatHandler(format_def)
    binary_data = handler.serialize_to_binary(test_data)
    restored_data = handler.deserialize_from_binary(binary_data)
    
    # Verify the length_field worked correctly
    assert restored_data["count"] == 2
    assert len(restored_data["items"]) == 2
    assert restored_data["items"][0]["id"] == 100
    assert restored_data["items"][1]["value"] == 2000


def test_nested_struct_with_size_calculation():
    """Test struct with size field that's calculated from other fields."""
    
    format_def = {
        "endianness": "little", 
        "description": "Nested struct with calculated size",
        "fields": [
            {
                "name": "header",
                "type": "struct",
                "fields": [
                    {"name": "magic", "type": "uint32"},
                    {"name": "data_size", "type": "uint16"},
                    {
                        "name": "payload",
                        "type": "array",
                        "element_type": "uint8",
                        "length_field": "context['header']['data_size']"  # References nested field
                    }
                ]
            }
        ]
    }
    
    test_data = {
        "header": {
            "magic": 0x12345678,
            "data_size": 4,
            "payload": [0xAA, 0xBB, 0xCC, 0xDD]
        }
    }
    
    handler = BinaryFormatHandler(format_def)
    binary_data = handler.serialize_to_binary(test_data)
    restored_data = handler.deserialize_from_binary(binary_data)
    
    assert restored_data["header"]["magic"] == 0x12345678
    assert restored_data["header"]["data_size"] == 4
    assert restored_data["header"]["payload"] == [0xAA, 0xBB, 0xCC, 0xDD]


def test_length_field_with_context_reference():
    """Test length_field that references previous fields in context."""
    
    format_def = {
        "endianness": "little", 
        "description": "Context reference test",
        "fields": [
            {"name": "header_size", "type": "uint8"},
            {"name": "data_count", "type": "uint8"},
            {
                "name": "items",
                "type": "array",
                "length_field": "context['data_count']",  # References previous field
                "element_type": "struct",
                "element_fields": [
                    {"name": "item_type", "type": "uint8"},
                    {"name": "item_value", "type": "uint16"}
                ]
            }
        ]
    }
    
    test_data = {
        "header_size": 10,
        "data_count": 3,
        "items": [
            {"item_type": 1, "item_value": 100},
            {"item_type": 2, "item_value": 200}, 
            {"item_type": 3, "item_value": 300}
        ]
    }
    
    handler = BinaryFormatHandler(format_def)
    binary_data = handler.serialize_to_binary(test_data)
    restored_data = handler.deserialize_from_binary(binary_data)
    
    assert restored_data["data_count"] == 3
    assert len(restored_data["items"]) == 3
    assert restored_data["items"][1]["item_value"] == 200
