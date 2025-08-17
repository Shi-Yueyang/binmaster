#!/usr/bin/env python3
"""
Simple tests for Binary Format Handler

This file contains basic tests to verify the BinaryFormatHandler works correctly.
"""

import pytest
import json
import os
import tempfile
import sys

# Add parent directory to path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binary_format_handler import BinaryFormatHandler, BinaryFormatError


class TestBinaryFormatHandler:
    """Test cases for BinaryFormatHandler class."""
    
    def test_import_handler(self):
        """Test that we can import the BinaryFormatHandler class."""
        assert BinaryFormatHandler is not None
    
    def test_exception_class(self):
        """Test that BinaryFormatError exception exists."""
        assert BinaryFormatError is not None
        
        # Test we can raise it
        with pytest.raises(BinaryFormatError):
            raise BinaryFormatError("Test error")
    
    def test_create_simple_format_file(self):
        """Test creating a simple format definition file."""
        simple_format = {
            "endianness": "little",
            "description": "Simple test format",
            "fields": [
                {"name": "magic", "type": "uint32"},
                {"name": "version", "type": "uint16"}
            ]
        }
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(simple_format, f)
            format_file = f.name
        
        try:
            # Test that we can create a handler with this format
            handler = BinaryFormatHandler(format_file)
            assert handler is not None
            assert handler.endianness == "little"
        finally:
            # Clean up
            os.unlink(format_file)
    
    def test_simple_data_serialization(self):
        """Test basic serialization functionality."""
        # Create a simple format
        simple_format = {
            "endianness": "little",
            "description": "Simple test format",
            "fields": [
                {"name": "magic", "type": "uint32"},
                {"name": "version", "type": "uint16"}
            ]
        }
        
        # Test data
        test_data = {
            "magic": 0x12345678,
            "version": 1
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as format_file:
            json.dump(simple_format, format_file)
            format_path = format_file.name
        
        with tempfile.NamedTemporaryFile(delete=False) as output_file:
            output_path = output_file.name
        
        try:
            # Test serialization
            handler = BinaryFormatHandler(format_path)
            handler.serialize_to_binary(test_data, output_path)
            
            # Check that output file was created and has content
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
            
        finally:
            # Clean up
            os.unlink(format_path)
            if os.path.exists(output_path):
                os.unlink(output_path)




if __name__ == "__main__":
    # Allow running the test file directly
    pytest.main([__file__])
