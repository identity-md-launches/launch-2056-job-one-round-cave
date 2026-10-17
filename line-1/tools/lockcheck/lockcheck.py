#!/usr/bin/env python3
"""Check shared renewable resource limits on a full offline work schedule."""
import argparse
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'plancheck'))
import plancheck as pc


def exact(value):
    """Finite decimal Fraction to string without using a rounding context."""
    value = Fraction(value)
    denominator = value.denominator
    places = 0
    while denominator != 1:
        divisor = 10 if denominator % 10 == 0 else 2 if denominator % 2 == 0 else 5
        if denominator % divisor:
            raise ValueError('non-decimal internal result')
        denominator //= divisor
        places += 1
    scaled = value.numerator * (10 ** places) // value.denominator
    if not places:
        return str(scaled)
    digits = str(abs(scaled)).rjust(places + 1, '0')
    return ('-' if scaled < 0 else '') + (digits[:-places] + '.' + digits[-places:]).rstrip('0').rstrip('.')


def positive_integer(value, label):
    if type(value) is not int or not 1 <= value <= 10**9:
        raise ValueError(label + ' must be an integer from 1 to 1000000000')
    return value


def resources(data, task_ids):
    pc.keys(data, ('capacities', 'demands'))
    caps, demands = data['capacities'], data['demands']
    if not isinstance(caps, dict) or not 1 <= len(caps) <= 64:
        raise ValueError('capacities must name 1 to 64 resources')
    for name, capacity in caps.items():
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            raise ValueError('resource names must be nonempty strings up to 100 characters')
        positive_integer(capacity, 'capacity')
    if not isinstance(demands, dict) or set(demands) != task_ids:
        raise ValueError('demands must explicitly name every task exactly once; use {} for none')
    for name, row in demands.items():
        if not isinstance(row, dict) or set(row) - set(caps):
            raise ValueError('task demands must map known resource names to units: ' + name)
        for units in row.values():
            positive_integer(units, 'demand')
    return caps, demands


def check(tasks, plan, limits, workers, budget=None):
    """Check fixed half-open task intervals; never schedule or execute work."""
    caps, demands = resources(limits, set(pc.graph(tasks)))
    baseline = pc.check(tasks, plan, workers, budget)
    result = {'valid': False, 'schedule_valid': baseline['valid'],
              'schedule_violations': baseline['violations'], 'resources': [],
              'scope': 'fixed full-task reservations on [start, finish); caller-supplied capacities and estimates; no execution or rescheduling',
              'arithmetic': 'exact decimal minutes rendered as strings; integer resource units'}
    if not baseline['valid']:
        result['scope'] = 'resource results withheld until the full schedule passes Plancheck'
        return result
    slots = {r['task']: (pc.number(r['start'], 'start'), pc.number(r['finish'], 'finish'))
             for r in plan['schedule']}
    for resource, capacity in sorted(caps.items()):
        events = {}
        for task, row in demands.items():
            if resource in row:
                start, end = slots[task]
                events.setdefault(start, []).append((task, row[resource]))
                events.setdefault(end, []).append((task, -row[resource]))
        active, usage, peak, conflicts = {}, 0, 0, []
        times = sorted(events)
        for index, time in enumerate(times):
            # All changes at a boundary are simultaneous. Finishing tasks release
            # their reservation before the following positive-length interval.
            for task, delta in events[time]:
                usage += delta
                if delta > 0:
                    active[task] = delta
                else:
                    del active[task]
            if index + 1 == len(times):
                continue
            peak = max(peak, usage)
            if usage > capacity:
                conflicts.append({'start_minutes': exact(time),
                                  'finish_minutes': exact(times[index + 1]),
                                  'usage': usage, 'excess': usage - capacity,
                                  'tasks': [{'task': task, 'units': units}
                                            for task, units in sorted(active.items())]})
        result['resources'].append({'id': resource, 'capacity': capacity,
                                    'peak_units': peak, 'valid': not conflicts,
                                    'conflicts': conflicts})
    result['valid'] = all(row['valid'] for row in result['resources'])
    return result


def example():
    tasks = {'tasks': [{'id': 'render', 'minutes': 3}, {'id': 'preview', 'minutes': 2}]}
    plan = {'workers': 2, 'finish': 3, 'schedule': [
        {'task': 'render', 'worker': 1, 'start': 0, 'finish': 3},
        {'task': 'preview', 'worker': 2, 'start': 1, 'finish': 3}]}
    limits = {'capacities': {'gpu': 1}, 'demands': {'render': {'gpu': 1}, 'preview': {'gpu': 1}}}
    return tasks, plan, limits


def demo():
    tasks, plan, limits = example()
    conflict = check(tasks, plan, limits, 2, 5)
    plan['schedule'][1].update(start=3, finish=5)
    plan['finish'] = 5
    return {'double_booked': conflict, 'serialized': check(tasks, plan, limits, 2, 5)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--tasks')
    parser.add_argument('--plan')
    parser.add_argument('--limits')
    parser.add_argument('--workers', type=int)
    parser.add_argument('--budget')
    args = parser.parse_args()
    try:
        if args.demo:
            if any(v is not None for v in (args.tasks, args.plan, args.limits, args.workers, args.budget)):
                raise ValueError('--demo cannot be combined with check options')
            report, code = demo(), 0
        else:
            if any(v is None for v in (args.tasks, args.plan, args.limits, args.workers)):
                raise ValueError('--tasks, --plan, --limits and --workers are required')
            report = check(pc.read_json(args.tasks), pc.read_json(args.plan), pc.read_json(args.limits),
                           args.workers, None if args.budget is None else Decimal(args.budget))
            code = 0 if report['valid'] else 2
        print(json.dumps(report, indent=2, allow_nan=False))
        return code
    except (ValueError, InvalidOperation, OSError, OverflowError, RecursionError) as exc:
        print('lockcheck: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
