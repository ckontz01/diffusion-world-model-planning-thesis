"""Small artificial DATA fixtures only; no VM, checkpoint or scientific forward."""
import hashlib
import json
import pathlib
import struct
import time
import validate_report as validator

start = time.monotonic()
good = {"study": "WM-DIAG0-A2-C0", "nonce": validator.NONCE,
        "status": "OS_ONLY_OFFLINE_BOOT_REPORT", "os_id": "ubuntu", "os_version": "22.04",
        "python_version": [3, 10, 12], "machine": "x86_64", "logical_cpus": 4,
        "memory_total_kib": 900000, "root_total_bytes": 2200000000,
        "root_available_bytes": 1200000000, "network_interfaces": ["lo", "eth0"],
        "real_checkpoints_loaded": False, "runtime_installation_attempted": False}
def frame(payload):
    if isinstance(payload, dict):
        payload = json.dumps(payload).encode()
    encoded = b"C0BOOT01" + struct.pack("<I", len(payload)) + hashlib.sha256(payload).digest() + payload
    return encoded + bytes(validator.DISK_BYTES - len(encoded))

checks = []
assert validator.validate_frame(frame(good)) == good
checks.append("artificial exact roundtrip")
bad = []
for name, key, value in [("wrong nonce", "nonce", "other"), ("extra schema field", "target", "os.system"),
                         ("wrong numeric type", "logical_cpus", True), ("CPU excess", "logical_cpus", 5),
                         ("RAM excess", "memory_total_kib", 2000000), ("executable path string", "network_interfaces", ["../evil.py"]),
                         ("research flag", "real_checkpoints_loaded", True), ("unexpected version", "python_version", [3, 11, 1])]:
    value_dict = dict(good); value_dict[key] = value; bad.append((name, frame(value_dict)))
missing = dict(good); del missing["machine"]; bad.append(("missing member", frame(missing)))
bad.append(("duplicate JSON key", frame(json.dumps(good).encode()[:-1] + b',"logical_cpus":4}')))
bad.append(("nonfinite JSON", frame(json.dumps(good).replace('"logical_cpus": 4', '"logical_cpus": NaN').encode())))
bad.append(("oversized declaration", b"C0BOOT01" + struct.pack("<I", 32769) + bytes(validator.DISK_BYTES - 12)))
corrupt = bytearray(frame(good)); corrupt[44] ^= 1; bad.append(("corrupt payload hash", bytes(corrupt)))
tail = bytearray(frame(good)); tail[-1] = 1; bad.append(("unexpected trailing data", bytes(tail)))
bad.append(("truncated container", frame(good)[:-1]))
for name, data in bad:
    try:
        validator.validate_frame(data)
    except (ValueError, TypeError, UnicodeError):
        checks.append("reject " + name)
    else:
        raise AssertionError("Did not reject " + name)

# Read the tiny ISO as bounded bytes, not by mounting any filesystem.
seed = pathlib.Path("C:/Users/Chris/thesis-vm/wm-diag0-a2-c0-runtime-v1/guest-boot-v1")
iso = (seed / "cidata.iso").read_bytes()
assert len(iso) == 57344 and hashlib.sha256(iso).hexdigest().upper() == "2A7BF46E5AA5063FEE2F43ED5DA495DE39E6A71274C4B67EAC8A449AC6A70C53"
primary = iso[16 * 2048:17 * 2048]
assert primary[:7] == b"\x01CD001\x01" and primary[40:72].decode("ascii").strip() == "CIDATA"
supplements = [iso[x:x+2048] for x in range(17*2048, min(len(iso), 24*2048), 2048) if iso[x] == 2 and iso[x+1:x+6] == b"CD001"]
assert len(supplements) == 1
supplement = supplements[0]
assert supplement[88:91] in [b"%/@", b"%/C", b"%/E"]
root = supplement[156:]
extent, length = struct.unpack_from("<I", root, 2)[0], struct.unpack_from("<I", root, 10)[0]
assert extent * 2048 + length <= len(iso)
directory = iso[extent * 2048:extent * 2048 + length]
members = {}
cursor = 0
while cursor < len(directory):
    record_length = directory[cursor]
    if record_length == 0:
        cursor = ((cursor // 2048) + 1) * 2048; continue
    record = directory[cursor:cursor + record_length]
    assert len(record) == record_length and record_length >= 34
    ident = record[33:33 + record[32]]
    if ident not in [b"\0", b"\1"]:
        name = ident.decode("utf-16-be").split(";")[0]
        assert name not in members and name in ["meta-data", "user-data"] and not record[25] & 2
        offset, size = struct.unpack_from("<I", record, 2)[0] * 2048, struct.unpack_from("<I", record, 10)[0]
        assert offset + size <= len(iso) and size <= 16384
        members[name] = iso[offset:offset + size]
    cursor += record_length
assert set(members) == {"meta-data", "user-data"}
for name, data in members.items():
    assert data == (seed / "seed" / name).read_bytes()
checks.append("ISO CIDATA label and exact two Joliet members independently read back")
print(json.dumps({"status": "ARTIFICIAL_REPORT_AND_ISO_CHECKS_PASSED", "checks": checks,
                  "elapsed_seconds": time.monotonic() - start, "guest_executed": False,
                  "actual_isolation_tests": False, "real_checkpoint_tests": False}, indent=2))
