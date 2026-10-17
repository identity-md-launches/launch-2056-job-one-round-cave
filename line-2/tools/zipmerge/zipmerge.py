#!/usr/bin/env python3
"""Plan or publish one collision-free tree from several approved ZIP archives."""
import argparse
import json
import math
from pathlib import Path
import re
import stat
import sys
import tempfile
import time
import zipfile
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'zipgate'))
from zipgate import Rejected, local_path, positive, process as gate_process


def process(archives, output=None, *, max_archives=32, merge_entries=1000,
            merge_nodes=32000, merge_bytes=67108864, merge_directory_bytes=2097152,
            entries=1000,
            directory_bytes=2097152, archive_bytes=33554432, nodes=32000,
            file_bytes=16777216, total_bytes=67108864, ratio=200,
            seconds=None, cancelled=None):
    """Validate all approved archives, then atomically publish their union.

    Input is a nonempty list of {'archive': path, 'sha256': reviewed digest}.
    Exact shared directories are allowed. Any repeated file, file/directory
    conflict, or case collision is refused before creating an output tree.
    The output must be absent and its parent must exist inside the workspace.
    """
    limits = dict(entries=entries, directory_bytes=directory_bytes,
                  archive_bytes=archive_bytes, nodes=nodes,
                  file_bytes=file_bytes, total_bytes=total_bytes, ratio=ratio)
    for name, value in dict(limits, max_archives=max_archives,
                            merge_entries=merge_entries, merge_nodes=merge_nodes,
                            merge_bytes=merge_bytes,
                            merge_directory_bytes=merge_directory_bytes).items():
        positive(name, value)
    if (not isinstance(archives, (list, tuple)) or not archives
            or len(archives) > max_archives):
        raise Rejected('archives must be a nonempty bounded list/tuple')
    if seconds is not None:
        try:
            valid = (not isinstance(seconds, bool) and isinstance(seconds, (int, float))
                     and math.isfinite(seconds) and seconds > 0)
        except OverflowError:
            valid = False
        if not valid:
            raise Rejected('seconds must be a finite positive number')
    if cancelled is not None and not callable(cancelled):
        raise Rejected('cancelled must be callable')
    started = time.monotonic()

    def checkpoint():
        if cancelled is not None and cancelled():
            raise Rejected('merge cancelled')
        if seconds is not None and time.monotonic() - started >= seconds:
            raise Rejected('merge time budget exceeded')
        return False

    # Validate all declarations before archive I/O or output creation.
    specs = []
    for item in archives:
        checkpoint()
        if not isinstance(item, dict) or set(item) != {'archive', 'sha256'}:
            raise Rejected('each archive needs exactly archive and sha256')
        if not isinstance(item['archive'], (str, Path)):
            raise Rejected('archive must be a workspace path')
        digest = item['sha256']
        if not isinstance(digest, str) or re.fullmatch(r'[0-9a-fA-F]{64}', digest) is None:
            raise Rejected('each archive needs an approved 64-hex SHA-256')
        specs.append((local_path(item['archive']), digest.lower()))
    target = local_path(output) if output is not None else None
    if target is not None:
        if target.exists() or target.is_symlink():
            raise Rejected('output must not already exist')
        if not target.parent.is_dir():
            raise Rejected('output parent must already exist')

    global_nodes = {}  # casefolded path -> (exact path, kind)
    used_entries = used_bytes = used_directory_bytes = 0
    inspections = []
    for source, digest in specs:
        checkpoint()
        # The gate bounds the central directory before ZIP parsing; the full
        # inspector checks every payload, including entries never copied yet.
        cap = dict(limits)
        cap['entries'] = min(entries, max(1, merge_entries - used_entries))
        cap['total_bytes'] = min(total_bytes, max(1, merge_bytes - used_bytes))
        # Even when exhausted, allow an empty central directory (zero bytes).
        # ZipGate requires a positive cap; any nonempty directory is at least
        # 46 bytes and cannot slip through this one-byte allowance.
        cap['directory_bytes'] = min(
            directory_bytes, max(1, merge_directory_bytes - used_directory_bytes))
        inspected = gate_process(source, expected_sha256=digest,
                                 cancelled=checkpoint, **cap)
        checked_entries = inspected['entries']
        used_directory_bytes += inspected['preflight']['directory_bytes']
        if used_directory_bytes > merge_directory_bytes:
            raise Rejected('merged directory byte limit exceeded')
        used_entries += len(checked_entries)
        used_bytes += inspected['total_bytes']
        if used_entries > merge_entries:
            raise Rejected('merged entry limit exceeded')
        if used_bytes > merge_bytes:
            raise Rejected('merged byte limit exceeded')
        for entry in checked_entries:
            checkpoint()
            name = entry['path']
            parts = name.split('/')
            for depth in range(1, len(parts) + 1):
                path = '/'.join(parts[:depth])
                kind = 'directory' if depth < len(parts) else entry['kind']
                key = path.casefold()
                prior = global_nodes.get(key)
                if prior is not None and (prior[0] != path or prior[1] != kind
                                          or kind == 'file'):
                    raise Rejected('merged path collision: ' + repr(path))
                if prior is None:
                    if len(global_nodes) >= merge_nodes:
                        raise Rejected('merged node limit exceeded')
                    global_nodes[key] = (path, kind)
        inspections.append(inspected)
    checkpoint()
    report = {
        'ok': True, 'mode': 'extract' if target else 'plan',
        'all_payloads_checked': True,
        'archives': [{'archive': str(source.relative_to(Path.cwd().resolve())),
                      'archive_sha256': inspected['archive_sha256'],
                      'entries': len(inspected['entries']),
                      'preflight': inspected['preflight']}
                     for (source, _), inspected in zip(specs, inspections)],
        'totals': {'archives': len(specs), 'entries': used_entries,
                   'nodes': len(global_nodes), 'uncompressed_bytes': used_bytes},
        'metadata': {'directory_bytes': used_directory_bytes,
                     'directory_byte_limit': merge_directory_bytes},
        'output': str(target.relative_to(Path.cwd().resolve())) if target else None,
    }
    if target is None:
        return report

    # A private sibling holds each validated extraction and the joined tree.
    # The destination appears only after every repeat digest/payload check and
    # every collision test has succeeded. Failure removes the private tree.
    with tempfile.TemporaryDirectory(prefix='.zipmerge-', dir=target.parent) as temporary:
        stage = Path(temporary)
        joined = stage / 'joined'
        joined.mkdir()
        for index, ((source, digest), inspected) in enumerate(zip(specs, inspections)):
            checkpoint()
            private = stage / ('source-' + str(index))
            repeated = gate_process(source, private, expected_sha256=digest,
                                    cancelled=checkpoint, **limits)
            if (repeated['entries'] != inspected['entries']
                    or repeated['total_bytes'] != inspected['total_bytes']):
                raise Rejected('archive changed between inspection and extraction')
            for entry in inspected['entries']:
                checkpoint()
                relative = Path(entry['path'])
                destination = joined / relative
                if entry['kind'] == 'directory':
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    source_file = private / relative
                    if not source_file.is_file() or source_file.is_symlink():
                        raise Rejected('staged file changed before merge')
                    if not stat.S_ISREG(source_file.stat().st_mode):
                        raise Rejected('staged file is not regular')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if destination.exists() or destination.is_symlink():
                        raise Rejected('output appeared during merge')
                    source_file.rename(destination)
        checkpoint()
        if target.exists() or target.is_symlink():
            raise Rejected('output appeared during merge')
        joined.rename(target)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('plan', 'extract'))
    parser.add_argument('output', nargs='?')
    parser.add_argument('--archive', action='append', required=True)
    parser.add_argument('--sha256', action='append', required=True)
    for name, default in [('max-archives', 32), ('merge-entries', 1000),
                          ('merge-nodes', 32000), ('merge-bytes', 67108864),
                          ('merge-directory-bytes', 2097152),
                          ('entries', 1000), ('directory-bytes', 2097152),
                          ('archive-bytes', 33554432), ('nodes', 32000),
                          ('file-bytes', 16777216), ('total-bytes', 67108864),
                          ('ratio', 200)]:
        parser.add_argument('--' + name, type=int, default=default)
    parser.add_argument('--seconds', type=float)
    args = vars(parser.parse_args())
    command, output = args.pop('command'), args.pop('output')
    paths, digests = args.pop('archive'), args.pop('sha256')
    if (command == 'extract') != (output is not None):
        parser.error('extract requires output; plan takes no output')
    if len(paths) != len(digests):
        parser.error('one --sha256 is required for each --archive')
    specs = [dict(archive=path, sha256=digest) for path, digest in zip(paths, digests)]
    try:
        result = process(specs, output, **args)
    except (ValueError, OSError, zipfile.BadZipFile, NotImplementedError,
            RuntimeError, EOFError, zlib.error) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=True))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
