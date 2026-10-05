"""Bounded public OS archive header discovery; no extraction or VM execution."""
import gzip
import hashlib
import json
import time
import urllib.request

URL = ('https://cloud-images.ubuntu.com/minimal/releases/jammy/'
       'release-20261001/ubuntu-22.04-minimal-cloudimg-amd64-azure.vhd.tar.gz')
CAP = 65536


class BoundedReader:
    def __init__(self, response):
        self.response = response
        self.count = 0
        self.digest = hashlib.sha256()

    def read(self, size=-1):
        if size < 0 or size > CAP - self.count:
            raise ValueError('compressed prefix request exceeds 64 KiB cap')
        block = self.response.read(size)
        self.count += len(block)
        self.digest.update(block)
        return block


def number(field):
    if field[0] & 0x80:
        if field[0] != 0x80:
            raise ValueError('negative/unsupported base-256 tar size')
        return int.from_bytes(field[1:], 'big')
    value = field.rstrip(b'\0 ').lstrip(b' ')
    if not value or any(c not in b'01234567' for c in value):
        raise ValueError('invalid tar numeric field')
    return int(value, 8)


def probe():
    start = time.monotonic()
    request = urllib.request.Request(URL, headers={'Range': 'bytes=0-65535'})
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.geturl() != URL:
            raise ValueError('unexpected redirect')
        reader = BoundedReader(response)
        with gzip.GzipFile(fileobj=reader, mode='rb') as stream:
            skipped = []
            for _ in range(4):
                if time.monotonic() - start > 30:
                    raise TimeoutError('header discovery exceeded 30 seconds')
                header = stream.read(512)
                if len(header) != 512 or not any(header):
                    raise ValueError('missing member header')
                expected = number(header[148:156])
                if sum(header[:148]) + 8 * 32 + sum(header[156:]) != expected:
                    raise ValueError('tar header checksum mismatch')
                name = header[:100].split(b'\0', 1)[0].decode('ascii', 'strict')
                size = number(header[124:136])
                kind = header[156:157]
                if kind in (b'g', b'x', b'L'):
                    if size > 4096:
                        raise ValueError('oversized auxiliary tar header')
                    stream.read(((size + 511) // 512) * 512)
                    skipped.append({'name': name, 'bytes': size, 'kind': kind.decode()})
                    continue
                if kind not in (b'0', b'\0') or not name.endswith('.vhd'):
                    raise ValueError('unexpected first regular archive member')
                return {
                    'url': URL,
                    'mode': 'PREFIX_HEADER_ONLY_NOT_FULL_IMAGE_AUTHENTICATION',
                    'http_status': response.status,
                    'compressed_bytes_read': reader.count,
                    'compressed_prefix_SHA256': reader.digest.hexdigest(),
                    'auxiliary_headers_skipped': skipped,
                    'member_name': name,
                    'declared_expanded_member_bytes': size,
                    'existing_runtime_reservation_bytes': 4000000000,
                    'member_alone_fits_runtime_reservation': size <= 4000000000,
                    'payload_extracted_or_saved': False,
                    'VM_started': False,
                    'whole_image_hash_or_signature_verified': False,
                    'elapsed_seconds': time.monotonic() - start,
                }
            raise ValueError('no regular VHD member within four-header bound')


if __name__ == '__main__':
    print(json.dumps(probe(), indent=2))
