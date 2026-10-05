"""Tiny, retained, artificial-only producer and independent parser tests.

The literal tensor bytes below are the test oracle. No module serialization,
checkpoint loading, scientific import, guest operation or real model forward.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
from unittest.mock import patch

import validator as v

HERE = Path(__file__).absolute().parent
PYTHON = sys.executable


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


# Hand-specified IEEE and integer little-endian words; producer does not choose them.
LITERALS = {
    "parameter.weight": ("F32", [2], "parameter", "finite", bytes.fromhex("0000803f00000080")),
    "buffer.persistent": ("I32", [2], "persistent_buffer", "finite", bytes.fromhex("01000000feffffff")),
    "buffer.nonpersistent": ("BF16", [2], "nonpersistent_buffer", "finite", bytes.fromhex("803f0080")),
    "attention.causal_mask": ("F32", [2, 2], "unregistered_tensor", "allow_negative_infinity",
                              bytes.fromhex("00000000000080ff0000000000000000")),
    "scalar": ("F64", [], "parameter", "finite", bytes.fromhex("000000000000f03f")),
    "empty": ("F32", [0, 3], "nonpersistent_buffer", "finite", b""),
    "half": ("F16", [2], "parameter", "finite", bytes.fromhex("003c0080")),
    "boolean": ("BOOL", [2], "persistent_buffer", "finite", b"\x00\x01"),
    "signed8": ("I8", [2], "parameter", "finite", b"\xff\x01"),
    "unsigned8": ("U8", [2], "parameter", "finite", b"\x00\xff"),
    "signed16": ("I16", [1], "parameter", "finite", b"\xff\xff"),
    "unsigned16": ("U16", [1], "parameter", "finite", b"\xff\xff"),
    "unsigned32": ("U32", [1], "parameter", "finite", b"\xff" * 4),
    "signed64": ("I64", [1], "parameter", "finite", b"\xff" * 8),
    "unsigned64": ("U64", [1], "parameter", "finite", b"\xff" * 8),
}


def fixture(root, label):
    folder = root / label
    folder.mkdir()
    stage = folder / "export"
    stage.mkdir()
    payload = bytearray()
    header = {}
    tensor_contract = {}
    for key, (dtype, shape, role, policy, raw) in sorted(LITERALS.items()):
        lo = len(payload)
        payload.extend(raw)
        header[key] = dict(dtype=dtype, shape=shape, data_offsets=[lo, len(payload)])
        tensor_contract[key] = dict(file="model.safetensors", dtype=dtype, shape=shape,
                                    role=role, nonfinite=policy, sha256=sha(raw))
    c = dict(version=1, binding="BOUND",
             limits=dict(total_bytes=65536, manifest_bytes=16384, header_bytes=8192,
                         tensor_count=32, rank=8, dimension=64, seconds=5),
             input_artifacts={"artificial_input": {"bytes": 7, "sha256": sha(b"fixture")}},
             files={"model.safetensors": {"bytes": 0, "sha256": None}}, tensors=tensor_contract,
             aliases={"parameter.shared_weight": "parameter.weight"},
             configuration={"normalization": {"mean": [0.5, -0.0], "std": [0.25, 1.0]},
                            "training": False, "architecture": "ARTIFICIAL_ONLY", "context": 1})
    m = dict(version=1, input_artifacts=copy.deepcopy(c["input_artifacts"]),
             aliases=copy.deepcopy(c["aliases"]), configuration=copy.deepcopy(c["configuration"]),
             file_sha256={}, tensor_sha256={k: sha(value[4]) for k, value in LITERALS.items()})
    write(folder, c, m, header, bytes(payload))
    return folder, c, m, header, bytes(payload)


def write(folder, c, m, h, payload, header_raw=None, trailer=b"", keep_length=False):
    raw = encoded(h) if header_raw is None else header_raw
    # Valid header padding is spaces only. Header bytes aren't an executable format.
    raw += b" " * ((-len(raw)) % 8)
    data = struct.pack("<Q", len(raw)) + raw + payload + trailer
    if not keep_length:
        c["files"]["model.safetensors"]["bytes"] = len(data)
    m["file_sha256"] = {"model.safetensors": sha(data)}
    (folder / "contract.json").write_bytes(encoded(c))
    (folder / "export" / "manifest.json").write_bytes(encoded(m))
    (folder / "export" / "model.safetensors").write_bytes(data)


def invoke(folder, **kwargs):
    return v.validate(folder / "contract.json", folder / "export",
                      kwargs.get("max_bytes", 65536), kwargs.get("max_seconds", 5))


def main():
    started = time.monotonic()
    root = HERE / ("artificial-" + sys.argv[1])
    root.mkdir()  # Exclusive attempt, never overwrite a prior attempt.
    checks = []

    def passed(label, result="PASSED", detail=None):
        checks.append(dict(check=label, result=result, detail=detail))

    def reject(label, mutate, reason):
        folder, c, m, h, payload = fixture(root, label)
        mutate(folder, c, m, h, payload)
        try:
            invoke(folder)
        except v.Rejected as error:
            assert str(error) == reason, (label, str(error), reason)
            passed(label, detail=reason)
        else:
            raise AssertionError(label + " was accepted")

    folder, c, m, h, payload = fixture(root, "valid_exact_roundtrip")
    report = invoke(folder)
    assert report["status"] == "DATA_ONLY_VALIDATED" and report["tensor_count"] == len(LITERALS)
    # Independent readback using literal expected descriptors and bytes; not emitted manifest.
    data = (folder / "export" / "model.safetensors").read_bytes()
    n = int.from_bytes(data[:8], "little")
    parsed = json.loads(data[8:8 + n])
    for key, (dtype, shape, role, policy, raw) in LITERALS.items():
        lo, hi = parsed[key]["data_offsets"]
        actual = data[8 + n + lo:8 + n + hi]
        assert actual == raw and parsed[key]["shape"] == shape and parsed[key]["dtype"] == dtype
        assert report["tensors"][key]["role"] == role and report["tensors"][key]["sha256"] == sha(raw)
    assert struct.unpack("<f", LITERALS["parameter.weight"][4][:4])[0] == 1.0
    assert LITERALS["parameter.weight"][4][4:] == b"\x00\x00\x00\x80"
    assert struct.unpack("<d", LITERALS["scalar"][4])[0] == 1.0
    assert report["aliases"] == {"parameter.shared_weight": "parameter.weight"}
    passed("valid_exact_roundtrip_all_14_declared_dtypes_scalar_empty_signed_zero_mask_and_roles")

    def header_change(key, value):
        def change(folder, c, m, h, payload):
            h[key] = value
            write(folder, c, m, h, payload)
        return change

    def drop(key):
        def change(folder, c, m, h, payload):
            del h[key]
            write(folder, c, m, h, payload)
        return change

    reject("missing_parameter", drop("parameter.weight"), "tensor_members")
    reject("lost_unregistered_mask", drop("attention.causal_mask"), "tensor_members")
    reject("missing_nonpersistent_buffer", drop("buffer.nonpersistent"), "tensor_members")
    reject("extra_tensor", header_change("surprise", dict(dtype="U8", shape=[0], data_offsets=[0, 0])), "tensor_members")
    reject("unexpected_header_metadata", header_change("__metadata__", {"import": "os"}), "tensor_members")
    reject("object_dtype", header_change("parameter.weight", dict(dtype="OBJECT", shape=[2], data_offsets=[0, 8])), "unsupported_dtype")
    reject("unimplemented_subbyte_dtype", header_change("parameter.weight", dict(dtype="F8_E4M3", shape=[2], data_offsets=[0, 2])), "unsupported_dtype")
    reject("wrong_dtype", header_change("parameter.weight", dict(dtype="I32", shape=[2], data_offsets=[0, 8])), "tensor_architecture")
    reject("wrong_shape", header_change("parameter.weight", dict(dtype="F32", shape=[1, 2], data_offsets=[0, 8])), "tensor_architecture")
    reject("oversized_dimension", header_change("parameter.weight", dict(dtype="F32", shape=[2**62], data_offsets=[0, 8])), "dimension")
    reject("zero_then_oversized_dimension", header_change("empty", dict(dtype="F32", shape=[0, 2**62], data_offsets=[0, 0])), "dimension")
    reject("rank_limit", header_change("parameter.weight", dict(dtype="F32", shape=[1] * 9, data_offsets=[0, 4])), "rank")

    def offsets(kind):
        def change(folder, c, m, h, payload):
            item = h["parameter.weight"]
            if kind == "overlap":
                item["data_offsets"] = [0, 8]
            elif kind == "negative":
                item["data_offsets"] = [-1, 7]
            elif kind == "huge":
                item["data_offsets"] = [2**62, 2**62 + 8]
            elif kind == "boolean":
                item["data_offsets"] = [False, 8]
            elif kind == "length":
                item["data_offsets"][1] -= 1
            write(folder, c, m, h, payload)
        return change

    reject("overlapping_offsets", offsets("overlap"), "coverage")
    reject("negative_offset", offsets("negative"), "offset_range")
    reject("huge_offset", offsets("huge"), "offset_range")
    reject("boolean_offset", offsets("boolean"), "offset_range")
    reject("wrong_tensor_byte_count", offsets("length"), "offset_size")
    reject("hole_or_trailing_payload", lambda f, c, m, h, p: write(f, c, m, h, p, trailer=b"x"), "coverage")
    reject("truncated_payload", lambda f, c, m, h, p: write(f, c, m, h, p[:-1]), "offset_range")

    def duplicate_header(folder, c, m, h, payload):
        raw = encoded(h)
        raw = b'{"scalar":' + encoded(h["scalar"]) + b"," + raw[1:]
        write(folder, c, m, h, payload, header_raw=raw)
    reject("duplicate_tensor_key", duplicate_header, "duplicate_json_key")

    def duplicate_manifest(folder, c, m, h, payload):
        path = folder / "export" / "manifest.json"
        path.write_bytes(b'{"version":1,' + path.read_bytes()[1:])
    reject("duplicate_manifest_key", duplicate_manifest, "duplicate_json_key")

    def huge_header(folder, c, m, h, payload):
        path = folder / "export" / "model.safetensors"
        path.write_bytes(struct.pack("<Q", 2**63) + b"{}")
        c["files"]["model.safetensors"]["bytes"] = 10
        (folder / "contract.json").write_bytes(encoded(c))
    reject("huge_claimed_header_no_allocation", huge_header, "header_size")
    reject("json_depth_limit", lambda f, c, m, h, p:
           write(f, c, m, h, p, header_raw=b'{"x":' + b"[" * 25 + b"0" + b"]" * 25 + b"}"), "json_depth")

    def meta(kind):
        def change(folder, c, m, h, payload):
            if kind == "target":
                m["configuration"]["_target_"] = "os.system"
            elif kind == "extra":
                m["executable"] = "pickle"
            elif kind == "bool":
                m["configuration"]["context"] = True
            elif kind == "negativezero":
                m["configuration"]["normalization"]["mean"][1] = 0.0
            elif kind == "alias":
                m["aliases"]["parameter.shared_weight"] = "missing"
            elif kind == "origin":
                m["input_artifacts"]["artificial_input"]["sha256"] = "0" * 64
            write(folder, c, m, h, payload)
        return change
    reject("hydra_import_instruction", meta("target"), "configuration_string")
    reject("extra_executable_manifest_field", meta("extra"), "manifest_fields")
    reject("config_boolean_is_not_integer", meta("bool"), "configuration_binding")
    reject("configuration_signed_zero_preserved", meta("negativezero"), "configuration_binding")
    reject("invalid_shared_alias", meta("alias"), "alias_binding")
    reject("wrong_original_artifact_identity", meta("origin"), "artifact_binding")

    def altered(folder, c, m, h, payload):
        p = bytearray(payload)
        lo, hi = h["parameter.weight"]["data_offsets"]
        p[lo] ^= 1
        m["tensor_sha256"]["parameter.weight"] = sha(p[lo:hi])  # Converter lies consistently.
        write(folder, c, m, h, bytes(p))
    reject("changed_bytes_self_consistent_converter_manifest", altered, "tensor_expected_hash")

    def float_bits(key, bits):
        def change(folder, c, m, h, payload):
            p = bytearray(payload)
            lo, hi = h[key]["data_offsets"]
            p[lo:lo + len(bits)] = bits
            c["tensors"][key]["sha256"] = None  # Force the finite policy, not an expected hash.
            m["tensor_sha256"][key] = sha(p[lo:hi])
            write(folder, c, m, h, bytes(p))
        return change
    reject("positive_infinity_mask_forbidden", float_bits("attention.causal_mask", bytes.fromhex("0000807f")), "nonfinite_tensor")
    reject("nan_mask_forbidden", float_bits("attention.causal_mask", bytes.fromhex("0000c07f")), "nonfinite_tensor")
    reject("negative_infinity_weight_forbidden", float_bits("parameter.weight", bytes.fromhex("000080ff")), "nonfinite_tensor")
    reject("bf16_nan_forbidden", float_bits("buffer.nonpersistent", bytes.fromhex("c07f")), "nonfinite_tensor")
    reject("f16_infinity_forbidden", float_bits("half", bytes.fromhex("007c")), "nonfinite_tensor")
    reject("f64_nan_forbidden", float_bits("scalar", bytes.fromhex("000000000000f87f")), "nonfinite_tensor")
    reject("invalid_boolean_bits", float_bits("boolean", b"\x02"), "invalid_bool")

    def contract_bad(kind):
        def change(folder, c, m, h, payload):
            if kind == "unbound":
                c["binding"] = "UNBOUND"
            elif kind == "count":
                c["limits"]["tensor_count"] = 1
            elif kind == "path":
                c["files"]["../escape.safetensors"] = c["files"].pop("model.safetensors")
            elif kind == "cycle":
                c["aliases"]["parameter.shared_weight"] = "parameter.shared_weight"
            elif kind == "aliasstored":
                c["aliases"] = {"scalar": "parameter.weight"}
            elif kind == "overflow":
                c["tensors"]["parameter.weight"]["shape"] = [64] * 8
            write(folder, c, m, h, payload, keep_length=(kind == "path"))
        return change
    reject("real_UNBOUND_contract_fails_closed", contract_bad("unbound"), "contract_UNBOUND")
    reject("tensor_count_limit", contract_bad("count"), "tensor_count")
    reject("path_traversal_contract_member", contract_bad("path"), "filename")
    reject("shared_alias_cycle", contract_bad("cycle"), "alias_binding")
    reject("alias_conflicts_with_stored_tensor", contract_bad("aliasstored"), "alias_binding")
    reject("bounded_dimension_product_overflow", contract_bad("overflow"), "tensor_size")
    reject("unexpected_file", lambda f, c, m, h, p: (f / "export" / "loader.py").write_bytes(b"# never execute"), "stage_members")
    reject("unexpected_directory", lambda f, c, m, h, p: (f / "export" / "extra").mkdir(), "stage_members")
    reject("oversized_manifest_actual_small_fixture", lambda f, c, m, h, p:
           (f / "export" / "manifest.json").write_bytes(b" " * 16385), "manifest_size")

    folder, c, m, h, p = fixture(root, "hardlink_rejected")
    os.link(folder / "export" / "model.safetensors", folder / "harmless-extra-link")
    try:
        invoke(folder)
    except v.Rejected as error:
        assert str(error) == "not_regular_single_link"
        passed("actual_host_hardlink_rejected", detail=str(error))
    else:
        raise AssertionError("hardlink accepted")

    folder, c, m, h, p = fixture(root, "reparse_bit_unit_fixture")
    actual_stat = os.lstat
    class ArtificialInfo:
        st_mode = stat_mode = 0o100644
        st_file_attributes = 0x400
    def synthetic_stat(path):
        if Path(path) == folder / "export" / "model.safetensors":
            return ArtificialInfo()
        return actual_stat(path)
    with patch.object(v.os, "lstat", side_effect=synthetic_stat):
        try:
            invoke(folder)
        except v.Rejected as error:
            assert str(error) == "linked_path"
            passed("reparse_attribute_unit_rejection_not_actual_junction_test", detail=str(error))
        else:
            raise AssertionError("reparse bit accepted")

    folder, c, m, h, p = fixture(root, "deadline_rejection")
    with patch.object(v.time, "monotonic", side_effect=[0.0, 6.0]):
        try:
            invoke(folder)
        except v.Rejected as error:
            assert str(error) == "time_limit"
            passed("cooperative_deadline_artificial_clock_rejection", detail=str(error))
        else:
            raise AssertionError("expired deadline accepted")
    try:
        invoke(folder, max_bytes=32)
    except v.Rejected as error:
        assert str(error) == "total_size"
        passed("caller_output_byte_cap_rejection", detail=str(error))
    else:
        raise AssertionError("byte cap accepted")

    folder, c, m, h, p = fixture(root, "independent_cli_valid")
    cli_started = time.monotonic()
    child = subprocess.run([PYTHON, "-I", "-B", str(HERE / "validator.py"),
                            "--contract", str(folder / "contract.json"), "--stage", str(folder / "export"),
                            "--max-bytes", "65536", "--max-seconds", "5"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False,
                           env={**os.environ, "OMP_NUM_THREADS": "4", "OPENBLAS_NUM_THREADS": "4"})
    cli_elapsed = time.monotonic() - cli_started
    assert child.returncode == 0 and not child.stderr and len(child.stdout) < 4096
    assert json.loads(child.stdout)["status"] == "DATA_ONLY_VALIDATED"
    passed("standalone_isolated_import_search_cli_data_only", detail={"wall_seconds": cli_elapsed})

    # No artificial forwards: Pro V1 narrowed this step to parser/schema/byte equality.
    # Guest containment, actual junction/ancestor races and runtime tests remain pending.
    result = dict(study="WM-DIAG0-A2-C0-V1", attempt=sys.argv[1], status="PASSED",
                  checks=len(checks), results=checks, elapsed_seconds=time.monotonic() - started,
                  fixture_and_source_tests_only=True, guest_containment_tested=False,
                  actual_symlink_or_junction_tested=False, actual_checkpoint_parity=False,
                  real_checkpoint_access=False, model_forwards=False, gate_ready=False,
                  safetensors_dependency_installed=False, python_version=sys.version,
                  literal_oracle_tensor_count=len(LITERALS), cli_wall_seconds=cli_elapsed)
    (root / "TEST-RECEIPT.json").write_bytes(json.dumps(result, indent=2, allow_nan=False).encode())
    print(json.dumps({key: value for key, value in result.items() if key != "results"}, sort_keys=True))


if __name__ == "__main__":
    main()
