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
if args.only_changed:
    if not update.raw_changed():
        print("downloaded raw data unchanged")
        exit(0)


# accidentally duplicated <tr> and other hrml errors
html = BeautifulSoup(update.rawdata, 'html.parser')

parse = fetchhelper.ParseData(update, 'data')

txt = str(html.find(text=re.compile('Stand: ')))
mo = re.search(r'Stand: (\d\d.\d\d.\d\d\d\d, \d\d:\d\d) Uhr', txt)
datatime = parse.parsedtime = update.contenttime = datetime.datetime.strptime(mo.group(1), '%d.%m.%Y, %H:%M').replace(tzinfo=datatz)

title = html.find(text=re.compile('Fallzahlen Infizierte nach Gemeinden')).find_parent('h2')
rows = title.find_next_sibling('table').find_all('tr')

with open(parse.parsedfile, 'w') as outf:
    cout = csv.writer(outf)
    header = ('Kommune', 'Timestamp', 'Confirmed')
    cout.writerow(header)

    for row in rows:
        tds = row.find_all('td')
        cout.writerow((tds[0].get_text(), datatime.isoformat(), int(tds[1].get_text())))
parse.diff()

if args.only_changed:
    if not parse.parseddiff.changed:
        print("parsed content \"%s\" unchanged" % parse.label)
        sys.exit(0)

parse.deploy_timestamp()
print("written %s" % parse.deployfile)

fetchhelper.git_commit([parse], args)
