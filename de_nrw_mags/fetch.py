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

html = BeautifulSoup(update.rawdata, 'html.parser')


def clean_num(numstr):
    if numstr in ['', '-']:
        return 0
    return int(numstr.replace('.', '').strip())

header = html.find(text="Bestätigte Fälle")

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
    print("Couldn't find date.", file=sys.stderr)
    sys.exit(1)

try:
    parse.parsedtime = datetime.strptime(mo.group(1), '%d. %m %Y, %H.%M').replace(tzinfo=datatz)
except ValueError:
    parse.parsedtime = datetime.strptime(mo.group(1), '%d. %m %Y, %H:%M').replace(tzinfo=datatz)

tab = header.find_parent('table')
if tab is None:
    print("couldn't find table", file=sys.stderr)
    exit(1)

with open(parse.parsedfile, 'w') as outf:
    cout = csv.writer(outf)
    rows = tab.find_all('tr')
    ths = rows[0].find_all('th')
    assert('Landkreis' in ths[0].get_text())
    assert('Gesamt' in rows[-1].find('td').get_text())
    rows = rows[1:-1]

    colnum = len(ths)
    cn_deaths = None
    cn_recovered = None
    ifsg = False
    if colnum == 2:
        cout.writerow(['Area', 'Date', 'Confirmed'])
    elif colnum == 3:
        assert('Todesfälle' in ths[2].get_text())
        cn_deaths = 2
        cout.writerow(['Area', 'Date', 'Confirmed', 'Deaths'])
    elif colnum == 4:
        assert('Todesfälle' in ths[2].get_text())
        assert('Genesene' in ths[3].get_text())
        cn_deaths = 2
        cn_recovered = 3
        cout.writerow(['Area', 'Date', 'Confirmed', 'Deaths', 'Recovered'])
    elif colnum == 5:
        assert('Bestätigt' in ths[1].get_text())
        assert('Todesfälle' in ths[3].get_text())
        assert('Genesene' in ths[4].get_text())
        cn_deaths = 3
        cn_recovered = 4
        cout.writerow(['Area', 'Date', 'Confirmed', 'Deaths', 'Recovered'])
    elif colnum == 6:
        assert('Bestätigt' in ths[1].get_text())
        assert('Bestätigt' in ths[2].get_text() and 'IfSG' in ths[2].get_text())
        assert('Todesfälle' in ths[3].get_text())
        assert('Todesfälle' in ths[4].get_text() and 'IfSG' in ths[4].get_text())
        assert('Genesene' in ths[5].get_text())
        cn_deaths = 3
        cn_recovered = 5
        ifsg = True
        cout.writerow(['Area', 'Date', 'Confirmed', 'EConfirmed', 'Deaths', 'EDeaths', 'Recovered'])
    else:
        raise Exception("unknown table structure")

    for tr in rows:
        tds = tr.find_all('td')
        assert(len(tds) == len(ths))
        area = tds[0].get_text()
        confirmed = clean_num(tds[1].get_text())
        if cn_deaths is not None:
            deceased = clean_num(tds[cn_deaths].get_text())
        if cn_recovered is not None:
            recovered = clean_num(tds[cn_recovered].get_text())
        if ifsg:
            econfirmed = clean_num(tds[1+1].get_text())
            edeceased = clean_num(tds[cn_deaths+1].get_text())
            cout.writerow([area, parse.parsedtime.isoformat(), confirmed, econfirmed, deceased, edeceased, recovered])
        elif cn_deaths is None:
            cout.writerow([area, parse.parsedtime.isoformat(), confirmed])
        elif cn_recovered is None:
            cout.writerow([area, parse.parsedtime.isoformat(), confirmed, deceased])
        else:
            cout.writerow([area, parse.parsedtime.isoformat(), confirmed, deceased, recovered])


parse.deploy_timestamp()

fetchhelper.git_commit([parse], args)
