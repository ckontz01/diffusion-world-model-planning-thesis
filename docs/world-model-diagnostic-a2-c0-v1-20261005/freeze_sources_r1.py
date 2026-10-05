"""Seal only approved compact source roots and authenticate existing tiny receipts."""
import hashlib
import json
from pathlib import Path
import time


def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    started = time.monotonic()
    doc = Path(__file__).absolute().parent
    root = doc.parents[1]
    provision = root / "docs/world-model-diagnostic-a2-c0-provisioning-20261005"
    target = doc / "SOURCE-IDENTITIES-001.json"
    if target.exists():
        raise FileExistsError("Exclusive source seal already exists")
    prepared = json.loads((provision / "guest-boot-v1/PREPARATION-RECEIPT.json").read_bytes())
    checks = {
        "guest_report.py": "guest_probe_SHA256",
        "validate_report.py": "independent_report_validator_SHA256",
        "Stop-Offline-Boot.ps1": "stop_helper_SHA256",
        "Test-Offline-Guest-Boot.ps1": "one_shot_administrator_script_SHA256",
        "Build-Seed-ISO.ps1": "seed_builder_SHA256",
        "test_report_and_iso.py": "artificial_test_source_SHA256"
    }
    for name, field in checks.items():
        actual = identity((provision / "guest-boot-v1" / name).read_bytes())
        if actual["sha256"].upper() != prepared[field]:
            raise ValueError("Previously tested administrator/boot source changed")
    # This is an existing JSON receipt, NOT a disk, filesystem mount or checkpoint.
    receipt_path = Path("C:/Users/Chris/thesis-vm/wm-diag0-a2-c0-prep-v1/OS-DISK-V1-VERIFIED.json")
    receipt_raw = receipt_path.read_bytes()
    if identity(receipt_raw)["sha256"].upper() != "F283B2144CA29310714638C657C41E54EBFEF5FEBEDE2A66F2A2ED02198BFC86":
        raise ValueError("Historical attachment receipt mismatch")
    compact_receipt = doc / "HUMAN-OS-ATTACHMENT-RECEIPT.json"
    if compact_receipt.exists():
        if compact_receipt.read_bytes() != receipt_raw:
            raise ValueError("Preserved compact receipt mismatch")
    else:
        with compact_receipt.open("xb") as f:
            f.write(receipt_raw)
    members = {}
    allowed_extensions = {".py", ".ps1", ".json", ".txt", ".md", ".safetensors", ""}
    for base in (doc, provision):
        for path in sorted(base.rglob("*")):
            if "__pycache__" in path.parts:
                continue  # Existing interpreter cache is retained locally, not published.
            if not path.is_file():
                continue
            if path.suffix.lower() not in allowed_extensions:
                raise ValueError("Unapproved publication member")
            members[path.relative_to(root).as_posix()] = identity(path.read_bytes())
    logical = sum(row["bytes"] for row in members.values())
    if logical > 64 * 1024**2 // 4:
        raise ValueError("V1 full-future copy reservation")
    result = dict(study="WM-DIAG0-A2-C0-V1", members=members,
                  source_logical_bytes=logical, previous_guest_sources_unchanged=True,
                  exact_prior_human_attachment_receipt_authenticated=True,
                  measured_process_seconds={"artificial_failed_001": 1.9593434,
                                            "artificial_passed_002": 1.2634194,
                                            "supplemental_passed_001": 0.4316376},
                  current_full_conservative_charge_seconds=1800,
                  cumulative_preparation_charged_seconds=8914.10301460012,
                  remaining_of_14400_seconds=5485.89698539988,
                  first_boot_full_charge_retained=True, real_conversion_seconds_consumed=0,
                  gate_ready=False, runtime_ready=False, real_checkpoint_access=False,
                  elapsed_freeze_seconds=time.monotonic() - started)
    with target.open("xb") as f:
        f.write(json.dumps(result, indent=2, sort_keys=True).encode())
    print(json.dumps({key: value for key, value in result.items() if key != "members"}, sort_keys=True))


if __name__ == "__main__":
    main()
