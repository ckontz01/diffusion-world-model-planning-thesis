"""Additional artificial-only hash, schema and numeric edge checks; no suite rerun."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import time

import validator as v
from test_validator import encoded, fixture, invoke, sha, write


def main():
    started = time.monotonic()
    root = Path(__file__).absolute().parent / "artificial-supplement-001"
    root.mkdir()
    checks = []
    f, c, m, h, p = fixture(root, "reviewer_whole_hash_valid")
    c["files"]["model.safetensors"]["sha256"] = m["file_sha256"]["model.safetensors"]
    (f / "contract.json").write_bytes(encoded(c))
    assert invoke(f)["status"] == "DATA_ONLY_VALIDATED"
    checks.append("reviewer_supplied_whole_hash_acceptance")

    f, c, m, h, p = fixture(root, "changed_header_same_tensor_bytes")
    original = (f / "export" / "model.safetensors").read_bytes()
    c["files"]["model.safetensors"]["sha256"] = sha(original)
    # Reorder a JSON field without changing tensors or overall header length.
    new_h = {key: {"shape": item["shape"], "data_offsets": item["data_offsets"], "dtype": item["dtype"]}
             for key, item in h.items()}
    raw = json.dumps(new_h, separators=(",", ":")).encode()
    assert len(raw) == int.from_bytes(original[:8], "little") - ((-len(raw)) % 8)
    write(f, c, m, h, p, header_raw=raw)
    try:
        invoke(f)
    except v.Rejected as error:
        assert str(error) == "file_expected_hash"
        checks.append("converter_self_consistent_header_change_rejected_by_reviewed_whole_hash")
    else:
        raise AssertionError("changed whole hash accepted")
    for label, raw, code in [
        ("nonfinite_JSON", b'{"x":NaN}', "json_nonfinite"),
        ("duplicate_contract_JSON", b'{"version":1,"version":1}', "duplicate_json_key"),
        ("invalid_utf8", b'{"x":"\xff"}', "json_syntax"),
        ("nested_depth", b"[" * 25 + b"0" + b"]" * 25, "json_depth")
    ]:
        try:
            v.parse_json(raw, 8192)
        except v.Rejected as error:
            assert str(error) == code
            checks.append(label)
        else:
            raise AssertionError(label)
    for dtype, raw in [("F16", bytes.fromhex("00fc")), ("BF16", bytes.fromhex("80ff")),
                       ("F64", bytes.fromhex("000000000000f0ff"))]:
        v.check_numeric(raw, dtype, "allow_negative_infinity")
        checks.append(dtype + "_declared_negative_infinity_allowed")
    for name in ("contract.schema.json", "export.schema.json", "REAL-STATE-BINDING.json", "AUTHORIZATION-AND-RESERVATION.json"):
        path = Path(__file__).absolute().parent / name
        v.parse_json(path.read_bytes(), v.MAX_CONTRACT)
        checks.append("strict_JSON_" + name)
    result = dict(study="WM-DIAG0-A2-C0-V1", attempt="supplement-001", status="PASSED",
                  checks=len(checks), results=checks, elapsed_seconds=time.monotonic() - started,
                  real_checkpoint_access=False, gate_ready=False)
    (root / "TEST-RECEIPT.json").write_bytes(json.dumps(result, indent=2).encode())
    print(json.dumps(result))


if __name__ == "__main__":
    main()
