#!/usr/bin/env python3
"""Resource checks, an independent discrete-time oracle and CLI behavior."""
import copy
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest

import lockcheck as lc

HERE = Path(__file__).resolve().parent
ROOT = Path.cwd()


class Checks(unittest.TestCase):
    def setUp(self):
        self.tasks, self.plan, self.limits = lc.example()

    def check(self):
        return lc.check(self.tasks, self.plan, self.limits, 2, 5)

    def test_demo(self):
        report = lc.demo()
        self.assertFalse(report['double_booked']['valid'])
        self.assertTrue(report['double_booked']['schedule_valid'])
        resource = report['double_booked']['resources'][0]
        self.assertEqual(resource['peak_units'], 2)
        self.assertEqual(resource['conflicts'], [{'start_minutes': '1', 'finish_minutes': '3',
                         'usage': 2, 'excess': 1, 'tasks': [{'task': 'preview', 'units': 1},
                                                          {'task': 'render', 'units': 1}]}])
        self.assertTrue(report['serialized']['valid'])
        self.assertEqual(report['serialized']['resources'][0]['peak_units'], 1)

    def test_immutable_and_order_independent(self):
        before = copy.deepcopy((self.tasks, self.plan, self.limits))
        expected = self.check()
        self.assertEqual(before, (self.tasks, self.plan, self.limits))
        self.tasks['tasks'].reverse()
        self.plan['schedule'].reverse()
        self.limits['demands'] = dict(reversed(list(self.limits['demands'].items())))
        self.assertEqual(self.check(), expected)

    def test_multiple_and_unused_resources(self):
        self.limits['capacities'] = {'gpu': 2, 'workspace': 1, 'unused': 7}
        self.limits['demands']['render']['workspace'] = 1
        self.limits['demands']['preview']['workspace'] = 2
        result = {r['id']: r for r in self.check()['resources']}
        self.assertTrue(result['gpu']['valid'])
        self.assertEqual(result['unused']['peak_units'], 0)
        self.assertEqual(result['workspace']['peak_units'], 3)
        self.assertEqual(result['workspace']['conflicts'][0]['excess'], 2)

    def test_no_demands(self):
        self.limits['demands'] = {'render': {}, 'preview': {}}
        self.assertTrue(self.check()['valid'])
        self.assertEqual(self.check()['resources'][0]['peak_units'], 0)

    def test_exact_endpoint_and_tiny_overlap(self):
        self.tasks = {'tasks': [{'id': 'a', 'minutes': Decimal('0.1')},
                                 {'id': 'b', 'minutes': Decimal('0.2')}]}
        self.plan = {'workers': 2, 'finish': Decimal('0.3'), 'schedule': [
            {'task': 'a', 'worker': 1, 'start': 0, 'finish': Decimal('0.1')},
            {'task': 'b', 'worker': 2, 'start': Decimal('0.1'), 'finish': Decimal('0.3')}]}
        self.limits['demands'] = {'a': {'gpu': 1}, 'b': {'gpu': 1}}
        self.assertTrue(self.check()['valid'])
        self.plan['schedule'][1].update(start=Decimal('0.09999999999999999999'),
                                         finish=Decimal('0.29999999999999999999'))
        self.plan['finish'] = Decimal('0.29999999999999999999')
        conflict = self.check()['resources'][0]['conflicts'][0]
        self.assertEqual(conflict['start_minutes'], '0.09999999999999999999')
        self.assertEqual(conflict['finish_minutes'], '0.1')

    def test_withheld_invalid_schedule(self):
        for mutate in ('worker', 'duration', 'finish', 'deadline', 'missing'):
            tasks, plan, limits = lc.example()
            if mutate == 'worker':
                plan['schedule'][1]['worker'] = 1
            elif mutate == 'duration':
                plan['schedule'][0]['finish'] = 2
            elif mutate == 'finish':
                plan['finish'] = 1
            elif mutate == 'deadline':
                pass
            else:
                plan['schedule'].pop()
            result = lc.check(tasks, plan, limits, 2, 2 if mutate == 'deadline' else 5)
            self.assertFalse(result['valid'])
            self.assertFalse(result['schedule_valid'])
            self.assertEqual(result['resources'], [])

    def test_bad_limits(self):
        invalid = [[], {}, {'capacities': {}, 'demands': {}},
                   {'capacities': {'gpu': 1}, 'demands': {'render': {}}}]
        for capacity in (True, 0, -1, 1.5, '1', 10**9 + 1):
            bad = copy.deepcopy(self.limits)
            bad['capacities']['gpu'] = capacity
            invalid.append(bad)
        for demand in (True, 0, -1, 1.5, '1', 10**9 + 1):
            bad = copy.deepcopy(self.limits)
            bad['demands']['render']['gpu'] = demand
            invalid.append(bad)
        for name in ('', ' ', 'x' * 101):
            invalid.append({'capacities': {name: 1}, 'demands': self.limits['demands']})
        bad = copy.deepcopy(self.limits)
        bad['demands']['preview'] = {'unknown': 1}
        invalid.append(bad)
        bad = copy.deepcopy(self.limits)
        bad['demands']['unknown'] = {}
        invalid.append(bad)
        bad = copy.deepcopy(self.limits)
        bad['extra'] = 1
        invalid.append(bad)
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                lc.check(self.tasks, self.plan, value, 2)

    def test_numeric_rendering(self):
        for spelling in ('0', '1', '0.002', '-12.5', '1E-100', '1E+100',
                         '0.123456789012345678901234567890123456789'):
            rational = Fraction(Decimal(spelling))
            self.assertEqual(Fraction(Decimal(lc.exact(rational))), rational)
        with self.assertRaises(ValueError):
            lc.exact(Fraction(1, 3))

    def test_200_grid_oracles(self):
        rng = random.Random(73736)
        for _ in range(200):
            rows, tasks, demands = [], [], {}
            caps = {'gpu': rng.randint(1, 5), 'workspace': rng.randint(1, 5)}
            count = rng.randint(1, 12)
            for i in range(count):
                task = 'task' + str(i)
                start, duration = rng.randint(0, 8), rng.randint(1, 5)
                rows.append({'task': task, 'worker': i + 1, 'start': start, 'finish': start + duration})
                tasks.append({'id': task, 'minutes': duration})
                demands[task] = {r: rng.randint(1, 4) for r in caps if rng.random() < .7}
            end = max(row['finish'] for row in rows)
            report = lc.check({'tasks': tasks}, {'schedule': rows, 'workers': count, 'finish': end},
                              {'capacities': caps, 'demands': demands}, count)
            all_good = True
            for resource in report['resources']:
                name = resource['id']
                usages = [sum(demands[row['task']].get(name, 0) for row in rows
                              if row['start'] <= minute < row['finish']) for minute in range(end)]
                self.assertEqual(resource['peak_units'], max(usages))
                expanded = {}
                for segment in resource['conflicts']:
                    for minute in range(int(segment['start_minutes']), int(segment['finish_minutes'])):
                        self.assertNotIn(minute, expanded)
                        expanded[minute] = segment['usage']
                        active = sorted((r['task'], demands[r['task']][name]) for r in rows
                                        if r['start'] <= minute < r['finish'] and name in demands[r['task']])
                        self.assertEqual([(r['task'], r['units']) for r in segment['tasks']], active)
                expected = {i: usage for i, usage in enumerate(usages) if usage > caps[name]}
                self.assertEqual(expanded, expected)
                self.assertEqual(resource['valid'], not expected)
                all_good &= not expected
            self.assertEqual(report['valid'], all_good)

    def test_cli(self):
        cmd = [sys.executable, '-B', str(HERE / 'lockcheck.py')]
        for extra, code in [(['--demo'], 0), ([], 1), (['--demo', '--workers', '2'], 1)]:
            result = subprocess.run(cmd + extra, text=True, capture_output=True)
            self.assertEqual(result.returncode, code, result.stderr)
        args = ['--tasks', str(HERE / 'tasks.json'), '--plan', str(HERE / 'plan.json'),
                '--limits', str(HERE / 'limits.json'), '--workers', '2', '--budget']
        for budget, code in [('5', 2), ('2', 2), ('NaN', 1), ('garbage', 1)]:
            result = subprocess.run(cmd + args + [budget], text=True, capture_output=True)
            self.assertEqual(result.returncode, code, result.stderr)
            if code == 2:
                self.assertFalse(json.loads(result.stdout)['valid'])
        scratch = ROOT / 'test/scratch/lockcheck'
        scratch.mkdir(parents=True, exist_ok=True)
        limits = scratch / 'limits.json'
        limits.write_text('{"capacities":{"gpu":1,"gpu":2},"demands":{}}')
        with self.assertRaises(ValueError):
            lc.pc.read_json(limits)
        self.limits['capacities']['gpu'] = 2
        limits.write_text(json.dumps(self.limits))
        args[5] = str(limits)
        result = subprocess.run(cmd + args + ['5'], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['valid'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
