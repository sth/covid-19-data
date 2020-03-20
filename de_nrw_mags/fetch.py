#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

import re, csv, os
from datetime import datetime
from bs4 import BeautifulSoup
import dateutil.tz

datatz = dateutil.tz.gettz('Europe/Berlin')

update = fetchhelper.Updater('https://www.mags.nrw/coronavirus-fallzahlen-nrw')
update.check_fetch(rawfile=args.rawfile)
if args.only_changed:
    if not update.raw_changed():
        print("downloaded raw data unchanged")
        exit(0)

html = BeautifulSoup(update.rawdata, 'html.parser')


def clean_num(numstr):
    return int(numstr.replace('.', '').strip())

header = html.find(text="Bestätigte Fälle")

parse = fetchhelper.ParseData(update, 'data')

txt = str(html.find(text=re.compile('Aktueller Stand:')))
txt = txt.replace('März', '03').replace('April', '04').replace('Mai', '05')
mo = re.search(r'Aktueller Stand: (\d\d\. \d\d \d\d\d\d, \d\d\.\d\d) Uhr', txt)
if mo is None:
    print("Couldn't find date.", file=sys.stdout)
    sys.exit(1)
parse.parsedtime = datetime.strptime(mo.group(1), '%d. %m %Y, %H.%M').replace(tzinfo=datatz)

tab = header.find_parent('table')
if tab is None:
    print("couldn't find table")
    exit(1)

with open(parse.parsedfile, 'w') as outf:
    cout = csv.writer(outf)
    cout.writerow(['Area', 'Date', 'Confirmed'])

    for tr in tab.find_all('tr')[1:-1]:
        tds = tr.find_all('td')
        area = tds[0].get_text()
        value = clean_num(tds[1].get_text())

        cout.writerow([area, parse.parsedtime.isoformat(), value])
parse.diff()

if args.only_changed:
    if not parse.parseddiff.changed:
        print("parsed content \"%s\" unchanged" % parse.label)
        exit(0)

parse.deploy_timestamp()
print("written %s" % parse.deployfile)

fetchhelper.git_commit([parse], args)
