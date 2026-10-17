#!/usr/bin/env python3
"""DispatchCheck regressions, including an independent finite payload oracle."""
import contextlib
import copy
import io
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import dispatchcheck as tool


def union(mapping=None):
    return {'oneOf': [{'$ref': '#/components/schemas/Done'}],
            'discriminator': {'propertyName': 'kind',
                'mapping': {'done': '#/components/schemas/Done'} if mapping is None else mapping}}


def doc(direction='response', schema=None, version='3.1.0'):
    media = {'application/json': {'schema': union() if schema is None else schema}}
    operation = {'responses': {}}
    if direction == 'response':
        operation['responses'] = {'200': {'description': 'test', 'content': media}}
    else:
        operation['requestBody'] = {'content': media}
    return {'openapi': version, 'paths': {'/probe': {'post': operation}},
            'components': {'schemas': {'Done': {'type': 'object',
                'required': ['kind', 'value'], 'properties': {
                    'kind': {'type': 'string', 'enum': ['done']},
                    'value': {'type': 'integer', 'enum': [0, 1]}}}}}}


def root(d, direction='response'):
    op = d['paths']['/probe']['post']
    body = op['responses']['200'] if direction == 'response' else op['requestBody']
    return body['content']['application/json']['schema']


def target(d):
    return d['components']['schemas']['Done']


def codes(r):
    return {f['code'] for f in r['findings']}


def target_break(r, code='schema_enum_incompatible'):
    return any(f['code'] == code and '/mapping/' in f['location'] for f in r['findings'])


