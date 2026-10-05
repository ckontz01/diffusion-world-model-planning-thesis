"""Read-only authentication of three OS-preparation tools, not research objects."""
import hashlib
import json
import pathlib
import subprocess

RELEASE = pathlib.Path('/var/lib/apt/lists/archive.ubuntu.com_ubuntu_dists_noble-updates_InRelease')
INDEX = pathlib.Path('/var/lib/apt/lists/archive.ubuntu.com_ubuntu_dists_noble-updates_main_binary-amd64_Packages')
KEYRING = '/usr/share/keyrings/ubuntu-archive-keyring.gpg'
NAMES = ('qemu-utils', 'libaio1t64', 'liburing2')


def main():
    verified = subprocess.run(['gpgv', '--status-fd', '1', '--keyring', KEYRING, str(RELEASE)], capture_output=True, text=True, timeout=10, check=True)
    if len(verified.stdout) + len(verified.stderr) > 32768 or '[GNUPG:] VALIDSIG ' not in verified.stdout:
        raise ValueError('signature verification unavailable')
    release = RELEASE.read_bytes()
    index = INDEX.read_bytes()
    if len(release) > 262144 or len(index) > 10000000:
        raise ValueError('cached metadata exceeds bounds')
    sha = hashlib.sha256(index).hexdigest()
    expected = f' {sha} {len(index):16d} main/binary-amd64/Packages'
    # Release spacing is publisher-defined; parse the SHA256 section explicitly.
    entries = []
    in_sha256 = False
    for line in release.decode('utf-8').splitlines():
        if line == 'SHA256:':
            in_sha256 = True
        elif in_sha256 and not line.startswith(' '):
            in_sha256 = False
        elif in_sha256:
            parts = line.split()
            if len(parts) == 3 and parts[2] == 'main/binary-amd64/Packages':
                entries.append(parts)
    if entries != [[sha, str(len(index)), 'main/binary-amd64/Packages']]:
        raise ValueError('signed release does not authenticate exact cached package index')
    records = []
    for block in index.decode('utf-8').split('\n\n'):
        fields = {}
        for line in block.splitlines():
            if line and not line[0].isspace() and ': ' in line:
                k, v = line.split(': ', 1)
                if k in fields:
                    raise ValueError('duplicate package field')
                fields[k] = v
        if fields.get('Package') in NAMES and fields.get('Architecture') == 'amd64':
            records.append({k: fields.get(k) for k in ('Package', 'Version', 'Filename', 'Size', 'SHA256', 'Installed-Size', 'Depends')})
    if len(records) != 3 or {r['Package'] for r in records} != set(NAMES):
        raise ValueError('missing or duplicate package identities')
    for record in records:
        if not record['Filename'].startswith('pool/main/') or '..' in record['Filename'] or int(record['Size']) > 3000000:
            raise ValueError('unsafe or oversized package identity')
    print(json.dumps({'mode': 'READ_ONLY_SIGNED_CACHED_OS_TOOL_METADATA', 'release_SHA256': hashlib.sha256(release).hexdigest(), 'index_SHA256': sha, 'index_bytes': len(index), 'gpg_validsig_status': [line for line in verified.stdout.splitlines() if line.startswith('[GNUPG:] VALIDSIG ')], 'packages': records, 'installed_or_executed_new_tool': False}, indent=2))


if __name__ == '__main__':
    main()
