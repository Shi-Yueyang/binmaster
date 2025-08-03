#!/usr/bin/env python3
"""Custom Format Creation Example"""

import json
import os
import sys

# Add parent directory to Python path to import binary_format_handler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from binary_format_handler import BinaryFormatHandler, BinaryFormatError


def main():
    print("=== Custom Format Creation Example ===")
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Create custom packet format
    packet_format = {
        "endianness": "big",
        "description": "Network packet format",
        "version": "1.0",
        "fields": [
            {
                "name": "packet_header",
                "type": "struct",
                "fields": [
                    {"name": "packet_id", "type": "uint32"},
                    {"name": "sequence_number", "type": "uint32"},
                    {"name": "flags", "type": "uint16"},
                    {"name": "data_length", "type": "uint16"}
                ]
            },
            {
                "name": "source_address",
                "type": "array",
                "size": 4,
                "element_type": "uint8"
            },
            {
                "name": "destination_address",
                "type": "array",
                "size": 4,
                "element_type": "uint8"
            },
            {
                "name": "payload",
                "type": "array",
                "length_field": "packet_header.data_length",
                "element_type": "uint8"
            },
            {
                "name": "checksum",
                "type": "uint32"
            }
        ]
    }
    
    # Save format
    with open('custom_packet_format.json', 'w') as f:
        json.dump(packet_format, f, indent=2)
    print("Created custom format definition")
    
    # Create sample data
    packet_data = {
        "packet_header": {
            "packet_id": 12345,
            "sequence_number": 1,
            "flags": 0x0001,
            "data_length": 11
        },
        "source_address": [192, 168, 1, 100],
        "destination_address": [10, 0, 0, 1],
        "payload": [72, 101, 108, 108, 111, 32, 87, 111, 114, 108, 100],  # "Hello World"
        "checksum": 0x12345678
    }
    
    try:
        # Test the custom format
        handler = BinaryFormatHandler('custom_packet_format.json')
        
        handler.serialize_to_binary(packet_data, 'packet_output.bin')
        file_size = os.path.getsize('packet_output.bin')
        print(f"Generated binary file: {file_size} bytes")
        
        restored_data = handler.deserialize_from_binary('packet_output.bin')
        
        if packet_data == restored_data:
            print("✓ Custom format test passed!")
        else:
            print("✗ Custom format test failed!")
            
    except BinaryFormatError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
