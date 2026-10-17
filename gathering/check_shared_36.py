#!/usr/bin/env python3
"""Run every shared bundle suite and demo in place and from a standalone copy."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'shared/api_bundle'
SUITES = ['selftest.py', 'parameter_selftest.py', 'status_selftest.py',
          'fallback_selftest.py', 'dispatch_selftest.py']
DEMOS = ['demo.py', 'parameter_demo.py', 'server_demo.py', 'status_demo.py',
         'fallback_demo.py', 'dispatch_demo.py']


def run(cwd):
    rows = []
    for script in SUITES + DEMOS:
        done = subprocess.run(['python3', '-B', 'shared/api_bundle/' + script],
                              cwd=cwd, capture_output=True, text=True, timeout=45)
        match = re.search(r'Ran (\d+) tests?', done.stderr)
        if script in DEMOS and done.returncode == 0:
            json.loads(done.stdout)
        rows.append(dict(command='python3 -B shared/api_bundle/' + script,
                         exit=done.returncode, tests=int(match.group(1)) if match else 0,
                         stdout_sha256=hashlib.sha256(done.stdout.encode()).hexdigest(),
                         evidence=(done.stdout + done.stderr)[-300:]))
    return rows


def main():
    manifest = json.loads((FOLDER / 'SOURCES.json').read_text())
    for relative, item in manifest.items():
        assert hashlib.sha256((FOLDER / relative).read_bytes()).hexdigest() == item['sha256']
        assert hashlib.sha256((ROOT / item['source']).read_bytes()).hexdigest() == item['source_sha256']
    in_place = run(ROOT)
    scratch = ROOT / 'test/scratch'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='shared36-', dir=scratch) as temporary:
        isolated = Path(temporary)
        shutil.copytree(FOLDER, isolated / 'shared/api_bundle', ignore=shutil.ignore_patterns('__pycache__'))
        standalone = run(isolated)
    result = dict(round=36, vendor_sources=len(manifest), in_place=in_place,
                  standalone=standalone,
                  tests=sum(row['tests'] for row in in_place), demos=len(DEMOS),
                  passed=all(row['exit'] == 0 for row in in_place + standalone)
                         and sum(row['tests'] for row in in_place) == 85
                         and sum(row['tests'] for row in standalone) == 85)
    raw = json.dumps(result, indent=2) + '\n'
    if len(raw.encode()) > 100000:
        raise ValueError('evidence exceeds 100 KB')
    (ROOT / 'gathering/shared-check-results-36.json').write_text(raw)
    print(json.dumps({'passed': result['passed'], 'tests_each': result['tests'],
                      'demos_each': result['demos'], 'vendor_sources': len(manifest)}, indent=2))
    return int(not result['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
