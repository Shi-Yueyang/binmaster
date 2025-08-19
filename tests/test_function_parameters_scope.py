#!/usr/bin/env python3
import os
import sys
import struct
import crcmod
import pytest

# Ensure the project root is on sys.path to import the module when running pytest from repo root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from binary_format_handler import BinaryFormatHandler, BinaryFormatError


def crc32_default(data: bytes) -> int:
    """Helper to compute CRC32 matching the handler's defaults."""
    crc_func = crcmod.mkCrcFun(0x104C11DB7, initCrc=0xFFFFFFFF, rev=True, xorOut=0xFFFFFFFF)
    return crc_func(data)


def test_crc32_scope_in_parameters_all_previous():
    """crc32 should use function_scope provided in function_parameters (all_previous)."""
    fmt = {
        "endianness": "little",
        "fields": [
            {"name": "a", "type": "uint8"},
            {"name": "b", "type": "uint16"},
            {
                "name": "crc",
                "type": "uint32",
                "function": "crc32",
                # No top-level scope fields
                "function_parameters": {
                    "function_scope": "all_previous",
                    "initial_value": 0xFFFFFFFF
                }
            }
        ]
    }

    data = {"a": 0x01, "b": 0x0203, "crc": "auto"}

    handler = BinaryFormatHandler(fmt)
    blob = handler.serialize_to_binary(data)

    # Expected CRC over bytes of a and b only
    payload = struct.pack('<B', data['a']) + struct.pack('<H', data['b'])
    expected_crc = crc32_default(payload)

    # Extract CRC from the end of blob (little-endian uint32)
    actual_crc, = struct.unpack('<I', blob[-4:])
    assert actual_crc == expected_crc


def test_crc32_scope_in_parameters_field_range():
    """crc32 should support field_range defined entirely in function_parameters."""
    fmt = {
        "endianness": "little",
        "fields": [
            {"name": "a", "type": "uint8"},
            {"name": "b", "type": "uint16"},
            {"name": "c", "type": "uint8"},
            {
                "name": "crc",
                "type": "uint32",
                "function": "crc32",
                "function_parameters": {
                    "function_scope": "field_range",
                    "function_scope_start": "a",
                    "function_scope_end": "b",
                    "initial_value": 0xFFFFFFFF
                }
            }
        ]
    }

    data = {"a": 0xAA, "b": 0xBBCC, "c": 0xDD, "crc": "auto"}

    handler = BinaryFormatHandler(fmt)
    blob = handler.serialize_to_binary(data)

    # Expected CRC over bytes of a..b range only (exclude c)
    payload = struct.pack('<B', data['a']) + struct.pack('<H', data['b'])
    expected_crc = crc32_default(payload)
    actual_crc, = struct.unpack('<I', blob[-4:])
    assert actual_crc == expected_crc


def test_parameters_override_top_level_scope():
    """function_parameters.function_scope should override top-level function_scope."""
    fmt = {
        "endianness": "little",
        "fields": [
            {"name": "a", "type": "uint8"},
            {"name": "b", "type": "uint16"},
            {
                "name": "crc",
                "type": "uint32",
                "function": "crc32",
                # Legacy top-level scope that would produce a different CRC
                "function_scope": "entire_file",
                # Parameters override to a precise field range
                "function_parameters": {
                    "function_scope": "field_range",
                    "function_scope_start": "a",
                    "function_scope_end": "b",
                    "initial_value": 0xFFFFFFFF
                }
            }
        ]
    }

    data = {"a": 0x11, "b": 0x2233, "crc": "auto"}
    handler = BinaryFormatHandler(fmt)
    blob = handler.serialize_to_binary(data)

    # Expected CRC over a..b only (not over entire_file which includes placeholder zeros)
    payload = struct.pack('<B', data['a']) + struct.pack('<H', data['b'])
    expected_crc = crc32_default(payload)
    actual_crc, = struct.unpack('<I', blob[-4:])
    assert actual_crc == expected_crc
