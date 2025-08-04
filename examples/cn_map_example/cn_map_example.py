import os
import sys
import json

# Add parent directory to Python path to import binary_format_handler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from binary_format_handler import BinaryFormatHandler, BinaryFormatError

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    handler = BinaryFormatHandler('cn_map_format.json')

    # deserialize
    map_index = handler.deserialize_from_binary('150896641.0')
    output_file = '150896641.0.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(map_index, f, indent=2, ensure_ascii=False)
    print(f"Result saved to: {output_file}")

 
    # Serialize
    with open('map_index_test.json','r',encoding='utf-8') as f:
        test_data = json.load(f)
    handler.serialize_to_binary(test_data, 'map_index_test.bin')
    map_index_restored = handler.deserialize_from_binary('map_index_test.bin')
    output_file_restored = 'map_index_test_restored.json'
    with open(output_file_restored, 'w', encoding='utf-8') as f:
        json.dump(map_index_restored, f, indent=2, ensure_ascii=False)
    os.remove('map_index_test.bin')

if __name__ == "__main__":
    main()
