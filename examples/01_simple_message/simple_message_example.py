#!/usr/bin/env python3
"""Simple Message Format Example"""

import json
import os
import sys

# Add parent directory to Python path to import binary_format_handler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from binary_format_handler import BinaryFormatHandler, BinaryFormatError


def main():
    print("=== Simple Message Format Example ===")
    
    # Change to script directory to find format file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    message_data = {
        "header": {
            "magic": 0x4D534720,  # "MSG " in hex
            "version": 1,
            "message_type": 100,
            "payload_size": 5
        },
        "sender": "user@example.com",
        "timestamp": 1672531200,
        "data": [72, 101, 108, 108, 111]  # "Hello"
    }
    
    try:
        # Create handler
        handler = BinaryFormatHandler('message_format.json')
        
        # Serialize
        handler.serialize_to_binary(message_data, 'message_output.bin')
        file_size = os.path.getsize('message_output.bin')
        print(f"Generated binary file: {file_size} bytes")
        
        # Deserialize
        restored_data = handler.deserialize_from_binary('message_output.bin')
        
        # Verify
        if message_data == restored_data:
            print("✓ Test passed!")
        else:
            print("✗ Test failed!")
            
    except (BinaryFormatError, FileNotFoundError) as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
