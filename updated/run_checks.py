"""Portable test-result evidence for numerical replay; Python standard library."""
from datetime import datetime,timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'

def main():
    start=time.perf_counter();stream=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'updated/tests'))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    source_files=[*sorted((ROOT/'updated').glob('*.py')),*sorted((ROOT/'updated/headless').glob('*.java')),
                  *sorted((ROOT/'updated/tests').glob('*.py'))]
    data={'schema':'beam-numerical-test-results-v1','checked_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
      'command':'python3 updated/run_checks.py','python_version':platform.python_version(),
      'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
      'elapsed_seconds':round(time.perf_counter()-start,6),'status':'passed' if result.wasSuccessful() else 'failed',
      'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
      'test_log':stream.getvalue().replace(str(ROOT),'<repo>'),
      'scope':'Independent synthetic geometry and actual unchanged historical numerical methods; not historical Android/hardware validation'}
    (ROOT/'validation/numerical-tests.json').write_text(json.dumps(data,indent=2)+'\n')
    print(stream.getvalue(),end='');return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
