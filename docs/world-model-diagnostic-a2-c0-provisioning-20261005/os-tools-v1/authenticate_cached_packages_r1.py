"""Authenticate the update tool and base-release libraries without installations."""
import hashlib
import json
import pathlib
import subprocess

KEYRING = '/usr/share/keyrings/ubuntu-archive-keyring.gpg'


def authenticate(suite, names):
    base = '/var/lib/apt/lists/archive.ubuntu.com_ubuntu_dists_' + suite
    release_path = pathlib.Path(base + '_InRelease')
    index_path = pathlib.Path(base + '_main_binary-amd64_Packages')
    verified = subprocess.run(['gpgv', '--status-fd', '1', '--keyring', KEYRING, str(release_path)], capture_output=True, text=True, timeout=10, check=True)
    if len(verified.stdout) + len(verified.stderr) > 32768 or '[GNUPG:] VALIDSIG ' not in verified.stdout:
        raise ValueError('signature verification unavailable')
    release = release_path.read_bytes()
    index = index_path.read_bytes()
    if len(release) > 262144 or len(index) > 10000000:
        raise ValueError('metadata exceeds bounds')
    digest = hashlib.sha256(index).hexdigest()
    entries, in_sha256 = [], False
    for line in release.decode('utf-8').splitlines():
        if line == 'SHA256:':
            in_sha256 = True
        elif in_sha256 and not line.startswith(' '):
            in_sha256 = False
        elif in_sha256:
            parts = line.split()
            if len(parts) == 3 and parts[2] == 'main/binary-amd64/Packages':
                entries.append(parts)
    if entries != [[digest, str(len(index)), 'main/binary-amd64/Packages']]:
        raise ValueError('signed release/index mismatch')
    records = []
    for block in index.decode('utf-8').split('\n\n'):
        fields = {}
        for line in block.splitlines():
            if line and not line[0].isspace() and ': ' in line:
                key, value = line.split(': ', 1)
                if key in fields:
                    raise ValueError('duplicate package field')
                fields[key] = value
        if fields.get('Package') in names and fields.get('Architecture') == 'amd64':
            records.append({key: fields.get(key) for key in ('Package', 'Version', 'Filename', 'Size', 'SHA256', 'Installed-Size', 'Depends')})
    if len(records) != len(names) or {r['Package'] for r in records} != set(names):
        raise ValueError('missing or duplicate exact identities')
    for record in records:
        if not record['Filename'].startswith('pool/main/') or '..' in record['Filename'] or int(record['Size']) > 3000000:
            raise ValueError('unsafe or oversized identity')
    return {'suite': suite, 'release_SHA256': hashlib.sha256(release).hexdigest(), 'index_SHA256': digest, 'index_bytes': len(index), 'gpg_validsig_status': [line for line in verified.stdout.splitlines() if line.startswith('[GNUPG:] VALIDSIG ')], 'packages': records}


if __name__ == '__main__':
    print(json.dumps({'mode': 'READ_ONLY_SIGNED_CACHED_OS_TOOL_METADATA', 'sources': [authenticate('noble-updates', {'qemu-utils'}), authenticate('noble', {'libaio1t64', 'liburing2'})], 'installed_or_executed_new_tool': False}, indent=2))
