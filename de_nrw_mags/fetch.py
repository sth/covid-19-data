#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

import re, csv, os, sys
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
    return int(numstr.replace('.', '').strip() or '0')

header = html.find(text="Bestätigte Fälle")

parse = fetchhelper.ParseData(update, 'data')

txt = str(html.find(text=re.compile('Aktueller Stand:')))
txt = txt.replace('März', '03').replace('April', '04').replace('Mai', '05')
mo = re.search(r'Aktueller Stand: (\d\d\. \d\d \d\d\d\d, \d\d\.\d\d) Uhr', txt)
if mo is None:
    print("Couldn't find date.", file=sys.stderr)
    sys.exit(1)
parse.parsedtime = datetime.strptime(mo.group(1), '%d. %m %Y, %H.%M').replace(tzinfo=datatz)

tab = header.find_parent('table')
if tab is None:
    print("couldn't find table", file=sys.stderr)
    exit(1)

with open(parse.parsedfile, 'w') as outf:
    cout = csv.writer(outf)
    rows = tab.find_all('tr')
    assert('Landkreis' in rows[0].find('th').get_text())
    assert('Gesamt' in rows[-1].find('td').get_text())
    rows = rows[1:-1]

    colnum = len(rows[0].find_all('td'))
    if colnum == 2:
        cout.writerow(['Area', 'Date', 'Confirmed'])
    elif colnum == 3:
        cout.writerow(['Area', 'Date', 'Confirmed', 'Deaths'])
    else:
        raise Exception("unknown table structure")

    for tr in rows:
        tds = tr.find_all('td')
        area = tds[0].get_text()
        confirmed = clean_num(tds[1].get_text())
        if colnum > 2:
            deceased = clean_num(tds[2].get_text())
        if colnum == 2:
            cout.writerow([area, parse.parsedtime.isoformat(), confirmed])
        else:
            cout.writerow([area, parse.parsedtime.isoformat(), confirmed, deceased])
parse.diff()

if args.only_changed:
    if not parse.parseddiff.changed:
        print("parsed content \"%s\" unchanged" % parse.label)
        exit(0)

parse.deploy_timestamp()
print("written %s" % parse.deployfile)

fetchhelper.git_commit([parse], args)
