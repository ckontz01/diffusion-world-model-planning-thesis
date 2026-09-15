"""Accepted pure infrastructure helpers, preserved separately from old snapshot.

Exact function bodies from candidate_value_dispatch.py at accepted 442c9659,
file SHA256 f75c0ff3c95af9da8197cc0b0218856f7dd8c81d2d6b36d8f8fe9f389925128a.
No old dispatcher launch/resume entry point is imported or called.
"""
import json
import os
from pathlib import Path
import stat
import candidate_value_contract as ct


def file_bytes(paths):
    total=0
    for p in paths:
        try:info=Path(p).stat()
        except FileNotFoundError:continue  # Concurrently removed temporary file.
        if stat.S_ISREG(info.st_mode):total+=info.st_size
    return total


def bytes_used(run):
    def onerror(exc):
        if not isinstance(exc,FileNotFoundError):raise exc
    return sum(file_bytes(Path(root)/name for name in names)
               for root,dirs,names in os.walk(str(run),onerror=onerror))


def technical_report(directory):
    """Authenticate all bytes; decode only top-level technical scalar fields."""
    p=Path(directory);names=set()
    for line in (p/'sha256.txt').read_text().splitlines():
        expected,name=line.split('  ',1)
        ct.require(name not in names and ct.sha(ct.child(p,name))==expected,'Resume output checksum')
        names.add(name)
    ct.require(names=={x.relative_to(p).as_posix() for x in p.rglob('*')
                      if x.is_file() and x.name!='sha256.txt'} and names,'Resume unsealed files')
    keys={'kind','index','source_sha256','capsule_sha256','technical_valid',
          'protected_payload_reads','historical_decisions_changed','maxrss_bytes',
          'bytes_before_report','reference','h'}
    out={}
    for line in (p/'REPORT.json').read_text().splitlines():
        if not line.startswith('  "'):continue
        key=line.split('"',2)[1]
        if key in keys:
            ct.require(key not in out,'Duplicate technical scalar')
            out[key]=json.loads('{'+line.strip().rstrip(',')+'}')[key]
    return out
