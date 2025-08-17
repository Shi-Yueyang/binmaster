#!/usr/bin/env python3
"""Test different initialization methods for BinaryFormatHandler."""

import pytest
import json
import tempfile
import os
from binary_format_handler import BinaryFormatHandler, BinaryFormatError


class TestBinaryFormatHandlerInit:
    """Test the different ways to initialize BinaryFormatHandler."""
    
    def setup_method(self):
        """Set up test data."""
        self.sample_format = {
            "endianness": "little",
            "description": "Test format",
            "fields": [
                {"name": "magic", "type": "uint32"},
                {"name": "version", "type": "uint16"},
                {"name": "name", "type": "string", "size": 32}
            ]
        }
        
    def test_init_with_dict(self):
        """Test initialization with a dictionary."""
        handler = BinaryFormatHandler(self.sample_format)
        assert handler.format_json_dict == self.sample_format
        assert handler.endianness == "little"
        assert handler.endian_char == '<'
        
    def test_init_with_json_string(self):
        """Test initialization with a JSON string."""
        json_string = json.dumps(self.sample_format)
        handler = BinaryFormatHandler(json_string)
        assert handler.format_json_dict == self.sample_format
        assert handler.endianness == "little"
        
    def test_init_with_file_path(self):
        """Test initialization with a file path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_format, f)
            temp_file = f.name
            
        try:
            handler = BinaryFormatHandler(temp_file)
            assert handler.format_json_dict == self.sample_format
            assert handler.endianness == "little"
        finally:
            os.unlink(temp_file)
            
    def test_init_with_invalid_json_string(self):
        """Test initialization with invalid JSON string."""
        invalid_json = '{"invalid": json}'
        with pytest.raises(BinaryFormatError) as exc_info:
            BinaryFormatHandler(invalid_json)
        assert "Invalid JSON" in str(exc_info.value)
        
    def test_init_with_nonexistent_file(self):
        """Test initialization with nonexistent file."""
        with pytest.raises(BinaryFormatError) as exc_info:
            BinaryFormatHandler("nonexistent_file.json")
        assert "Format file not found" in str(exc_info.value)
        
    def test_init_with_invalid_type(self):
        """Test initialization with invalid input type."""
        with pytest.raises(BinaryFormatError) as exc_info:
            BinaryFormatHandler(123)
        assert "Unsupported format_source type" in str(exc_info.value)
        
    def test_init_with_missing_fields_key(self):
        """Test initialization with format missing 'fields' key."""
        invalid_format = {"endianness": "little", "description": "No fields"}
        with pytest.raises(BinaryFormatError) as exc_info:
            BinaryFormatHandler(invalid_format)
        assert "must contain 'fields' key" in str(exc_info.value)
        
    def test_init_with_default_endianness(self):
        """Test initialization with default endianness when not specified."""
        format_without_endianness = {
            "description": "Test format",
            "fields": [{"name": "test", "type": "uint32"}]
        }
        handler = BinaryFormatHandler(format_without_endianness)
        assert handler.endianness == "little"  # default
        assert handler.endian_char == '<'
        
    def test_init_with_big_endian(self):
        """Test initialization with big endian format."""
        big_endian_format = {
            "endianness": "big",
            "description": "Big endian test",
            "fields": [{"name": "test", "type": "uint32"}]
        }
        handler = BinaryFormatHandler(big_endian_format)
        assert handler.endianness == "big"
        assert handler.endian_char == '>'
