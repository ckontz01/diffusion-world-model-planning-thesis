"""Trusted, OS-only first-boot probe. Run inside the disposable guest only."""
import hashlib
import json
import os
import pathlib
import struct
import subprocess
import sys

NONCE = "c0-boot-v1-9cd3026b-dc45-4adc-b7c4-e2942308bf94"
MAGIC = b"C0BOOT01"
DISK_BYTES = 8 * 1024 * 1024

def main():
    candidates = []
    for entry in pathlib.Path("/sys/block").iterdir():
        if entry.name.startswith("sd") and int((entry / "size").read_text()) * 512 == DISK_BYTES:
            candidates.append(entry.name)
    if len(candidates) != 1:
        raise RuntimeError("Exactly one 8 MiB report disk required; no device written")
    device = "/dev/" + candidates[0]
    fd = os.open(device, os.O_RDWR | os.O_SYNC)
    try:
        if any(os.pread(fd, DISK_BYTES, 0)):
            raise RuntimeError("Report disk is not entirely zero; no overwrite")
        release = {}
        for line in pathlib.Path("/etc/os-release").read_text()[:8192].splitlines():
            key, sep, value = line.partition("=")
            if sep:
                release[key] = value.strip('"')
        memory = pathlib.Path("/proc/meminfo").read_text()[:8192]
        mem_kib = int(next(x.split()[1] for x in memory.splitlines() if x.startswith("MemTotal:")))
        space = os.statvfs("/")
        report = {
            "study": "WM-DIAG0-A2-C0", "nonce": NONCE, "status": "OS_ONLY_OFFLINE_BOOT_REPORT",
            "os_id": release.get("ID", ""), "os_version": release.get("VERSION_ID", ""),
            "python_version": list(sys.version_info[:3]), "machine": os.uname().machine,
            "logical_cpus": os.cpu_count(), "memory_total_kib": mem_kib,
            "root_total_bytes": space.f_blocks * space.f_frsize,
            "root_available_bytes": space.f_bavail * space.f_frsize,
            "network_interfaces": sorted(x.name for x in pathlib.Path("/sys/class/net").iterdir()),
            "real_checkpoints_loaded": False, "runtime_installation_attempted": False,
        }
        payload = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(payload) > 32768:
            raise RuntimeError("Oversized report")
        frame = MAGIC + struct.pack("<I", len(payload)) + hashlib.sha256(payload).digest() + payload
        if os.pwrite(fd, frame, 0) != len(frame):
            raise RuntimeError("Short report write")
        os.fsync(fd)
    finally:
        os.close(fd)
    os.sync()
    subprocess.run(["/sbin/poweroff"], check=True, timeout=10)

if __name__ == "__main__":
    main()
