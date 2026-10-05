"""Extract exact authenticated utility/library members; never install a package."""
import hashlib
import json
import pathlib
import subprocess
import tarfile

ROOT = pathlib.Path('/mnt/c/Users/Chris/thesis-vm/wm-diag0-a2-c0-runtime-v1/os-tools-v1')
PACKAGES = (
    ('qemu-utils_8.2.2+ds-0ubuntu1.18_amd64.deb', '10695e57937d8a1d0ec6d017a6770d02353ec0c9500e4a36928230b2d39026c5', './usr/bin/qemu-img', 'bin/qemu-img', 2480872),
    ('libaio1t64_0.3.113-6build1_amd64.deb', 'b1c4ebee35cfc85481443171e6e09943f3b0b530901fdf4fd6a864e242c2a1a5', './usr/lib/x86_64-linux-gnu/libaio.so.1t64.0.2', 'lib/libaio.so.1t64', 14336),
    ('liburing2_2.5-1build1_amd64.deb', 'c2aef62accee92a06263c3ad4ef46132c13e409b54296c44792a20491830a7b0', './usr/lib/x86_64-linux-gnu/liburing.so.2.5', 'lib/liburing.so.2', 26856),
)


def main():
    if (ROOT / 'bin').exists() or (ROOT / 'lib').exists():
        raise ValueError('Selected extraction exists: reconcile, do not repeat')
    for parent in [ROOT, *ROOT.parents]:
        if parent.is_symlink():
            raise ValueError('Redirected tool root')
    for filename, digest, _, _, _ in PACKAGES:
        path = ROOT / filename
        if path.stat().st_size > 3000000 or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Package authentication mismatch')
    (ROOT / 'bin').mkdir()
    (ROOT / 'lib').mkdir()
    identities = []
    for filename, _, member_name, destination, expected_bytes in PACKAGES:
        proc = subprocess.Popen(['dpkg-deb', '--fsys-tarfile', str(ROOT / filename)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        found = 0
        with tarfile.open(fileobj=proc.stdout, mode='r|') as archive:
            for member in archive:
                if member.name != member_name:
                    continue
                found += 1
                if found != 1 or not member.isfile() or member.size != expected_bytes:
                    raise ValueError('Selected regular member identity mismatch')
                stream = archive.extractfile(member)
                data = stream.read(expected_bytes + 1)
                if len(data) != expected_bytes:
                    raise ValueError('Selected member length mismatch')
                target = ROOT / destination
                with target.open('xb') as output:
                    output.write(data)
                identities.append({'path': destination, 'bytes': len(data), 'SHA256': hashlib.sha256(data).hexdigest()})
        errors = proc.stderr.read(8193)
        if proc.wait(timeout=10) != 0 or errors or found != 1:
            raise ValueError('Package extraction error; preserve selected partials')
    print(json.dumps({'mode': 'SELECTED_AUTHENTICATED_OS_TOOL_EXTRACTION', 'members': identities, 'symlinks_created': False, 'package_hooks_or_installation': False, 'tool_executed': False, 'research_artifacts_opened': False}, indent=2))


if __name__ == '__main__':
    main()
