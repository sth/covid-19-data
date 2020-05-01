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

update = fetchhelper.Updater('https://covidtracking.com/api/v1/states/current.csv', ext='csv')
update.check_fetch(rawfile=args.rawfile)

parse = fetchhelper.ParseData(update, 'data')
parse.parsedtime = None
with open(update.rawfile) as inf:
    cr = csv.reader(inf)
    header = next(cr)

    selector_labels = ['state', 'lastUpdateEt', 'positive', 'death']
    selector = []
    for sl in selector_labels:
        for (i, h) in enumerate(header):
            if h == sl:
                selector.append(i)
                break
        else:
            print("Couldn't mach header", file=sys.stderr)
            sys.exit(1)

    with open(parse.parsedfile, 'w') as outf:
        cw = csv.writer(outf)
        cw.writerow(['Area', 'Date', 'Confirmed', 'Deaths'])

        for line in cr:
            values = [line[i] for i in selector]
            if not values[0]:
                continue
            timestamp = datetime.strptime('2020 ' + values[1], '%Y %m/%d %H:%M').replace(tzinfo=datatz)
            if parse.parsedtime is None or parse.parsedtime < timestamp:
                parse.parsedtime = timestamp
            cw.writerow([values[0], timestamp, values[2] or '0', values[3] or '0'])

parse.deploy_timestamp()

fetchhelper.git_commit([parse], args)