class Tests(unittest.TestCase):
    def test_unchanged_mapping_target_response_expands(self):
        a = doc()
        b = copy.deepcopy(a)
        target(b)['properties']['value']['enum'] += [2]
        r = tool.compare(a, b)
        self.assertTrue(target_break(r))
        self.assertEqual(r['dispatch_pairs'][0]['old_target'], r['dispatch_pairs'][0]['new_target'])
        self.assertIn('document_metadata_changed', codes(r))

    def test_finite_payload_oracle_both_directions(self):
        # These singleton unions accept exactly the enumerated integer payloads.
        # Evaluate actual old/new payload sets, independently of analyzer helpers.
        subsets = [set(c) for n in range(1, 4) for c in itertools.combinations(range(3), n)]
        cases = 0
        for direction, old_values, new_values in itertools.product(('request', 'response'), subsets, subsets):
            a = doc(direction)
            b = copy.deepcopy(a)
            target(a)['properties']['value']['enum'] = sorted(old_values)
            target(b)['properties']['value']['enum'] = sorted(new_values)
            old_payloads = {('done', v) for v in range(3) if v in old_values}
            new_payloads = {('done', v) for v in range(3) if v in new_values}
            unsafe = bool(old_payloads - new_payloads) if direction == 'request' else bool(new_payloads - old_payloads)
            self.assertEqual(target_break(tool.compare(a, b)), unsafe,
                             (direction, old_values, new_values))
            cases += 1
        self.assertEqual(cases, 98)

    def test_property_name_and_presence_need_review(self):
        a = doc()
        for mutation, expected in ((lambda s: s['discriminator'].update(propertyName='type'),
                                     'discriminator_property_changed'),
                                    (lambda s: s.pop('discriminator'),
                                     'discriminator_presence_changed')):
            b = copy.deepcopy(a)
            mutation(root(b))
            r = tool.compare(a, b)
            self.assertIn(expected, codes(r))
            self.assertEqual(r['status'], 'review_required')
            self.assertEqual(r['dispatch_pairs'], [])
        self.assertIn('discriminator_presence_changed', codes(tool.compare(b, a)))

    def test_mapping_added_removed_not_assumed_closed(self):
        a = doc()
        b = copy.deepcopy(a)
        root(b)['discriminator']['mapping']['another'] = 'Done'
        self.assertIn('discriminator_mapping_added', codes(tool.compare(a, b)))
        self.assertIn('discriminator_mapping_removed', codes(tool.compare(b, a)))
        self.assertEqual(tool.compare(b, a)['status'], 'review_required')

    def test_retarget_review_and_constraint_comparison(self):
        a = doc()
        b = copy.deepcopy(a)
        b['components']['schemas']['Other'] = {'type': 'string'}
        root(b)['discriminator']['mapping']['done'] = 'Other'
        r = tool.compare(a, b)
        self.assertIn('discriminator_target_changed', codes(r))
        self.assertTrue(target_break(r, 'schema_type_incompatible'))

    def test_component_name_and_pointer_equivalent(self):
        a = doc()
        b = copy.deepcopy(a)
        root(b)['discriminator']['mapping']['done'] = 'Done'
        r = tool.compare(a, b)
        self.assertNotIn('discriminator_target_changed', codes(r))
        self.assertFalse(any(f['severity'] == 'breaking' for f in r['findings']))

    def test_pointer_escaping_and_alias_resolution(self):
        a = doc(schema=union({'d/~': 'D/~'}))
        a['components']['schemas']['D/~'] = {'$ref': '#/components/schemas/Done'}
        b = copy.deepcopy(a)
        target(b)['properties']['value']['enum'].append(2)
        r = tool.compare(a, b)
        self.assertTrue(target_break(r))
        self.assertEqual(r['dispatch_pairs'][0]['old_target'], '#/components/schemas/D~1~0')
        self.assertIn('/mapping/d~1~0/target/', next(f['location'] for f in r['findings'] if f['code'] == 'schema_enum_incompatible'))

    def test_equal_inline_container_still_reaches_nested_dispatch(self):
        a = doc(schema={'type': 'object', 'properties': {'result': union()}})
        b = copy.deepcopy(a)
        target(b)['properties']['value']['enum'].append(2)
        self.assertEqual(root(a), root(b))
        self.assertTrue(target_break(tool.compare(a, b)))

    def test_array_items_and_local_schema_ref(self):
        a = doc(schema={'type': 'array', 'items': {'$ref': '#/components/schemas/Envelope'}})
        a['components']['schemas']['Envelope'] = union()
        b = copy.deepcopy(a)
        target(b)['required'].remove('value')
        r = tool.compare(a, b)
        self.assertTrue(target_break(r, 'response_property_not_guaranteed'))

    def test_recursive_dispatch_terminates(self):
        a = doc()
        target(a)['properties']['child'] = union()
        b = copy.deepcopy(a)
        target(b)['properties']['value']['enum'].append(2)
        r = tool.compare(a, b)
        self.assertTrue(target_break(r))
        self.assertEqual(len(r['dispatch_pairs']), 2)
        self.assertLess(r['schema_visits'], 100)

    def test_boolean_target_stays_review(self):
        a = doc()
        b = copy.deepcopy(a)
        b['components']['schemas']['Done'] = False
        self.assertTrue(target_break(tool.compare(a, b), 'boolean_schema_changed'))

    def test_empty_implicit_map_requires_review(self):
        a = doc(schema=union({}))
        r = tool.compare(a, copy.deepcopy(a))
        self.assertIn('discriminator_implicit_dispatch_unchecked', codes(r))
        self.assertEqual(r['status'], 'review_required')
        root(a)['discriminator'].pop('mapping')
        self.assertIn('discriminator_implicit_dispatch_unchecked', codes(tool.compare(a, a)))

    def test_remote_missing_malformed_targets_refused(self):
        for value in ('https://example.invalid/schema', '#/components/schemas/Missing',
                      '#/components/schemas/Bad~2Escape', 'Absent', '', 42):
            with self.subTest(value=value):
                a = doc(schema=union({'done': value}))
                with self.assertRaises(tool.api.Invalid):
                    tool.compare(a, a)
        a = doc()
        a['components']['schemas']['Done'] = {'$ref': '#/components/schemas/Done'}
        with self.assertRaises(tool.api.Invalid):
            tool.compare(a, a)

    def test_malformed_discriminators_and_composites_refused(self):
        for bad in (None, [], {}, {'propertyName': ''}, {'propertyName': 'kind', 'mapping': []},
                    {'propertyName': 'kind', 'surprise': True}):
            a = doc()
            root(a)['discriminator'] = bad
            with self.subTest(bad=bad), self.assertRaises(tool.api.Invalid):
                tool.compare(a, a)
        for composite in (None, [], {}, True):
            a = doc()
            root(a)['oneOf'] = composite
            with self.assertRaises(tool.api.Invalid):
                tool.compare(a, a)
        a = doc()
        root(a).pop('oneOf')
        with self.assertRaises(tool.api.Invalid):
            tool.compare(a, a)

    def test_mapping_pair_and_schema_budgets_refuse(self):
        a = doc(schema=union({str(n): 'Done' for n in range(65)}))
        with self.assertRaises(tool.api.Invalid):
            tool.compare(a, a)
        a = doc()
        with patch.object(tool, 'MAX_DISPATCH_PAIRS', 0), self.assertRaises(tool.api.Invalid):
            tool.compare(a, a)
        with patch.object(tool.api, 'MAX_STEPS', 0), self.assertRaises(tool.api.Invalid):
            tool.compare(a, a)

    def test_status_fallback_and_previous_findings_retained(self):
        a = doc()
        a['paths']['/probe']['post']['responses'] = {'2XX': {
            'description': 'test', 'headers': {'X-Receipt': {'required': True, 'schema': {'type': 'string'}}}}}
        b = copy.deepcopy(a)
        b['paths']['/probe']['post']['responses']['200'] = {'description': 'test'}
        prior = tool.previous.compare(a, b)
        r = tool.compare(a, b)
        self.assertTrue(all(f in r['findings'] for f in prior['findings']))
        self.assertIn('fallback_response_header_removed', codes(r))
        self.assertEqual(r['selector_groups'], prior['selector_groups'])

    def test_fallback_dispatch_target_reached(self):
        a = doc()
        responses = a['paths']['/probe']['post']['responses']
        responses['2XX'] = responses.pop('200')
        b = copy.deepcopy(a)
        b['paths']['/probe']['post']['responses']['200'] = copy.deepcopy(responses['2XX'])
        target(b)['properties']['value']['enum'].append(2)
        r = tool.compare(a, b)
        self.assertTrue(any('/responses/200/' in f['location'] and f['code'] == 'schema_enum_incompatible' for f in r['findings']))

    def test_versions_and_unchanged_capture(self):
        for version in ('3.0.3', '3.1.0'):
            a = doc(version=version)
            self.assertEqual(tool.compare(a, a)['findings'], [])
        a, _ = tool.api.load(Path(__file__).resolve().parents[1] / 'apidelta/imd-openapi.json')
        r = tool.compare(a, a)
        self.assertEqual(r['findings'], [])
        self.assertEqual(r['operations_compared'], 5)

    def test_deterministic_nonmutating_and_cli_exits(self):
        a = doc()
        b = copy.deepcopy(a)
        target(b)['properties']['value']['enum'].append(2)
        snapshot = copy.deepcopy((a, b))
        r = tool.compare(a, b)
        self.assertEqual((a, b), snapshot)
        self.assertEqual(r, tool.compare(a, b))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(tool.main(['demo']), 0)
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            p, q = Path(folder) / 'old.json', Path(folder) / 'new.json'
            p.write_text(json.dumps(a))
            for candidate, expected in ((a, 0), (b, 1), (doc(schema=union({})), 3), ({}, 2)):
                q.write_text(json.dumps(candidate))
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(tool.main(['compare', str(p), str(q)]), expected)


if __name__ == '__main__':
    unittest.main()
