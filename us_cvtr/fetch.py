#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

import subprocess, datetime, re, csv, os
from datetime import datetime
from bs4 import BeautifulSoup
import dateutil.tz

def cleannum(s):
    return int(s.replace(' ', ''))

datatz = dateutil.tz.gettz('America/New York')

update = fetchhelper.Updater('https://covidtracking.com/api/states.csv')
update.check_fetch(rawfile=args.rawfile)
if args.only_changed:
    if not update.raw_changed():
        print("downloaded raw data unchanged")
        exit(0)

parse = fetchhelper.ParseData(update, 'data')
parse.parsedtime = update.rawtime
with open(update.rawfile) as inf:
    cr = csv.reader(inf)
    header = next(cr)
    assert(header[0] == 'state')
    assert(header[1] == 'positive')
    assert(header[4] == 'death')
    assert(header[6] == 'lastUpdateEt')

    with open(parse.parsedfile, 'w') as outf:
        cw = csv.writer(outf)
        cw.writerow(['Area', 'Date', 'Confirmed', 'Deaths'])

        for line in cr:
            timestamp = datetime.strptime('2020 ' + line[6], '%Y %m/%d %H:%M').replace(tzinfo=datatz)
            cw.writerow([line[0], timestamp, line[1] or '0', line[4] or '0'])

parse.diff()
if args.only_changed:
    if not parse.parseddiff.changed:
        print("parsed content \"%s\" unchanged" % parse.label)
        #return

parse.deploy_timestamp()

fetchhelper.git_commit([parse], args)
