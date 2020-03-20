#!/usr/bin/env python3

import sys, subprocess

failed = False
for sub in ['de_rki', 'de_by_lgl', 'de_bw_soz', 'at_sgpk']:
    cp = subprocess.run(['./fetch.py'] + sys.argv[1:], cwd=sub)
    failed = failed or (cp.returncode != 0)

if failed:
    sys.exit(1)
