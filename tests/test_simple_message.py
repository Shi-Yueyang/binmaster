#!/usr/bin/env python3
"""Test simple message format functionality."""

import os
import tempfile
import pytest
from binary_format_handler import BinaryFormatHandler, BinaryFormatError


@pytest.fixture
def message_format():
    """Simple message format definition."""
    return {
        "endianness": "little",
        "description": "Simple message format with header and payload",
        "version": "1.0",
        "fields": [
            {
                "name": "header",
                "type": "struct",
                "description": "Message header",
                "fields": [
                    {
                        "name": "magic",
                        "type": "uint32",
                        "description": "Magic number to identify format"
                    },
                    {
                        "name": "version",
                        "type": "uint16",
                        "description": "Format version"
                    },
                    {
                        "name": "message_type",
                        "type": "uint16",
                        "description": "Type of message"
                    },
                    {
                        "name": "payload_size",
                        "type": "uint32",
                        "description": "Size of payload in bytes"
                    }
                ]
            },
            {
                "name": "sender",
                "type": "string",
                "size": 64,
                "encoding": "utf-8",
                "description": "Sender identifier (fixed 64 bytes)"
            },
            {
                "name": "timestamp",
                "type": "uint64",
                "description": "Unix timestamp"
            },
            {
                "name": "data",
                "type": "array",
                "length_field": "context['header']['payload_size']",
                "element_type": "uint8",
                "description": "Variable-length payload data"
            }
        ]
    }


@pytest.fixture
def sample_message_data():
    """Sample message data for testing."""
    return {
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


class TestSimpleMessage:
    """Test simple message format serialization and deserialization."""
    
    def test_message_roundtrip_with_dict(self, message_format, sample_message_data):
        """Test serialization and deserialization using format dict."""
        # Create handler with format dictionary
        handler = BinaryFormatHandler(message_format)
        
        # Serialize to bytes
        binary_data = handler.serialize_to_binary(sample_message_data)
        assert isinstance(binary_data, bytes)
        assert len(binary_data) > 0
        
        # Deserialize from bytes
        restored_data = handler.deserialize_from_binary(binary_data)
        
        # Verify data integrity
        assert restored_data == sample_message_data
    
    def test_message_roundtrip_with_file(self, message_format, sample_message_data):
        """Test serialization and deserialization using temporary files."""
        # Create handler with format dictionary
        handler = BinaryFormatHandler(message_format)
        
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as tmp_file:
            output_file = tmp_file.name
        
        try:
            # Serialize to file
            handler.serialize_to_binary(sample_message_data, output_file)
            
            # Verify file was created and has content
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0
            
            # Deserialize from file
            restored_data = handler.deserialize_from_binary(output_file)
            
            # Verify data integrity
            assert restored_data == sample_message_data
            
        finally:
            # Clean up
            if os.path.exists(output_file):
                os.unlink(output_file)
    
    def test_message_serialization_size(self, message_format, sample_message_data):
        """Test that serialized message has expected size."""
        handler = BinaryFormatHandler(message_format)
        binary_data = handler.serialize_to_binary(sample_message_data)
        
        # Expected size calculation:
        # header.magic: 4 bytes (uint32)
        # header.version: 2 bytes (uint16)
        # header.message_type: 2 bytes (uint16)
        # header.payload_size: 4 bytes (uint32)
        # sender: 64 bytes (fixed string)
        # timestamp: 8 bytes (uint64)
        # data: 5 bytes (array of 5 uint8)
        # Total: 4 + 2 + 2 + 4 + 64 + 8 + 5 = 89 bytes
        expected_size = 89
        assert len(binary_data) == expected_size
    
    def test_header_fields(self, message_format, sample_message_data):
        """Test that header fields are correctly serialized/deserialized."""
        handler = BinaryFormatHandler(message_format)
        binary_data = handler.serialize_to_binary(sample_message_data)
        restored_data = handler.deserialize_from_binary(binary_data)
        
        # Check each header field
        assert restored_data["header"]["magic"] == 0x4D534720
        assert restored_data["header"]["version"] == 1
        assert restored_data["header"]["message_type"] == 100
        assert restored_data["header"]["payload_size"] == 5
    
    def test_variable_length_data(self, message_format):
        """Test with different payload sizes."""
        handler = BinaryFormatHandler(message_format)
        
        # Test with different data lengths
        test_cases = [
            [72],  # 1 byte
            [72, 101],  # 2 bytes
            [72, 101, 108, 108, 111, 32, 87, 111, 114, 108, 100],  # 11 bytes
        ]
        
        for test_data in test_cases:
            message_data = {
                "header": {
                    "magic": 0x4D534720,
                    "version": 1,
                    "message_type": 100,
                    "payload_size": len(test_data)
                },
                "sender": "test@example.com",
                "timestamp": 1672531200,
                "data": test_data
            }
            
            binary_data = handler.serialize_to_binary(message_data)
            restored_data = handler.deserialize_from_binary(binary_data)
            
            assert restored_data == message_data
            assert restored_data["data"] == test_data
            assert len(restored_data["data"]) == len(test_data)
