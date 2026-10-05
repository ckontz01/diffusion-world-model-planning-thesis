"""V1 data-only strict subset of Safetensors. No model/pickle imports or construction.

The expected contract is reviewer-trusted, NOT a converter-produced oracle.
Directory inputs must be locally staged regular files; this is not guest isolation.
"""
import argparse
import contextlib
import hashlib
import json
import math
import os
import re
import stat
import struct
import sys
import time
from pathlib import Path

MAX_CONTRACT = 262144
HARD = dict(total_bytes=536870912, manifest_bytes=262144, header_bytes=262144,
            tensor_count=8192, rank=8, dimension=1000000, seconds=120)
DTYPES = {"BOOL": 1, "I8": 1, "U8": 1, "I16": 2, "U16": 2,
          "I32": 4, "U32": 4, "I64": 8, "U64": 8,
          "BF16": 2, "F16": 2, "F32": 4, "F64": 8}
FLOAT_BITS = {"BF16": (16, 7, 8), "F16": (16, 10, 5),
              "F32": (32, 23, 8), "F64": (64, 52, 11)}
NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.]{0,159}\Z")
FILE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\.safetensors\Z")
HEX = re.compile(r"[0-9a-f]{64}\Z")
ENUM = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
ROLES = {"parameter", "persistent_buffer", "nonpersistent_buffer", "unregistered_tensor"}


class Rejected(Exception):
    pass


def require(ok, code):
    if not ok:
        raise Rejected(code)


def exact(obj, keys, code):
    require(type(obj) is dict and set(obj) == set(keys), code)


def integer(value, lo, hi, code):
    require(type(value) is int and lo <= value <= hi, code)
    return value


def digest(value, code):
    require(type(value) is str and HEX.fullmatch(value), code)
    return value


def name(value):
    require(type(value) is str and NAME.fullmatch(value), "identifier")
    return value


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def parse_json(raw, cap):
    require(type(raw) is bytes and 0 < len(raw) <= cap, "json_size")
    # Bound nesting BEFORE the standard JSON parser recurses. Ignore braces in strings.
    depth = 0
    quoted = escaped = False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            require(depth <= 24, "json_depth")
        elif byte in (93, 125):
            depth -= 1
            require(depth >= 0, "json_depth")
    require(depth == 0 and not quoted, "json_syntax")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Rejected("json_nonfinite")))
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        raise Rejected("json_syntax") from None


def config(value, depth=0):
    require(depth <= 12, "configuration_depth")
    if type(value) is dict:
        require(len(value) <= 128, "configuration_count")
        for key, item in value.items():
            name(key)
            config(item, depth + 1)
    elif type(value) is list:
        require(len(value) <= 128, "configuration_count")
        for item in value:
            config(item, depth + 1)
    elif type(value) is str:
        require(ENUM.fullmatch(value), "configuration_string")
    elif type(value) is float:
        require(math.isfinite(value), "configuration_nonfinite")
    else:
        require(type(value) in (bool, int) and
                (type(value) is bool or abs(value) <= 2**53), "configuration_type")


def identical(a, b):
    # Python equality alone would incorrectly equate true with 1 and 1 with 1.0.
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return set(a) == set(b) and all(identical(a[k], b[k]) for k in a)
    if type(a) is list:
        return len(a) == len(b) and all(identical(x, y) for x, y in zip(a, b))
    if type(a) is float:
        return struct.pack("<d", a) == struct.pack("<d", b)
    return a == b


