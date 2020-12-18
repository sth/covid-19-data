#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

import subprocess, datetime, re, csv, os, sys
from bs4 import BeautifulSoup
import dateutil.tz

datatz = dateutil.tz.gettz('Europe/Berlin')

update = fetchhelper.Updater('https://www.landkreis-muenchen.de/themen/verbraucherschutz-gesundheit/gesundheit/coronavirus/fallzahlen/')
update.check_fetch(rawfile=args.rawfile)

# accidentally duplicated <tr> and other hrml errors
html = BeautifulSoup(update.rawdata, 'html.parser')

parse = fetchhelper.ParseData(update, 'data')

txt = str(html.find(text=re.compile('Stand: ')))
mo = re.search(r'Stand: (\d\d.\d\d.\d\d\d\d, \d\d:\d\d) ?Uhr', txt)
datatime = parse.parsedtime = update.contenttime = datetime.datetime.strptime(mo.group(1), '%d.%m.%Y, %H:%M').replace(tzinfo=datatz)

title = html.find(text=re.compile('Fallzahlen Infizierte nach Gemeinden')).find_parent('h2')
rows = fetchhelper.text_table(title.find_next_sibling('table'))

assert(len(rows[0]) == 2 or len(rows[0]) == 3)
if rows[0][0] == 'Gemeinde/Stadt':
    rows = rows[1:]

with open(parse.parsedfile, 'w') as outf:
    cout = csv.writer(outf)
    header = ('Kommune', 'Timestamp', 'Confirmed')
    cout.writerow(header)
    for tds in rows:
        cout.writerow((tds[0], datatime.isoformat(), int(tds[1])))

parse.deploy_timestamp()

fetchhelper.git_commit([parse], args)
