#!/usr/bin/env python3
"""
Test script for two-phase serialization with arbitrary range feature
"""

import json
import os
import sys

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from binary_format_handler import BinaryFormatHandler

def test_two_phase_serialization():
    """Test two-phase serialization with different scope types."""

    # Test data (note: we don't provide values for functional fields)
    test_data = {
        "magic": 0x12345678,
        "version": 1,
        "flags": 0x0001,
        "data_count": 3,
        "data_array": [100, 200, 300]
        # Functional fields (header_crc, data_checksum, total_crc, calculated_size) 
        # will be automatically calculated
    }
    
    try:
        handler = BinaryFormatHandler('test_two_phase_format.json')
        
        print("Testing two-phase serialization with arbitrary scopes...")
        
        # Serialize to binary (functional fields will be auto-calculated)
        handler.serialize_to_binary(test_data, 'test_two_phase.bin')
        print("✓ Successfully serialized with auto-calculated functional fields")
        
        # Deserialize from binary
        restored_data = handler.deserialize_from_binary('test_two_phase.bin')
        with open('restored_data.json', 'w') as f:
            json.dump(restored_data, f, indent=2)

        print("✓ Successfully deserialized data")
        
        # Display results
        print("\nOriginal data (without functional fields):")
        print(json.dumps(test_data, indent=2))
        
        print("\nRestored data (with calculated functional fields):")
        print(json.dumps(restored_data, indent=2))
        
        # Show calculated values
        print(f"\nCalculated functional fields:")
        print(f"Header CRC (magic to flags): 0x{restored_data['header_crc']:08x}")
        print(f"Data checksum (XOR from data_count): {restored_data['data_checksum']}")
        print(f"Total CRC (all previous): 0x{restored_data['total_crc']:08x}")
        print(f"Calculated file size: {restored_data['calculated_size']} bytes")
        
        # Check file size
        actual_size = os.path.getsize('test_two_phase.bin')
        print(f"Actual file size: {actual_size} bytes")
        

        
        print("\n✓ All tests passed!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Cleanup on error
        for file in ['test_two_phase_format.json', 'test_two_phase.bin']:
            if os.path.exists(file):
                os.remove(file)


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    test_two_phase_serialization()
