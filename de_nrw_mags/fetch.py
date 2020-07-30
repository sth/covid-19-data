#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

fetchhelper.check_oldfetch(args)

import re, csv, os, sys
import datetime, glob
from bs4 import BeautifulSoup
import dateutil.tz

if args.optional:
    # Check if we think we need to update
    now = datetime.datetime.now()
    if now.time() > datetime.time(12, 0):
        # We expect data for the current day
        target = now.date()
    else:
        # We expect at least data for the previous day
        target = (now - datetime.timedelta(days=1)).date()
    match = target.isoformat()
    if glob.glob('data/*%s*.csv' % match):
        # Looks good.
        print("Data for %s already saved." % match)
        sys.exit(0)

datatz = dateutil.tz.gettz('Europe/Berlin')

update = fetchhelper.Updater('https://www.mags.nrw/coronavirus-fallzahlen-nrw')
update.check_fetch(rawfile=args.rawfile)

html = BeautifulSoup(update.rawdata, 'html.parser')


def clean_num(numstr):
    if numstr in ['', '-']:
        return 0
    return int(re.sub(r'[.:]', '', numstr).strip())

header = html.find(text="Bestätigte Fälle (IfSG)")

parse = fetchhelper.ParseData(update, 'data')

def clean_date(s):
    for i, m in enumerate(['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
        'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']):
        s = s.replace(m, '%02d' % (i+1))
    return s

txt = str(html.find(text=re.compile('Aktueller Stand:')))
txt = clean_date(txt)
mo = re.search(r'Aktueller Stand: (\d?\d\. \d\d \d\d\d\d, *\d\d[.:]\d\d) Uhr', txt)
if mo is None:
    mo = re.search(r'Aktueller Stand: (\d?\d\. \d\d \d\d\d\d).', txt)
    if mo is None:
        print("Couldn't find date.", file=sys.stderr)
        sys.exit(1)
    # We guess it's in the morning, since official numbers have to be reported until 09:00
    parse.parsedtime = datetime.datetime.strptime(mo.group(1), '%d. %m %Y').replace(hour=3, minute=30, tzinfo=datatz)
else:
    try:
        parse.parsedtime = datetime.datetime.strptime(mo.group(1), '%d. %m %Y, %H.%M').replace(tzinfo=datatz)
    except ValueError:
        parse.parsedtime = datetime.datetime.strptime(mo.group(1), '%d. %m %Y, %H:%M').replace(tzinfo=datatz)

tab = header.find_parent('table')
if tab is None:
    print("couldn't find table", file=sys.stderr)
    exit(1)

with open(parse.parsedfile, 'w') as outf:
    cout = csv.writer(outf)
    rows = fetchhelper.text_table(tab)
    ths = rows[0]
    assert('Landkreis' in ths[0])
    assert('Gesamt' in ''.join(rows[-1]) or 'Nordrhein-Westfalen' in ''.join(rows[-1]))
    rows = rows[1:-1]

    assert(len(ths) == 5)
    colnum = len(ths)
    assert('Bestätigte' in ths[1])
    assert('Todesfälle' in ths[2])
    assert('Genesene' in ths[3])
    assert('Inzidenz' in ths[4])
    cn_deaths = 2
    cn_recovered = 3
    cout.writerow(['Area', 'Date', 'EConfirmed', 'EDeaths', 'Recovered'])

    for tds in rows:
        assert(len(tds) == len(ths))
        area = tds[0].rstrip('*')
        confirmed = clean_num(tds[1])
        deceased = clean_num(tds[cn_deaths])
        if tds[cn_recovered] in ['k. A.', 'k.A.']:
            recovered = None
        else:
            recovered = clean_num(tds[cn_recovered])
        cout.writerow([area, parse.parsedtime.isoformat(), confirmed, deceased, recovered])


parse.deploy_timestamp()

fetchhelper.git_commit([parse], args)
