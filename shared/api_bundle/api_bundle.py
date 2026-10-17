#!/usr/bin/env python3
"""Compare OpenAPI JSON inside ZIP snapshots without extracting any member."""
import argparse
import hashlib
import hmac
import io
import json
import math
from pathlib import Path
import re
import sys
import time
import zipfile
import zlib

from vendor import apidelta, oauthcheck, schemecheck, servercheck, paramcheck, statuscheck, fallbackheaders, dispatchcheck, safezip, zipgate

MAX_ARCHIVE = 32 * 1024 * 1024


def read_bundle(path, member='openapi.json', expected_sha256=None, checkpoint=lambda: None, nodes=32000, directory_bytes=2097152):
    checkpoint()
    zipgate.positive('directory_bytes', directory_bytes)
    if type(nodes) is not int or nodes <= 0:
        raise ValueError('nodes must be a positive integer')
    if expected_sha256 is not None and (
            not isinstance(expected_sha256, str)
            or re.fullmatch(r'[0-9a-fA-F]{64}', expected_sha256) is None):
        raise ValueError('expected SHA-256 must be exactly 64 hexadecimal characters')
    # Snapshot once: validation and comparison see the same bytes even if the
    # source changes later. No archive pathname is ever used as an output path.
    path = safezip.local_path(path)
    if not path.is_file():
        raise ValueError('archive must be an ordinary workspace file')
    raw = bytearray()
    with path.open('rb') as source:
        while True:
            checkpoint()
            chunk = source.read(min(65536, MAX_ARCHIVE + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) > MAX_ARCHIVE:
                raise ValueError('archive exceeds 32 MiB')
    if len(raw) > MAX_ARCHIVE:
        raise ValueError('archive exceeds 32 MiB')
    archive_sha256 = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and not hmac.compare_digest(
            archive_sha256, expected_sha256.lower()):
        raise ValueError('archive SHA-256 differs from approved digest')
    limits = argparse.Namespace(entries=1000, file_bytes=16*1024*1024,
                                total_bytes=64*1024*1024, ratio=200)
    preflight = zipgate.directory_gate(raw, entries=limits.entries,
                                       directory_bytes=directory_bytes, checkpoint=checkpoint)
    selected = None
    inventory = []
    actual_total = 0
    checkpoint()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries, _ = safezip.inventory(archive, limits, checkpoint, node_limit=nodes)
        for info, name in entries:
            checkpoint()
            if info.is_dir():
                continue
            if name == member and info.file_size > apidelta.MAX_BYTES:
                raise ValueError('selected description exceeds 1 MiB')
            digest = hashlib.sha256()
            count = 0
            payload = bytearray() if name == member else None
            with archive.open(info) as stream:
                while True:
                    checkpoint()
                    chunk = stream.read(65536)
                    if not chunk:
                        break
                    count += len(chunk)
                    actual_total += len(chunk)
                    if count > limits.file_bytes or actual_total > limits.total_bytes:
                        raise ValueError('streamed ZIP resource limit exceeded')
                    digest.update(chunk)
                    if payload is not None:
                        if count > apidelta.MAX_BYTES:
                            raise ValueError('selected description exceeds 1 MiB')
                        payload.extend(chunk)
            if count != info.file_size:
                raise ValueError('declared and actual member size differ')
            inventory.append({'path': name, 'bytes': count, 'sha256': digest.hexdigest()})
            if payload is not None:
                selected = bytes(payload)
    checkpoint()
    if selected is None:
        raise ValueError('selected description is missing or is a directory')
    obj = json.loads(selected, object_pairs_hook=apidelta.pairs,
                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError('non-finite JSON')))
    apidelta.validate(obj)
    return obj, {'archive_sha256': archive_sha256,
                 'approved_sha256_checked': expected_sha256 is not None,
                 'preflight': preflight,
                 'member': member, 'member_sha256': hashlib.sha256(selected).hexdigest(),
                 'checked_files': inventory, 'all_payloads_crc_checked': True}


def compare(old, new, member='openapi.json', old_sha256=None, new_sha256=None,
            seconds=None, cancelled=None, nodes=32000, directory_bytes=2097152,
            oauth=False, servers=False, parameters=False, statuses=False, fallback_headers=False,
            dispatch=False):
    if seconds is not None:
        try:
            valid_seconds = (not isinstance(seconds, bool)
                             and isinstance(seconds, (int, float))
                             and math.isfinite(seconds) and seconds > 0)
        except OverflowError:
            valid_seconds = False
        if not valid_seconds:
            raise ValueError('seconds must be a finite positive number')
    if cancelled is not None and not callable(cancelled):
        raise ValueError('cancelled must be callable')
    deadline = time.monotonic() + seconds if seconds is not None else None

    def checkpoint():
        if cancelled is not None and cancelled():
            raise ValueError('operation cancelled')
        if deadline is not None and time.monotonic() >= deadline:
            raise ValueError('operation time budget exceeded')

    a, before = read_bundle(old, member, old_sha256, checkpoint, nodes, directory_bytes)
    b, after = read_bundle(new, member, new_sha256, checkpoint, nodes, directory_bytes)
    checkpoint()
    report = (dispatchcheck if dispatch else fallbackheaders if fallback_headers else
              statuscheck if statuses else paramcheck if parameters else servercheck if servers else
              oauthcheck if oauth else schemecheck).compare(a, b)
    checkpoint()
    report['bundle_inputs'] = {'old': before, 'new': after}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('old', help='old workspace ZIP')
    parser.add_argument('new', help='new workspace ZIP')
    parser.add_argument('--member', default='openapi.json', help='exact member name in both ZIPs')
    parser.add_argument('--old-sha256', help='require these exact approved old archive bytes')
    parser.add_argument('--new-sha256', help='require these exact approved new archive bytes')
    parser.add_argument('--nodes', type=int, default=32000, help='maximum distinct member paths and implicit parents per archive')
    parser.add_argument('--directory-bytes', type=int, default=2097152, help='maximum ZIP central directory bytes before parsing, per archive')
    parser.add_argument('--seconds', type=float, help='cooperative time budget for the whole comparison')
    parser.add_argument('--oauth', action='store_true', help='also check declared OAuth flow and acquisition continuity')
    parser.add_argument('--servers', action='store_true', help='also check effective server destinations; includes OAuth checks')
    parser.add_argument('--parameters', action='store_true', help='also check parameter wire formats, response headers and operation IDs; includes server and OAuth checks')
    parser.add_argument('--statuses', action='store_true', help='also check response status fallbacks; includes parameter, server and OAuth checks')
    parser.add_argument('--fallback-headers', action='store_true', help='also check response headers across status overrides; includes all earlier analyzers')
    parser.add_argument('--dispatch', action='store_true', help='also compare explicit discriminator mapping targets; includes all earlier analyzers')
    args = parser.parse_args()
    try:
        report = compare(args.old, args.new, args.member, args.old_sha256,
                         args.new_sha256, args.seconds, nodes=args.nodes,
                         directory_bytes=args.directory_bytes, oauth=args.oauth, servers=args.servers, parameters=args.parameters, statuses=args.statuses, fallback_headers=args.fallback_headers, dispatch=args.dispatch)
        print(json.dumps(report, indent=2, allow_nan=False))
        return {'breaking': 1, 'review_required': 3, 'no_detected_breakage': 0}[report['status']]
    except (ValueError, OSError, RuntimeError, EOFError, zipfile.BadZipFile,
            NotImplementedError, zlib.error, RecursionError, TypeError, KeyError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    sys.exit(main())
