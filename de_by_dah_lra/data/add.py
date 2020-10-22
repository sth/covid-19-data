#!/usr/bin/env python3

import argparse
import datetime

ap = argparse.ArgumentParser()
ap.add_argument('--dry-run', '-n', action='store_true', help="Don't add to git")
ap.add_argument('timestamp')
args = ap.parse_args()

if args.timestamp.startswith('gemeinden'):
    args.timestamp = args.timestamp[10:-4]

args.timestamp = datetime.datetime.fromisoformat(args.timestamp)

import os

if args.timestamp.tzinfo is None:
    args.timestamp = args.timestamp.astimezone()

targetname = 'data_' + args.timestamp.astimezone(datetime.timezone.utc).replace(tzinfo=None).isoformat(timespec='minutes') + '.csv'

sourcename = None 
for fn in sorted(os.listdir('.')):
    if fn < targetname:
        sourcename = fn
    else:
        break

if sourcename is None:
    print("Found no source")
    sys.exit(1)

import csv

targetts = args.timestamp.isoformat()
with open(sourcename) as inf:
    with open(targetname, 'w') as outf:
        cw = csv.writer(outf)
        for row in csv.reader(inf):
            if row[1] != 'Timestamp':
                row[1] = targetts
            cw.writerow(row)
print("created", targetname)

import subprocess
while True:
    subprocess.run(['vim', targetname])
    print('Sum:')
    subprocess.run(['./sum.py', targetname])
    answer = input('correct? [y] ')
    if answer in ['', 'y', 'j']:
        break

if not args.dry_run:
    subprocess.run(['git', 'add', targetname])
    print("added.")
