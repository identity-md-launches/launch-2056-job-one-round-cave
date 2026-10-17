#!/usr/bin/env python3
"""Integration checks for approved ZIP snapshots and discriminator targets."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

import api_bundle as bundle
from dispatch_demo import documents


class DispatchBundleTests(unittest.TestCase):
    def setUp(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='dispatch-tests-', dir=scratch)
        self.root = Path(self.temp.name)
        _, self.old, self.new = documents()

    def tearDown(self):
        self.temp.cleanup()

    def archive(self, name, document):
        path = self.root / name
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr(zipfile.ZipInfo('docs/openapi.json'), json.dumps(document))
            archive.writestr(zipfile.ZipInfo('inert.py'), 'raise RuntimeError("never execute")')
        return path

    def pair(self, old=None, new=None):
        a = self.archive('old.zip', self.old if old is None else old)
        b = self.archive('new.zip', self.new if new is None else new)
        options = dict(member='docs/openapi.json',
            old_sha256=hashlib.sha256(a.read_bytes()).hexdigest(),
            new_sha256=hashlib.sha256(b.read_bytes()).hexdigest())
        return a, b, options

    def test_unchanged_mapping_target_change_is_found_after_approval(self):
        a, b, options = self.pair()
        earlier = bundle.compare(a, b, fallback_headers=True, **options)
        report = bundle.compare(a, b, dispatch=True, **options)
        self.assertEqual(earlier['status'], 'review_required')
        self.assertEqual(report['status'], 'breaking')
        self.assertEqual(report['dispatch_pairs'][0]['tag'], 'done')
        self.assertTrue(any(f['code'] == 'schema_type_incompatible' and
            '/mapping/done/target/' in f['location'] for f in report['findings']))
        self.assertTrue(all(v['approved_sha256_checked'] and v['all_payloads_crc_checked']
            for v in report['bundle_inputs'].values()))
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['new.zip', 'old.zip'])

    def test_unchanged_approved_capture(self):
        capture = json.loads(Path(__file__).with_name('imd-openapi.json').read_bytes())
        a, b, options = self.pair(capture, capture)
        report = bundle.compare(a, b, dispatch=True, **options)
        self.assertEqual(report['status'], 'no_detected_breakage')
        self.assertEqual(report['operations_compared'], 5)
        self.assertEqual(report['dispatch_pairs'], [])

    def test_request_narrowing_and_inherited_header_finding(self):
        old = copy.deepcopy(self.old)
        new = copy.deepcopy(old)
        op = old['paths']['/requests/quote']['post']
        op['requestBody'] = {'content': {'application/json': {'schema':
            copy.deepcopy(op['responses']['200']['content']['application/json']['schema'])}}}
        old['components']['schemas']['DispatchExample']['properties']['receipt']['enum'] = ['a', 'b']
        new = copy.deepcopy(old)
        new['components']['schemas']['DispatchExample']['properties']['receipt']['enum'] = ['a']
        new['paths']['/requests/quote']['post']['responses']['200']['headers'] = {
            'X-Receipt': {'required': True, 'schema': {'type': 'string'}}}
        a, b, options = self.pair(old, new)
        report = bundle.compare(a, b, dispatch=True, **options)
        codes = {f['code'] for f in report['findings']}
        self.assertIn('schema_enum_incompatible', codes)
        self.assertIn('response_header_added', codes)

    def test_digest_crc_and_budget_refuse_before_analysis(self):
        a, b, options = self.pair()
        with mock.patch.object(bundle.dispatchcheck, 'compare') as analyzer:
            with self.assertRaises(ValueError):
                bundle.compare(a, b, dispatch=True, **{**options, 'old_sha256': '0' * 64})
            with self.assertRaises(ValueError):
                bundle.compare(a, b, dispatch=True, directory_bytes=1, **options)
            with self.assertRaises(ValueError):
                bundle.compare(a, b, dispatch=True, nodes=1, **options)
            b.write_bytes(b.read_bytes().replace(b'never execute', b'NEVER EXECUTE'))
            with self.assertRaises(zipfile.BadZipFile):
                bundle.compare(a, b, dispatch=True,
                    **{**options, 'new_sha256': hashlib.sha256(b.read_bytes()).hexdigest()})
            analyzer.assert_not_called()

    def test_cli_exits_and_precedence(self):
        a, _, _ = self.pair(self.old, self.old)
        review = copy.deepcopy(self.old)
        review['paths']['/requests/quote']['post']['responses']['200']['content'][
            'application/json']['schema']['discriminator']['mapping'] = {}
        cases = ((self.old, 0), (self.new, 1), ({}, 2), (review, 3))
        for doc, expected in cases:
            b = self.archive('new.zip', doc)
            cmd = [sys.executable, '-B', bundle.__file__, str(a), str(b),
                '--member', 'docs/openapi.json', '--dispatch', '--fallback-headers',
                '--old-sha256', hashlib.sha256(a.read_bytes()).hexdigest(),
                '--new-sha256', hashlib.sha256(b.read_bytes()).hexdigest()]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            if expected != 2:
                self.assertTrue(json.loads(result.stdout)['extension'].startswith('dispatchcheck-v1'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