def byte_size(dtype, shape, limits):
    require(dtype in DTYPES, "unsupported_dtype")
    require(type(shape) is list and len(shape) <= limits["rank"], "rank")
    # Inspect every dimension, even after a zero (never permit [0, HUGE]).
    dims = [integer(x, 0, limits["dimension"], "dimension") for x in shape]
    count = 0 if 0 in dims else 1
    if count:
        for dim in dims:
            require(count <= limits["total_bytes"] // DTYPES[dtype] // max(1, dim), "tensor_size")
            count *= dim
    return count * DTYPES[dtype]


def contract_checked(c):
    exact(c, ("version", "binding", "limits", "input_artifacts", "files", "tensors",
              "aliases", "configuration"), "contract_fields")
    require(type(c["version"]) is int and c["version"] == 1, "contract_version")
    require(c["binding"] == "BOUND", "contract_UNBOUND")
    exact(c["limits"], HARD, "limit_fields")
    for key, maximum in HARD.items():
        integer(c["limits"][key], 1, maximum, "limit_range")
    exact_artifacts(c["input_artifacts"])
    config(c["configuration"])
    require(type(c["configuration"]) is dict, "configuration_root")
    require(type(c["files"]) is dict and 1 <= len(c["files"]) <= 8, "files_count")
    declared_sum = 0
    for filename, item in c["files"].items():
        require(type(filename) is str and FILE.fullmatch(filename), "filename")
        exact(item, ("bytes", "sha256"), "file_contract_fields")
        declared_sum += integer(item["bytes"], 10, c["limits"]["total_bytes"], "file_size")
        if item["sha256"] is not None:
            digest(item["sha256"], "file_hash")
    require(declared_sum <= c["limits"]["total_bytes"], "total_size")
    require(type(c["tensors"]) is dict and
            1 <= len(c["tensors"]) <= c["limits"]["tensor_count"], "tensor_count")
    referenced = set()
    for key, item in c["tensors"].items():
        name(key)
        exact(item, ("file", "dtype", "shape", "role", "nonfinite", "sha256"), "tensor_contract_fields")
        require(item["file"] in c["files"] and item["role"] in ROLES, "tensor_contract_binding")
        byte_size(item["dtype"], item["shape"], c["limits"])
        require(item["nonfinite"] in ("finite", "allow_negative_infinity"), "nonfinite_policy")
        require(item["nonfinite"] == "finite" or item["dtype"] in FLOAT_BITS, "nonfinite_dtype")
        if item["sha256"] is not None:
            digest(item["sha256"], "tensor_hash")
        referenced.add(item["file"])
    require(referenced == set(c["files"]), "empty_file_contract")
    require(type(c["aliases"]) is dict and len(c["aliases"]) <= c["limits"]["tensor_count"], "alias_count")
    for alias, target in c["aliases"].items():
        name(alias)
        name(target)
        # Only a one-hop alias to a stored canonical tensor. No duplicate data or cycles.
        require(alias not in c["tensors"] and target in c["tensors"], "alias_binding")
    return c


def exact_artifacts(value):
    require(type(value) is dict and 1 <= len(value) <= 16, "artifact_count")
    for key, item in value.items():
        name(key)
        exact(item, ("bytes", "sha256"), "artifact_fields")
        integer(item["bytes"], 1, 2**40, "artifact_size")
        digest(item["sha256"], "artifact_hash")


def no_links(path):
    require(path.is_absolute(), "absolute_path_required")
    # No UNC/network roots, alternate data streams, links, junctions or reparse points.
    if os.name == "nt":
        require(not str(path).startswith("\\\\") and ":" not in str(path)[2:], "local_path_required")
    for parent in reversed((path, *path.parents)):
        info = os.lstat(parent)
        require(not stat.S_ISLNK(info.st_mode) and
                not getattr(info, "st_file_attributes", 0) & 0x400, "linked_path")


@contextlib.contextmanager
def locked_open(path, directory=False, root=None):
    """Windows handles deny write/delete sharing and verify final, local handle path.

    POSIX fallback uses O_NOFOLLOW. Concurrent hostile ancestor mutation on POSIX is
    outside this host-staging profile; callers must stage into a reviewer-owned tree.
    """
    no_links(path)
    if os.name == "nt":
        import ctypes
        import msvcrt
        from ctypes import wintypes
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        create = k.CreateFileW
        create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                           wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
        create.restype = wintypes.HANDLE
        close = k.CloseHandle
        close.argtypes = (wintypes.HANDLE,)
        close.restype = wintypes.BOOL
        final = k.GetFinalPathNameByHandleW
        final.argtypes = (wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD)
        final.restype = wintypes.DWORD
        flags = 0x00200000 | (0x02000000 if directory else 0x08000000)
        handle = create(str(path), 0x80 if directory else 0x80000000, 1, None, 3, flags, None)
        require(handle != wintypes.HANDLE(-1).value, "open_denied")
        owned = True
        try:
            buf = ctypes.create_unicode_buffer(32768)
            length = final(handle, buf, len(buf), 0)
            require(0 < length < len(buf), "handle_path")
            resolved = buf.value
            require(resolved.startswith("\\\\?\\") and not resolved.startswith("\\\\?\\UNC\\"), "handle_local_path")
            resolved = Path(resolved[4:])
            require(os.path.normcase(str(resolved)) == os.path.normcase(str(path)), "handle_path_binding")
            no_links(path)
            if root is not None:
                require(resolved.parent == root, "outside_stage")
            if directory:
                require(stat.S_ISDIR(os.lstat(path).st_mode), "stage_not_directory")
                yield None
            else:
                fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
                owned = False
                with os.fdopen(fd, "rb") as stream:
                    require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode) and
                            os.fstat(stream.fileno()).st_nlink == 1, "not_regular_single_link")
                    yield stream
        finally:
            if owned:
                close(handle)
    else:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        if directory:
            flags |= getattr(os, "O_DIRECTORY", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") if not directory else contextlib.nullcontext(None) as stream:
            try:
                info = os.fstat(fd)
                require(stat.S_ISDIR(info.st_mode) if directory else
                        stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "not_regular_single_link")
                yield stream
            finally:
                if directory:
                    os.close(fd)


def check_numeric(raw, dtype, policy):
    if dtype == "BOOL":
        require(all(x in (0, 1) for x in raw), "invalid_bool")
    if dtype not in FLOAT_BITS:
        return
    bits, frac, exp = FLOAT_BITS[dtype]
    exp_mask = ((1 << exp) - 1) << frac
    negative_inf = (1 << (bits - 1)) | exp_mask
    width = bits // 8
    for position in range(0, len(raw), width):
        word = int.from_bytes(raw[position:position + width], "little")
        if word & exp_mask == exp_mask:
            require(policy == "allow_negative_infinity" and word == negative_inf, "nonfinite_tensor")


def validate(expected_contract, stage, max_bytes, max_seconds):
    started = time.monotonic()
    require(type(max_seconds) in (int, float) and math.isfinite(max_seconds) and
            0 < max_seconds <= HARD["seconds"], "caller_time_limit")
    integer(max_bytes, 1, HARD["total_bytes"], "caller_byte_limit")
    deadline = started + max_seconds

    def tick():
        require(time.monotonic() <= deadline, "time_limit")

    expected_contract, stage = Path(expected_contract).absolute(), Path(stage).absolute()
    with locked_open(expected_contract) as stream:
        require(os.fstat(stream.fileno()).st_size <= MAX_CONTRACT, "contract_size")
        c = contract_checked(parse_json(stream.read(MAX_CONTRACT + 1), MAX_CONTRACT))
    deadline = min(deadline, started + c["limits"]["seconds"])
    byte_cap = min(max_bytes, c["limits"]["total_bytes"])
    tick()
    with contextlib.ExitStack() as stack:
        stack.enter_context(locked_open(stage, directory=True))
        allowed = {"manifest.json", *c["files"]}
        # Stop enumeration at the declared bound; don't materialize an attacker-sized tree.
        found = set()
        total = 0
        with os.scandir(stage) as entries:
            for entry in entries:
                tick()
                require(entry.name in allowed and entry.name not in found, "stage_members")
                require(entry.is_file(follow_symlinks=False), "stage_not_file")
                found.add(entry.name)
                total += entry.stat(follow_symlinks=False).st_size
                require(total <= byte_cap, "total_size")
        require(found == allowed, "stage_members")
        streams = {filename: stack.enter_context(locked_open(stage / filename, root=stage))
                   for filename in sorted(allowed)}
        actual_total = sum(os.fstat(s.fileno()).st_size for s in streams.values())
        require(actual_total <= byte_cap, "total_size")
        manifest = streams["manifest.json"]
        require(os.fstat(manifest.fileno()).st_size <= c["limits"]["manifest_bytes"], "manifest_size")
        m = parse_json(manifest.read(c["limits"]["manifest_bytes"] + 1), c["limits"]["manifest_bytes"])
        exact(m, ("version", "input_artifacts", "configuration", "aliases", "file_sha256", "tensor_sha256"), "manifest_fields")
        require(type(m["version"]) is int and m["version"] == 1, "manifest_version")
        exact_artifacts(m["input_artifacts"])
        config(m["configuration"])
        require(identical(m["input_artifacts"], c["input_artifacts"]), "artifact_binding")
        require(identical(m["configuration"], c["configuration"]), "configuration_binding")
        require(identical(m["aliases"], c["aliases"]), "alias_binding")
        exact(m["file_sha256"], c["files"], "file_hash_members")
        exact(m["tensor_sha256"], c["tensors"], "tensor_hash_members")
        for value in (*m["file_sha256"].values(), *m["tensor_sha256"].values()):
            digest(value, "manifest_hash")
        accepted = {}
        file_hashes = {}
        for filename, file_spec in sorted(c["files"].items()):
            tick()
            s = streams[filename]
            before = os.fstat(s.fileno())
            require(before.st_size == file_spec["bytes"], "file_length")
            prefix = s.read(8)
            require(len(prefix) == 8, "truncated_prefix")
            n = struct.unpack("<Q", prefix)[0]
            require(2 <= n <= c["limits"]["header_bytes"] and n <= before.st_size - 8, "header_size")
            header_raw = s.read(n)
            require(len(header_raw) == n and header_raw.startswith(b"{"), "header_encoding")
            header = parse_json(header_raw, c["limits"]["header_bytes"])
            wanted = {key: item for key, item in c["tensors"].items() if item["file"] == filename}
            exact(header, wanted, "tensor_members")  # __metadata__ is intentionally NOT allowed.
            require(len(header) <= c["limits"]["tensor_count"], "tensor_count")
            intervals = []
            payload_bytes = before.st_size - 8 - n
            for key, info in header.items():
                tick()
                name(key)
                exact(info, ("dtype", "shape", "data_offsets"), "tensor_header_fields")
                require(type(info["dtype"]) is str, "dtype_type")
                size = byte_size(info["dtype"], info["shape"], c["limits"])
                require(identical(info["dtype"], wanted[key]["dtype"]) and
                        identical(info["shape"], wanted[key]["shape"]), "tensor_architecture")
                offsets = info["data_offsets"]
                require(type(offsets) is list and len(offsets) == 2, "offset_fields")
                lo, hi = [integer(x, 0, payload_bytes, "offset_range") for x in offsets]
                require(hi >= lo and hi - lo == size, "offset_size")
                intervals.append((lo, hi, key))
            # Include empty tensors at valid coverage boundaries; no overlap, holes or tail.
            cursor = 0
            for lo, hi, key in sorted(intervals):
                require(lo == cursor, "coverage")
                cursor = hi
            require(cursor == payload_bytes, "coverage")
            whole = hashlib.sha256(prefix + header_raw)
            for lo, hi, key in sorted(intervals):
                tensor_hash = hashlib.sha256()
                left = hi - lo
                spec = wanted[key]
                while left:
                    tick()
                    block = s.read(min(65536, left))
                    require(block and len(block) % DTYPES[spec["dtype"]] == 0, "truncated_tensor")
                    whole.update(block)
                    tensor_hash.update(block)
                    check_numeric(block, spec["dtype"], spec["nonfinite"])
                    left -= len(block)
                h = tensor_hash.hexdigest()
                require(h == m["tensor_sha256"][key], "tensor_manifest_hash")
                require(spec["sha256"] is None or h == spec["sha256"], "tensor_expected_hash")
                accepted[key] = {"dtype": spec["dtype"], "shape": spec["shape"],
                                 "role": spec["role"], "bytes": hi - lo, "sha256": h}
            require(s.read(1) == b"", "trailing_bytes")
            h = whole.hexdigest()
            require(h == m["file_sha256"][filename], "file_manifest_hash")
            require(file_spec["sha256"] is None or h == file_spec["sha256"], "file_expected_hash")
            after = os.fstat(s.fileno())
            require((before.st_size, before.st_mtime_ns, before.st_ino) ==
                    (after.st_size, after.st_mtime_ns, after.st_ino), "file_changed")
            file_hashes[filename] = h
        tick()
        require(set(accepted) == set(c["tensors"]), "missing_state")
    return {"status": "DATA_ONLY_VALIDATED", "version": 1,
            "contract_sha256": hashlib.sha256(json.dumps(c, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "stage_bytes": actual_total, "tensor_count": len(accepted), "files": file_hashes,
            "tensors": accepted, "aliases": c["aliases"], "elapsed_seconds": time.monotonic() - started,
            "gate_ready": False, "checkpoint_loaded": False, "model_constructed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--max-bytes", type=int, required=True)
    parser.add_argument("--max-seconds", type=float, required=True)
    args = parser.parse_args()
    try:
        result = validate(args.contract, args.stage, args.max_bytes, args.max_seconds)
        # Avoid unbounded stdout even for a high-tensor-count accepted report.
        result.pop("tensors")
        print(json.dumps(result, allow_nan=False, sort_keys=True))
    except (Rejected, OSError, ValueError, TypeError, KeyError, OverflowError) as error:
        print(json.dumps({"status": "REJECTED", "reason": str(error) if isinstance(error, Rejected) else
                          type(error).__name__, "gate_ready": False}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
