"""Helper utilities for the Drone Forensic Framework"""

import os
import hashlib


def calculate_file_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def ensure_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
        return True
    return False


def format_timestamp(dt):
    # YYYYMMDD_HHMMSS format for filenames
    return dt.strftime('%Y%m%d_%H%M%S')