#!/usr/bin/env python3

import sys, os, subprocess

failed = False
for sub in os.listdir('.'):
    if not os.path.exists(os.path.join(sub, 'fetch.py')):
        continue
    cp = subprocess.run(['./fetch.py'] + sys.argv[1:], cwd=sub)
    failed = failed or (cp.returncode != 0)

if failed:
    sys.exit(1)
