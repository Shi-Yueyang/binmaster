import os
import sys
import json

# Add parent directory to Python path to import binary_format_handler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from binary_format_handler import BinaryFormatHandler, BinaryFormatError

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    handler = BinaryFormatHandler('line_format.json')
    map_line_data = handler.deserialize_from_binary('Config2.line1')

    json_file = 'Config2.line1.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(map_line_data, f, indent=2, ensure_ascii=False)

    bin_file = 'Config2.line1.bin'
    handler.serialize_to_binary(map_line_data, bin_file)
    
    restored_data = handler.deserialize_from_binary(bin_file)
    with open('restored_data.json', 'w', encoding='utf-8') as f:
        json.dump(restored_data, f, indent=2, ensure_ascii=False)
    
if __name__ == "__main__":
    main()