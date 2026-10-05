"""Report, not extract, the first bounded public OS tar member header."""
import gzip
import json
import time
import urllib.request
from probe_vhd_header import URL, number
from probe_vhd_header_r1 import PrefixReader


def probe():
    start = time.monotonic()
    with urllib.request.urlopen(urllib.request.Request(URL, headers={'Range': 'bytes=0-65535'}), timeout=20) as response:
        if response.geturl() != URL:
            raise ValueError('unexpected redirect')
        reader = PrefixReader(response)
        with gzip.GzipFile(fileobj=reader, mode='rb') as stream:
            header = stream.read(512)
            if len(header) != 512:
                raise ValueError('incomplete header')
            if sum(header[:148]) + 256 + sum(header[156:]) != number(header[148:156]):
                raise ValueError('tar header checksum mismatch')
            size = number(header[124:136])
            kind = header[156:157]
            real_size = number(header[483:495]) if kind == b'S' else None
            return {
                'url': URL,
                'mode': 'BOUNDED_OS_METADATA_ONLY_NOT_AUTHENTICATED_IMAGE',
                'http_status': response.status,
                'compressed_bytes_read': reader.count,
                'compressed_prefix_SHA256': reader.digest.hexdigest(),
                'first_member_name': header[:100].split(b'\0', 1)[0].decode('ascii', 'replace'),
                'tar_type_flag_hex': kind.hex(),
                'tar_magic': header[257:265].decode('ascii', 'replace'),
                'declared_stored_member_bytes': size,
                'GNU_sparse_logical_member_bytes': real_size,
                'runtime_reservation_bytes': 4000000000,
                'logical_size_alone_exceeds_runtime_reservation': real_size > 4000000000 if real_size is not None else size > 4000000000,
                'payload_extracted_saved_mounted_or_executed': False,
                'full_image_hash_or_signature_verified': False,
                'VM_started': False,
                'elapsed_seconds': time.monotonic() - start,
            }


if __name__ == '__main__':
    print(json.dumps(probe(), indent=2))
