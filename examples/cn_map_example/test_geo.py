import os
import sys
import json

# Add parent directory to Python path to import binary_format_handler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from binary_format_handler import BinaryFormatHandler, BinaryFormatError

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    handler = BinaryFormatHandler('cn_map_geo_format.json')
    map_geo = handler.deserialize_from_binary('mapfiles/64642.1')
    output_file = 'mapfiles/64642.1.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(map_geo, f, indent=2, ensure_ascii=False)
    print(f"Result saved to: {output_file}")
    

if __name__ == "__main__":
    main()
