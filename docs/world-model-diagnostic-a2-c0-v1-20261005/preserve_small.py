"""Native Windows: exclusively preserve the two new compact Git source roots only.

Never reads weights, OS images, VM disks, guest filesystems or historical archives.
A failed new transfer remains in place and must be diagnosed, not blindly rerun.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).absolute().parents[2]
DOC = Path(__file__).absolute().parent
PREFIXES = ("docs/world-model-diagnostic-a2-c0-v1-20261005/",
            "docs/world-model-diagnostic-a2-c0-provisioning-20261005/")
DEST = Path("D:/THESIS-BACKUPS/world-model-diagnostic-a2-c0-v1-20261005")
VOLUME = "0a2f1ba9-0000-0000-0000-100000000000"
CAP = 64 * 1024**2


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, timeout=30)


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def whole(path):
    h = hashlib.sha256()
    total = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            total += len(chunk)
            if total > CAP:
                raise ValueError("Small package cap; retain partial")
            h.update(chunk)
    return {"bytes": total, "sha256": h.hexdigest()}


def verify(path, expected):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError("Archive member membership")
        for name, identity in expected.items():
            row = z.getinfo(name)
            if row.file_size != identity["bytes"] or digest(z.read(name)) != identity:
                raise ValueError("Archive member identity")
    return len(expected)


def main():
    started = time.monotonic()
    if os.name != "nt":
        raise PermissionError("Native Windows transfer required")
    commit = sys.argv[1]
    if len(commit) != 40 or git("rev-parse", commit).decode().strip() != commit:
        raise ValueError("Full commit required")
    volume = json.loads(subprocess.check_output([
        "powershell.exe", "-NoProfile", "-Command",
        "Get-Volume -DriveLetter D | Select-Object FileSystemLabel,UniqueId,SizeRemaining,HealthStatus | ConvertTo-Json"
    ], timeout=30))
    if volume["FileSystemLabel"] != "THESIS_SSD" or VOLUME not in volume["UniqueId"].lower():
        raise PermissionError("Wrong designated SSD")
    if volume["HealthStatus"] != "Healthy" or volume["SizeRemaining"] < 40 * 1024**3:
        raise ValueError("SSD health/free-space gate")
    names = git("ls-tree", "-r", "--name-only", commit, "--", *[p[:-1] for p in PREFIXES]).decode().splitlines()
    if not names or any(not n.startswith(PREFIXES) or "/delivery/" in n for n in names):
        raise ValueError("Exact source-only allowlist")
    if any(Path(n).suffix.lower() not in (".py", ".ps1", ".json", ".txt", ".md", ".safetensors", "") for n in names):
        raise ValueError("Unexpected compact source/fixture type")
    members = {name: git("show", commit + ":" + name) for name in names}
    expected = {name: digest(raw) for name, raw in members.items()}
    if sum(row["bytes"] for row in expected.values()) > CAP // 4:
        raise ValueError("Full-future local/archive/SSD/receipt copies cap")
    for name, identity in expected.items():
        # Git byte identity must cover the tested and frozen exact local sources.
        if digest((ROOT / name).read_bytes()) != identity:
            raise ValueError("Local versus committed source mismatch")
    manifest = json.dumps({"study": "WM-DIAG0-A2-C0-V1", "source_commit": commit,
                           "members": expected, "gate_ready": False,
                           "models_or_OS_images": False}, indent=2, sort_keys=True).encode()
    members["PACKAGE-MEMBERS.json"] = manifest
    expected["PACKAGE-MEMBERS.json"] = digest(manifest)
    delivery = DOC / "delivery"
    delivery.mkdir(exist_ok=True)
    DEST.mkdir(parents=True, exist_ok=True)
    local = delivery / ("a2-c0-v1-" + commit + ".zip")
    target = DEST / local.name
    receipt = DOC / "SSD-VERIFIED-V1-001.json"
    ssd_receipt = DEST / "SSD-VERIFIED-V1-001.json"
    if any(p.exists() for p in (local, target, receipt, ssd_receipt)):
        raise FileExistsError("Existing new package/partial/receipt: no overwrite or duplicate")
    with local.open("xb") as f:
        with zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as z:
            for name, raw in sorted(members.items()):
                z.writestr(name, raw)
        f.flush()
        os.fsync(f.fileno())
    count = verify(local, expected)
    identity = whole(local)
    with local.open("rb") as src, target.open("xb") as dst:
        for chunk in iter(lambda: src.read(65536), b""):
            dst.write(chunk)
        dst.flush()
        os.fsync(dst.fileno())
    if whole(target) != identity or verify(target, expected) != count:
        raise ValueError("SSD whole/member mismatch; preserve partial")
    logical = sum((ROOT / n).stat().st_size for n in names)
    combined = logical + identity["bytes"] * 2 + len(manifest) + 1000000
    if combined > CAP:
        raise ValueError("New all-copies cap exceeded")
    result = {"status": "WHOLE_AND_EVERY_MEMBER_VERIFIED", "study": "WM-DIAG0-A2-C0-V1",
              "source_commit": commit, "archive": str(target), "local_archive": str(local),
              "whole": identity, "verified_members": count,
              "members_manifest_sha256": digest(manifest)["sha256"], "volume": volume,
              "new_logical_source_bytes": logical, "new_full_future_copies_reserved_bytes": combined,
              "previous_retained_preparation_conservative_bytes": 4795342635,
              "retained_preparation_with_full_64MiB_reservation_bytes": 4862451499,
              "elapsed_seconds": time.monotonic() - started,
              "gate_ready": False, "real_checkpoint_access": False,
              "historical_archives_rebacked_up": 0, "runtime_images_or_models_recopied": 0}
    raw = json.dumps(result, indent=2, sort_keys=True).encode()
    for path in (receipt, ssd_receipt):
        with path.open("xb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
    if receipt.read_bytes() != ssd_receipt.read_bytes():
        raise ValueError("Compact receipt readback")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
