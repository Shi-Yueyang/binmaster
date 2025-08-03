#!/usr/bin/env python3
"""
Example usage of the Binary Format Handler

This script demonstrates how to use the BinaryFormatHandler class
with different format definitions and data structures.
"""

import json
import os
import sys

# Add parent directory to Python path to import binary_format_handler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binary_format_handler import BinaryFormatHandler, BinaryFormatError


def example_simple_message():
    """Example with a simple message format."""
    print("=== Simple Message Format Example ===")
    
    # Sample data for the message format
    message_data = {
        "header": {
            "magic": 0x4D534720,  # "MSG " in hex
            "version": 1,
            "message_type": 100,
            "payload_size": 5
        },
        "sender": "user@example.com",
        "timestamp": 1672531200,  # Unix timestamp
        "data": [72, 101, 108, 108, 111]  # "Hello" as bytes
    }
    
    try:
        # Create handler
        handler = BinaryFormatHandler('message_format.json')
        
        # Serialize
        print("Serializing message data...")
        handler.serialize_to_binary(message_data, 'message_output.bin')
        
        # Check file size
        file_size = os.path.getsize('message_output.bin')
        print(f"Generated binary file size: {file_size} bytes")
        
        # Deserialize
        print("Deserializing message data...")
        restored_data = handler.deserialize_from_binary('message_output.bin')
        
        # Display results
        print("\nOriginal data:")
        print(json.dumps(message_data, indent=2))
        print("\nRestored data:")
        print(json.dumps(restored_data, indent=2))
        
        # Verify
        if message_data == restored_data:
            print("✓ Message format test passed!")
        else:
            print("✗ Message format test failed!")
            
    except BinaryFormatError as e:
        print(f"Error: {e}")


def example_3d_model():
    """Example with a 3D model format."""
    print("\n=== 3D Model Format Example ===")
    
    # Sample data for a simple triangle
    model_data = {
        "file_header": {
            "signature": "MODEL3D",
            "version_major": 2,
            "version_minor": 1,
            "vertex_count": 3,
            "face_count": 1,
            "material_count": 1
        },
        "vertices": [
            {
                "position": {"x": 0.0, "y": 1.0, "z": 0.0},
                "normal": {"x": 0.0, "y": 0.0, "z": 1.0},
                "uv": {"u": 0.5, "v": 1.0},
                "color": {"r": 255, "g": 0, "b": 0, "a": 255}
            },
            {
                "position": {"x": -1.0, "y": -1.0, "z": 0.0},
                "normal": {"x": 0.0, "y": 0.0, "z": 1.0},
                "uv": {"u": 0.0, "v": 0.0},
                "color": {"r": 0, "g": 255, "b": 0, "a": 255}
            },
            {
                "position": {"x": 1.0, "y": -1.0, "z": 0.0},
                "normal": {"x": 0.0, "y": 0.0, "z": 1.0},
                "uv": {"u": 1.0, "v": 0.0},
                "color": {"r": 0, "g": 0, "b": 255, "a": 255}
            }
        ],
        "faces": [
            {
                "v1": 0,
                "v2": 1,
                "v3": 2,
                "material_id": 0
            }
        ],
        "materials": [
            {
                "name": "DefaultMaterial",
                "diffuse_color": {"r": 0.8, "g": 0.8, "b": 0.8, "a": 1.0},
                "specular_color": {"r": 1.0, "g": 1.0, "b": 1.0},
                "shininess": 32.0,
                "texture_path": "textures/default.png"
            }
        ]
    }
    
    try:
        # Create handler
        handler = BinaryFormatHandler('model_format.json')
        
        # Serialize
        print("Serializing 3D model data...")
        handler.serialize_to_binary(model_data, 'model_output.bin')
        
        # Check file size
        file_size = os.path.getsize('model_output.bin')
        print(f"Generated binary file size: {file_size} bytes")
        
        # Deserialize
        print("Deserializing 3D model data...")
        restored_data = handler.deserialize_from_binary('model_output.bin')
        
        # Display key information
        print(f"\nModel signature: {restored_data['file_header']['signature']}")
        print(f"Version: {restored_data['file_header']['version_major']}.{restored_data['file_header']['version_minor']}")
        print(f"Vertices: {restored_data['file_header']['vertex_count']}")
        print(f"Faces: {restored_data['file_header']['face_count']}")
        print(f"Materials: {restored_data['file_header']['material_count']}")
        
        # Verify
        if model_data == restored_data:
            print("✓ 3D model format test passed!")
        else:
            print("✗ 3D model format test failed!")
            # Show first difference for debugging
            for key in model_data:
                if model_data[key] != restored_data[key]:
                    print(f"Difference in '{key}':")
                    print(f"  Original: {model_data[key]}")
                    print(f"  Restored: {restored_data[key]}")
                    break
                    
    except BinaryFormatError as e:
        print(f"Error: {e}")


def create_custom_format():
    """Example of creating a custom format definition."""
    print("\n=== Custom Format Creation Example ===")
    
    # Define a custom packet format
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
                "element_type": "uint8",
                "description": "IPv4 source address"
            },
            {
                "name": "destination_address",
                "type": "array",
                "size": 4,
                "element_type": "uint8",
                "description": "IPv4 destination address"
            },
            {
                "name": "payload",
                "type": "array",
                "length_field": "packet_header.data_length",
                "element_type": "uint8",
                "description": "Variable-length payload"
            },
            {
                "name": "checksum",
                "type": "uint32",
                "description": "CRC32 checksum"
            }
        ]
    }
    
    # Save the format
    with open('custom_packet_format.json', 'w') as f:
        json.dump(packet_format, f, indent=2)
    print("Created custom packet format definition: custom_packet_format.json")
    
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
        
        print("Testing custom packet format...")
        handler.serialize_to_binary(packet_data, 'packet_output.bin')
        restored_data = handler.deserialize_from_binary('packet_output.bin')
        
        if packet_data == restored_data:
            print("✓ Custom packet format test passed!")
        else:
            print("✗ Custom packet format test failed!")
            
    except BinaryFormatError as e:
        print(f"Error: {e}")


def main():
    """Run all examples."""
    print("Binary Format Handler Examples")
    print("=" * 50)
    
    # Ensure examples directory exists
    os.makedirs('examples', exist_ok=True)
    
    # Run examples
    example_simple_message()
    example_3d_model()
    create_custom_format()
    
    print("\n" + "=" * 50)
    print("All examples completed!")
    
    # Clean up generated files
    cleanup = input("\nDelete generated binary files? (y/n): ").lower().strip()
    if cleanup == 'y':
        for filename in ['message_output.bin', 'model_output.bin', 'packet_output.bin']:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"Deleted {filename}")


if __name__ == "__main__":
    main()
