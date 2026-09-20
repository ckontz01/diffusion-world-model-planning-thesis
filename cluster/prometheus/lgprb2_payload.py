"""RB2-only lossless payload formatting; historical/control writers unchanged."""
import json
from pathlib import Path


def write_payload(path, value):
    """Exclusive UTF-8/LF JSON; only whitespace differs from the old writer."""
    with Path(path).open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, sort_keys=True, separators=(',', ':'), allow_nan=False)
        stream.write('\n')


def seal_bytes(root):
    """Exact Linux seal length before exclusive creation (SHA hex + path + LF)."""
    root = Path(root)
    return sum(64 + 2 + len(p.relative_to(root).as_posix().encode('utf8')) + 1
               for p in root.rglob('*') if p.is_file())
