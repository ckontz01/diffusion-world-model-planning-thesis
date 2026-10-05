"""Corrected bounded metadata probe; original failed probe is retained unchanged."""
import gzip
import hashlib
import json
import time
import urllib.request
from probe_vhd_header import CAP, URL, number


class PrefixReader:
    def __init__(self, response):
        self.response = response
        self.count = 0
        self.digest = hashlib.sha256()

    def read(self, size=-1):
        remaining = CAP - self.count
        if remaining == 0:
            return b''
        # gzip requests a 128 KiB buffer in this Python. Clamp the actual read
        # instead of increasing the original 64 KiB network-byte ceiling.
        requested = remaining if size < 0 else min(size, remaining)
        block = self.response.read(requested)
        self.count += len(block)
        self.digest.update(block)
        return block


def probe():
    start = time.monotonic()
    with urllib.request.urlopen(urllib.request.Request(URL, headers={'Range': 'bytes=0-65535'}), timeout=20) as response:
        if response.geturl() != URL:
            raise ValueError('unexpected redirect')
        reader = PrefixReader(response)
        with gzip.GzipFile(fileobj=reader, mode='rb') as stream:
            skipped = []
            for _ in range(4):
                if time.monotonic() - start > 30:
                    raise TimeoutError('header probe exceeded 30 seconds')
                header = stream.read(512)
                if len(header) != 512 or not any(header):
                    raise ValueError('missing tar member header')
                if sum(header[:148]) + 8 * 32 + sum(header[156:]) != number(header[148:156]):
                    raise ValueError('tar checksum mismatch')
                name = header[:100].split(b'\0', 1)[0].decode('ascii', 'strict')
                size = number(header[124:136])
                kind = header[156:157]
                if kind in (b'g', b'x', b'L'):
                    if size > 4096:
                        raise ValueError('oversized auxiliary header')
                    stream.read(((size + 511) // 512) * 512)
                    skipped.append({'name': name, 'bytes': size})
                    continue
                if kind not in (b'0', b'\0') or not name.endswith('.vhd'):
                    raise ValueError('unexpected regular member')
                return dict(url=URL, mode='PREFIX_HEADER_ONLY_NOT_FULL_IMAGE_AUTHENTICATION', http_status=response.status,
                            compressed_bytes_read=reader.count, compressed_prefix_SHA256=reader.digest.hexdigest(),
                            auxiliary_headers_skipped=skipped, member_name=name, declared_expanded_member_bytes=size,
                            existing_runtime_reservation_bytes=4000000000, member_alone_fits_runtime_reservation=size <= 4000000000,
                            payload_extracted_or_saved=False, VM_started=False, whole_image_hash_or_signature_verified=False,
                            elapsed_seconds=time.monotonic() - start)
            raise ValueError('no VHD within four-header bound')


if __name__ == '__main__':
    print(json.dumps(probe(), indent=2))
