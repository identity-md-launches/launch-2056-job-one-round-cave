#!/usr/bin/env python3
"""Replay reviewed, offline line checks and demos without changing line folders."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def jobs(line):
    for folder in sorted((ROOT / f'line-{line}/tools').iterdir()):
        if not folder.is_dir():
            continue
        name = folder.name
        def run(script, *args, expected=0, kind='demo'):
            return (name, kind, ['python3', '-B', str(script.relative_to(ROOT)), *args], expected)
        suite = folder / 'selftest.py'
        if suite.exists():
            if name == 'apidelta':
                yield name, 'check', ['python3', '-B', 'gathering/audit_apidelta_36.py'], 0
            else:
                yield run(suite, kind='check')
        main = folder / (name + '.py')
        if line == 1:
            if name in ('workplan', 'optplan', 'gatecheck', 'gateplan'):
                yield run(main, '--self-test', kind='inline-check')
            if name == 'budgetpath':
                yield run(main, str((folder / 'example.json').relative_to(ROOT)))
            else:
                options = {
                    'workplan': ('--demo', '--workers', '2', '--budget', '25'),
                    'optplan': ('--idle-demo', '--workers', '2'),
                    'replan': ('--demo', '--workers', '2', '--budget', '27'),
                    'slackmap': ('--demo', '--budget', '10'),
                    'goalslice': ('--demo', '--explain'),
                    'gateplan': ('--demo', '--workers', '1', '--budget', '7'),
                }.get(name, ('--demo',))
                yield run(main, *options)
        elif line == 2:
            if name == 'zipmerge':
                yield run(folder / 'metadata_selftest.py', kind='check')
                yield run(folder / 'metadata_demo.py')
            demo = folder / 'demo.py'
            if not demo.exists():
                demo = folder / 'swarm_demo.py'
            if demo.exists():
                yield run(demo)
        elif line == 3:
            if name == 'rewardledger':
                # Its documented /tmp CSV output is redirected to stdout so the
                # demonstration has no output file outside the allowed scratch.
                yield run(main, 'line-3/tools/rewardledger/example.json')
            else:
                yield run(main, 'demo', expected=1 if name == 'rewardcompare' else 0)
        else:
            yield run(main, 'demo')
    if line == 1:
        main = ROOT / 'line-1/tools/gateplan/gateplan.py'
        yield ('gateplan', 'refusal', ['python3', '-B', str(main.relative_to(ROOT)),
              '--demo', '--workers', '1', '--budget', '6'], 2)
        yield ('gateplan', 'refusal', ['python3', '-B', str(main.relative_to(ROOT)),
              '--demo', '--max-states', '1'], 1)


def run_line(line):
    rows = []
    for name, kind, command, expected in jobs(line):
        done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90)
        combined = done.stdout + done.stderr
        found = re.search(r'Ran (\d+) tests?', combined)
        passed = done.returncode == expected
        if name == 'rewardledger' and kind == 'demo':
            passed = passed and 'report_sha256,' in done.stdout and '666666666666666667' in done.stdout
        rows.append(dict(line=line, tool=name, kind=kind, command=command,
                         expected_exit=expected, actual_exit=done.returncode,
                         passed=passed, unittest_cases=int(found.group(1)) if found else 0,
                         stdout_sha256=hashlib.sha256(done.stdout.encode()).hexdigest(),
                         evidence=combined[-450:]))
    return rows


def main():
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = [r for group in pool.map(run_line, range(1, 5)) for r in group]
    summary = []
    for line in range(1, 5):
        group = [r for r in rows if r['line'] == line]
        summary.append(dict(line=line, tools=len({r['tool'] for r in group}),
                            commands=len(group), unittest_cases=sum(r['unittest_cases'] for r in group),
                            unexpected=sum(not r['passed'] for r in group)))
    report = dict(round=36, scope='All documented tool checks and offline demos',
                  summary=summary, commands=rows)
    raw = json.dumps(report, indent=2) + '\n'
    if len(raw.encode()) > 100000:
        raise ValueError('evidence exceeds 100 KB')
    (ROOT / 'gathering/audit-lines-36.json').write_text(raw)
    print(json.dumps(summary, indent=2))
    for row in rows:
        if not row['passed']:
            print(json.dumps(row, indent=2))
    return int(any(not row['passed'] for row in rows))


if __name__ == '__main__':
    raise SystemExit(main())
