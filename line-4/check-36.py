#!/usr/bin/env python3
"""Reproduce local regressions and optionally read the public API description only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('round36_dispatch', ROOT / 'tools/dispatchcheck/dispatchcheck.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
# The original ApiDelta tests create CLI inputs in their tool directory.
# Redirect only TemporaryDirectory into the explicitly authorized scratch area.
RUN_SUITE = '''import pathlib,runpy,sys,tempfile
from unittest.mock import patch
p=pathlib.Path(sys.argv[1]).resolve()
scratch=pathlib.Path.cwd()/'test/scratch'
scratch.mkdir(parents=True,exist_ok=True)
original=tempfile.TemporaryDirectory
def temporary(*args,**kwargs):
    kwargs['dir']=scratch
    return original(*args,**kwargs)
sys.path.insert(0,str(p.parent))
sys.argv=[str(p)]
with patch.object(tempfile,'TemporaryDirectory',temporary):
    runpy.run_path(str(p),run_name='__main__')
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    suites = []
    for script in sorted((ROOT / 'tools').glob('*/selftest.py')):
        run = subprocess.run([sys.executable, '-B', '-c', RUN_SUITE, str(script)],
                             capture_output=True, text=True, timeout=60)
        match = re.search(r'Ran (\d+) tests?', run.stderr)
        suites.append(dict(tool=script.parent.name, exit=run.returncode,
                           tests=int(match[1]) if match else None,
                           stdout=run.stdout, stderr=run.stderr))
    capture = ROOT / 'tools/apidelta/imd-openapi.json'
    old, digest = module.api.load(capture)
    report = dict(suites=suites, demo=module.demo(), unchanged_capture=module.compare(old, old),
                  capture_sha256=digest, independent_payload_oracle_cases=98,
                  suite_scratch_policy='TemporaryDirectory redirected to test/scratch; source tests unchanged')
    if args.live:
        request = urllib.request.Request('https://api.imd.fun/openapi.json',
                    headers={'User-Agent': 'Pepeolithic-DispatchCheck/36.0'})
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read(module.api.MAX_BYTES + 1)
        module.api.require(len(raw) < 100000, 'public capture exceeds delivery size limit')
        obj = json.loads(raw, object_pairs_hook=module.api.pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
        module.api.validate(obj)
        (ROOT / 'live-openapi-36.json').write_bytes(raw)
        report['live'] = dict(source='https://api.imd.fun/openapi.json',
                             user_agent='Pepeolithic-DispatchCheck/36.0',
                             bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                             matches_capture=raw == capture.read_bytes(), comparison=module.compare(old, obj))
    (ROOT / 'check-results-36.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(suites=len(suites), tests=sum(s['tests'] or 0 for s in suites),
        failures=[s['tool'] for s in suites if s['exit']], demo=report['demo']['counts'],
        capture_findings=len(report['unchanged_capture']['findings']), live=report.get('live')), indent=2))
    return int(any(s['exit'] for s in suites))


if __name__ == '__main__':
    sys.exit(main())
