#!/usr/bin/env python3
"""Shared central-directory bounds, including refusal before payload parsing."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from zipmerge import Rejected, process
import zipgate


class MetadataTests(unittest.TestCase):
    def setUp(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch, prefix='merge-metadata-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.a = self.pack('a.zip', 'a', comment=b'x' * 200)
        self.b = self.pack('b.zip', 'b', comment=b'y' * 200)
        # Classic central directory: 46 fixed bytes + one-byte name + comment.
        self.each = 247

    def pack(self, filename, name=None, comment=b''):
        archive = self.root / filename
        with zipfile.ZipFile(archive, 'w') as writer:
            if name is not None:
                info = zipfile.ZipInfo(name)
                info.comment = comment
                writer.writestr(info, b'x')
        return dict(archive=archive, sha256=hashlib.sha256(archive.read_bytes()).hexdigest())

    def test_exact_boundary_extracts(self):
        output = self.root / 'out'
        result = process([self.a, self.b], output,
                         merge_directory_bytes=2 * self.each)
        self.assertEqual(result['metadata'], dict(directory_bytes=494,
                                                  directory_byte_limit=494))
        self.assertEqual((output / 'a').read_bytes(), b'x')
        self.assertEqual((output / 'b').read_bytes(), b'x')

    def test_one_byte_under_refuses_before_second_parser(self):
        output = self.root / 'out'
        with patch('zipgate.safe_process', wraps=zipgate.safe_process) as parser:
            with self.assertRaisesRegex(Rejected, 'directory byte limit'):
                process([self.a, self.b], output, merge_directory_bytes=493)
            self.assertEqual(parser.call_count, 1)
        self.assertFalse(output.exists())
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['a.zip', 'b.zip'])

    def test_first_archive_refused_before_any_parser(self):
        with patch('zipgate.safe_process') as parser:
            with self.assertRaisesRegex(Rejected, 'directory byte limit'):
                process([self.a], merge_directory_bytes=246)
            parser.assert_not_called()

    def test_empty_archive_after_exhausted_budget(self):
        empty = self.pack('empty.zip')
        result = process([self.a, empty], merge_directory_bytes=self.each)
        self.assertEqual(result['metadata']['directory_bytes'], self.each)
        self.assertEqual(result['totals']['archives'], 2)

    def test_nonempty_archive_after_exhausted_budget(self):
        with patch('zipgate.safe_process', wraps=zipgate.safe_process) as parser:
            with self.assertRaisesRegex(Rejected, 'directory byte limit'):
                process([self.a, self.b], merge_directory_bytes=self.each)
            self.assertEqual(parser.call_count, 1)

    def test_all_empty_with_one_byte_budget(self):
        empty = self.pack('empty.zip')
        self.assertEqual(process([empty, empty], merge_directory_bytes=1)
                         ['metadata']['directory_bytes'], 0)

    def test_per_archive_limit_still_applies(self):
        with self.assertRaisesRegex(Rejected, 'directory byte limit'):
            process([self.a], directory_bytes=246, merge_directory_bytes=1000)

    def test_invalid_limits_before_archive_io(self):
        for value in [0, -1, True, 1.5, '494', None]:
            with self.subTest(value=value), patch('zipmerge.gate_process') as gate:
                with self.assertRaisesRegex(Rejected, 'positive integer'):
                    process([self.a], merge_directory_bytes=value)
                gate.assert_not_called()

    def test_default_bounds_many_metadata_heavy_archives(self):
        specs = []
        for i in range(2):
            path = self.root / ('heavy' + str(i) + '.zip')
            with zipfile.ZipFile(path, 'w') as writer:
                for j in range(17):
                    info = zipfile.ZipInfo(str(i) + '/' + str(j))
                    info.comment = b'c' * 65535
                    writer.writestr(info, b'x')
            specs.append(dict(archive=path, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        # Each metadata directory fits the 2 MiB per-archive default; together
        # they exceed the new 2 MiB shared default, without big payloads.
        with self.assertRaisesRegex(Rejected, 'directory byte limit'):
            process(specs)
        result = process(specs, merge_directory_bytes=3 * 1024 * 1024)
        self.assertGreater(result['metadata']['directory_bytes'], 2 * 1024 * 1024)

    def test_cli_limit_and_report(self):
        command = [sys.executable, '-B', str(Path(__file__).with_name('zipmerge.py')),
                   'plan', '--archive', str(self.a['archive']), '--sha256', self.a['sha256'],
                   '--archive', str(self.b['archive']), '--sha256', self.b['sha256'],
                   '--merge-directory-bytes']
        good = subprocess.run(command + ['494'], capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout)['metadata']['directory_bytes'], 494)
        bad = subprocess.run(command + ['493'], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2, bad.stderr)
        self.assertFalse(json.loads(bad.stdout)['ok'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
