# Ref: https://github.com/albar965/littlenavmap/issues/1088
import struct

import numpy as np


def parse_geometry(blob_data):
    """
    Parses a Little Navmap boundary.geometry BLOB into a list of (lon, lat) tuples.
    Uses Big-Endian decoding as per QDataStream defaults.
    """
    if not blob_data or len(blob_data) < 4:
        return []
    # 1. Unpack the first 4 bytes to get the number of points (Big-Endian unsigned int)
    num_points = struct.unpack('>I', blob_data[:4])[0]
    # 2. Calculate expected byte size: 4 bytes (header) + 8 bytes * points (4 bytes lon + 4 bytes lat)
    expected_size = 4 + (num_points * 8)
    if len(blob_data) < expected_size:
        raise ValueError(
            f"Corrupted BLOB: expected {expected_size} bytes, got {len(blob_data)}")
    # 3. Create the struct format string: '>' (Big-Endian) followed by 'f' (float32) * (points * 2)
    fmt = f'>{num_points * 2}f'
    # 4. Unpack the rest of the bytes into a flat tuple of floats
    coords_raw = struct.unpack(fmt, blob_data[4:expected_size])
    # 5. Group the flat tuple into (longitude, latitude) coordinate pairs
    coordinates = np.array([[coords_raw[i], coords_raw[i + 1]] for i in
                            range(0, len(coords_raw), 2)])
    return coordinates