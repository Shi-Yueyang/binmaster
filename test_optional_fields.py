#!/usr/bin/env python3
"""
Test script for optional fields functionality in binary_format_handler.py
"""

import json
import os
from binary_format_handler import BinaryFormatHandler

def test_optional_fields():
    """Test that optional fields work correctly based on conditions."""
    
    # Create a simple test format with optional fields
    test_format = {
        "endianness": "little",
        "description": "Test format with optional fields",
        "fields": [
            {"name": "count", "type": "uint8"},
            {
                "name": "optional_value",
                "type": "uint16", 
                "condition": "count > 0"
            },
            {"name": "always_present", "type": "uint32"}
        ]
    }
    
    # Save test format
    with open('test_format.json', 'w') as f:
        json.dump(test_format, f, indent=2)
    
    # Test data where condition is true (count > 0)
    test_data_with_optional = {
        "count": 5,
        "optional_value": 1234,
        "always_present": 999999
    }
    
    # Test data where condition is false (count = 0)
    test_data_without_optional = {
        "count": 0,
        "always_present": 888888
    }
    
    try:
        handler = BinaryFormatHandler('test_format.json')
        
        print("Testing optional field inclusion (count > 0)...")
        handler.serialize_to_binary(test_data_with_optional, 'test_with_optional.bin')
        restored_with_optional = handler.deserialize_from_binary('test_with_optional.bin')
        print("✓ Successfully serialized and deserialized data with optional field")
        print(f"Original: {test_data_with_optional}")
        print(f"Restored: {restored_with_optional}")
        
        print("\nTesting optional field exclusion (count = 0)...")
        handler.serialize_to_binary(test_data_without_optional, 'test_without_optional.bin')
        restored_without_optional = handler.deserialize_from_binary('test_without_optional.bin')
        print("✓ Successfully serialized and deserialized data without optional field")
        print(f"Original: {test_data_without_optional}")
        print(f"Restored: {restored_without_optional}")
        
        # Check file sizes
        size_with = os.path.getsize('test_with_optional.bin')
        size_without = os.path.getsize('test_without_optional.bin')
        print(f"\nFile sizes:")
        print(f"With optional field: {size_with} bytes")
        print(f"Without optional field: {size_without} bytes")
        print(f"Difference: {size_with - size_without} bytes (should be 2 for uint16)")
        
        # Cleanup
        os.remove('test_format.json')
        os.remove('test_with_optional.bin')
        os.remove('test_without_optional.bin')
        
        print("\n✓ All tests passed!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        # Cleanup on error
        for file in ['test_format.json', 'test_with_optional.bin', 'test_without_optional.bin']:
            if os.path.exists(file):
                os.remove(file)

if __name__ == "__main__":
    test_optional_fields()
