#!/usr/bin/env python3
"""Run unchanged ApiDelta tests while keeping temporary files outside its line."""
from pathlib import Path
import runpy
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = ROOT / 'test/scratch/audit-lines-3-4-36'
TARGET = ROOT / 'line-4/tools/apidelta/selftest.py'
original = tempfile.TemporaryDirectory


def temporary_directory(*args, **kwargs):
    kwargs['dir'] = SCRATCH
    return original(*args, **kwargs)


if __name__ == '__main__':
    SCRATCH.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(TARGET.parent))
    sys.argv = [str(TARGET)]
    with patch.object(tempfile, 'TemporaryDirectory', temporary_directory):
        runpy.run_path(str(TARGET), run_name='__main__')
