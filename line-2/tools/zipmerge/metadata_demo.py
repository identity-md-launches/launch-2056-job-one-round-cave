#!/usr/bin/env python3
"""Replay the real shipped public API capture with a shared ZIP metadata cap."""
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from zipmerge import Rejected, local_path, process


def main():
    sources = Path(__file__).resolve().parents[1] / 'safezip'
    capture = (sources / 'imd-openapi.json').read_bytes()
    provenance = (sources / 'sample-source.json').read_bytes()
    assert hashlib.sha256(capture).hexdigest() == (
        'be142840c010710cb2a5b9e5c73e71d8e79ec4054c15661699d60bfa627be96a')
    scratch = local_path('test/scratch')
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch, prefix='merge-metadata-demo-') as temporary:
        root = Path(temporary)
        specs = []
        expected_directory_bytes = 0
        for name, data in [('openapi.json', capture), ('source.json', provenance)]:
            archive = root / (name + '.zip')
            info = zipfile.ZipInfo('docs/' + name)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.comment = b'Illustrative package review note. ' * 100
            expected_directory_bytes += 46 + len(info.filename.encode('utf8')) + len(info.comment)
            with zipfile.ZipFile(archive, 'w') as writer:
                writer.writestr(info, data)
            specs.append(dict(archive=archive,
                              sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))
        try:
            process(specs, root / 'refused',
                    merge_directory_bytes=expected_directory_bytes - 1)
        except Rejected as error:
            refusal = str(error)
        else:
            raise AssertionError('shared metadata overrun accepted')
        assert not (root / 'refused').exists()
        output = root / 'combined'
        report = process(specs, output, merge_directory_bytes=expected_directory_bytes)
        assert (output / 'docs/openapi.json').read_bytes() == capture
        assert (output / 'docs/source.json').read_bytes() == provenance
        assert report['metadata']['directory_bytes'] == expected_directory_bytes
        print(json.dumps(dict(ok=True, network_used=False,
                              historical_public_source='https://api.imd.fun/openapi.json',
                              capture_bytes=len(capture), byte_identical=True,
                              one_byte_under_refused=refusal, report=report), indent=2))


if __name__ == '__main__':
    main()
