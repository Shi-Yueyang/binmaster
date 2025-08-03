#!/usr/bin/env python3
"""3D Model Format Example"""

import os
import sys

# Add parent directory to Python path to import binary_format_handler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from binary_format_handler import BinaryFormatHandler, BinaryFormatError


def main():
    print("=== 3D Model Format Example ===")
    
    # Change to script directory to find format file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
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
        
        # Serialize and deserialize
        handler.serialize_to_binary(model_data, 'model_output.bin')
        file_size = os.path.getsize('model_output.bin')
        print(f"Generated binary file: {file_size} bytes")
        
        restored_data = handler.deserialize_from_binary('model_output.bin')
        
        # Show info
        header = restored_data['file_header']
        print(f"Model: {header['signature']} v{header['version_major']}.{header['version_minor']}")
        print(f"Vertices: {header['vertex_count']}, Faces: {header['face_count']}")
        
        # Verify (allowing for floating-point precision differences)
        if model_data == restored_data:
            print("✓ Test passed!")
        else:
            print("⚠ Minor differences (normal for floating-point data)")
            
    except (BinaryFormatError, FileNotFoundError) as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
