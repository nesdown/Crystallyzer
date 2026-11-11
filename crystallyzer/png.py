"""A small PNG encoder, so the package needs nothing beyond numpy."""

from __future__ import annotations

import base64
import struct
import zlib

import numpy as np


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def encode(image: np.ndarray) -> bytes:
    """Grey (H×W) or colour (H×W×3) arrays, as floats from 0 to 1 or as uint8."""
    arr = np.asarray(image)
    if arr.dtype != np.uint8:
        arr = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)
    if arr.ndim == 2:
        colour = 0
    elif arr.ndim == 3 and arr.shape[2] == 3:
        colour = 2
    else:
        raise ValueError(f"Expected a grey or RGB image, got shape {arr.shape}")
    h, w = arr.shape[:2]
    rows = arr.reshape(h, -1)
    raw = b"".join(b"\x00" + rows[y].tobytes() for y in range(h))
    header = struct.pack(">IIBBBBB", w, h, 8, colour, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header) + _chunk(b"IDAT", zlib.compress(raw, 6)) + _chunk(b"IEND", b"")


def data_url(image: np.ndarray) -> str:
    return "data:image/png;base64," + base64.b64encode(encode(image)).decode()
