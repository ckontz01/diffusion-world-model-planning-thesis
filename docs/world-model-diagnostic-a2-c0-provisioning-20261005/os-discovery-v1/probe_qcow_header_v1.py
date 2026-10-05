"""Read only the fixed official candidate's QCOW header; no disk payload retained."""
import hashlib
import json
import struct
import time
import urllib.request

URL = 'https://cloud-images.ubuntu.com/minimal/releases/jammy/release-20261001/ubuntu-22.04-minimal-cloudimg-amd64.img'


def probe():
    start = time.monotonic()
    request = urllib.request.Request(URL, headers={'Range': 'bytes=0-103'})
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.geturl() != URL or response.status != 206:
            raise ValueError('expected exact URL and partial response')
        prefix = response.read(104)
        if len(prefix) != 104 or prefix[:4] != b'QFI\xfb':
            raise ValueError('not a complete QCOW header')
        version = struct.unpack_from('>I', prefix, 4)[0]
        if version not in (2, 3):
            raise ValueError('unsupported QCOW header version')
        return {
            'mode': 'BOUNDED_OS_METADATA_ONLY_NOT_AUTHENTICATED_IMAGE',
            'url': URL,
            'http_status': response.status,
            'content_range': response.headers.get('Content-Range'),
            'bytes_read': len(prefix),
            'prefix_SHA256': hashlib.sha256(prefix).hexdigest(),
            'qcow_version': version,
            'declared_virtual_disk_bytes': struct.unpack_from('>Q', prefix, 24)[0],
            'declared_backing_file_offset': struct.unpack_from('>Q', prefix, 8)[0],
            'declared_backing_file_size': struct.unpack_from('>I', prefix, 16)[0],
            'full_image_hash_or_signature_verified': False,
            'payload_extracted_saved_mounted_or_executed': False,
            'VM_started': False,
            'elapsed_seconds': time.monotonic() - start,
        }


if __name__ == '__main__':
    print(json.dumps(probe(), indent=2))
