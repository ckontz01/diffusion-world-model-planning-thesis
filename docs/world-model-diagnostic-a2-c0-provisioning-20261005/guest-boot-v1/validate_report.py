"""Independent bounded DATA-ONLY validator. Never mounts a guest filesystem."""
import hashlib
import json
import os
import pathlib
import stat
import struct
import sys

DISK_BYTES = 8388608
NONCE = "c0-boot-v1-9cd3026b-dc45-4adc-b7c4-e2942308bf94"
FIELDS = {"study", "nonce", "status", "os_id", "os_version", "python_version", "machine",
          "logical_cpus", "memory_total_kib", "root_total_bytes", "root_available_bytes",
          "network_interfaces", "real_checkpoints_loaded", "runtime_installation_attempted"}

def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result

def reject_constant(value):
    raise ValueError("Nonfinite JSON constant")

def validate_frame(data):
    if len(data) != DISK_BYTES or data[:8] != b"C0BOOT01":
        raise ValueError("Size or magic mismatch")
    length = struct.unpack_from("<I", data, 8)[0]
    if not 1 <= length <= 32768:
        raise ValueError("Payload length exceeds contract")
    payload = data[44:44 + length]
    if hashlib.sha256(payload).digest() != data[12:44] or any(data[44 + length:]):
        raise ValueError("Hash mismatch or unexpected trailing data")
    report = json.loads(payload.decode("utf-8", "strict"), object_pairs_hook=unique, parse_constant=reject_constant)
    if type(report) is not dict or set(report) != FIELDS:
        raise ValueError("Missing or extra schema members")
    expected = {"study": "WM-DIAG0-A2-C0", "nonce": NONCE, "status": "OS_ONLY_OFFLINE_BOOT_REPORT",
                "os_id": "ubuntu", "os_version": "22.04", "machine": "x86_64"}
    if any(type(report[k]) is not str or report[k] != v for k, v in expected.items()):
        raise ValueError("Unexpected identity / OS")
    version = report["python_version"]
    if type(version) is not list or len(version) != 3 or any(type(x) is not int for x in version) or version[:2] != [3, 10] or not 0 <= version[2] <= 100:
        raise ValueError("Unexpected Python version")
    limits = {"logical_cpus": (1, 4), "memory_total_kib": (1, 1048576),
              "root_total_bytes": (1, 2361393152), "root_available_bytes": (0, 2361393152)}
    for key, (low, high) in limits.items():
        if type(report[key]) is not int or not low <= report[key] <= high:
            raise ValueError("Invalid numeric resource field: " + key)
    if report["root_available_bytes"] > report["root_total_bytes"]:
        raise ValueError("Invalid free space")
    interfaces = report["network_interfaces"]
    if type(interfaces) is not list or not 1 <= len(interfaces) <= 8 or len(set(x for x in interfaces if type(x) is str)) != len(interfaces):
        raise ValueError("Invalid interface inventory")
    if any(type(x) is not str or not 1 <= len(x) <= 16 or not all(c.isascii() and (c.isalnum() or c in "_.-") for c in x) for x in interfaces):
        raise ValueError("Invalid interface name")
    for key in ("real_checkpoints_loaded", "runtime_installation_attempted"):
        if report[key] is not False:
            raise ValueError("Non-preparation report")
    return report

def validate_disk(path):
    path = pathlib.Path(path)
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode) or path.stat().st_size != DISK_BYTES + 512:
        raise ValueError("Not an exact fixed VHD data container")
    with path.open("rb") as stream:
        data = stream.read(DISK_BYTES)
        footer = bytearray(stream.read(512))
        if stream.read(1):
            raise ValueError("Extra bytes")
    checksum = struct.unpack_from(">I", footer, 64)[0]
    footer[64:68] = bytes(4)
    if footer[:8] != b"conectix" or struct.unpack_from(">Q", footer, 16)[0] != 0xffffffffffffffff or struct.unpack_from(">Q", footer, 48)[0] != DISK_BYTES or struct.unpack_from(">I", footer, 60)[0] != 2 or checksum != (~sum(footer) & 0xffffffff):
        raise ValueError("Fixed VHD footer rejected")
    return validate_frame(data)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: validate_report.py EXACT_FIXED_VHD_PATH")
    print(json.dumps(validate_disk(sys.argv[1]), sort_keys=True, allow_nan=False))
