#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

fetchhelper.check_oldfetch(args)

import subprocess, datetime, re, csv, os
from datetime import datetime
from bs4 import BeautifulSoup
import dateutil.tz

def cleannum(s):
    return int(s.replace('.', '').rstrip('+*^'))

datatz = dateutil.tz.gettz('Europe/Vienna')

update = fetchhelper.Updater('https://www.sozialministerium.at/Informationen-zum-Coronavirus/Neuartiges-Coronavirus-(2019-nCov).html')
update.check_fetch(rawfile=args.rawfile)

html = BeautifulSoup(update.rawdata, 'html.parser')

def strip_footnote(s):
    return s.rstrip('*')

table = fetchhelper.text_table(html.find('table'))
ths = table[0]
assert('Bundesland' in ths[0])
assert('gesamt' in ths[-1])
trs = table[1:]
assert('tigte' in trs[0][0])
assert('Todesf' in trs[1][0])
assert('Genesen' in trs[2][0])
assert('Hospital' in trs[3][0])
assert('Intensiv' in trs[4][0])
assert('Testungen' in trs[5][0])
parse = [
        fetchhelper.ParseData(update, 'confirmed'),
        fetchhelper.ParseData(update, 'deaths'),
        fetchhelper.ParseData(update, 'recovered'),
        fetchhelper.ParseData(update, 'hospital'),
        fetchhelper.ParseData(update, 'intensivecare'),
        fetchhelper.ParseData(update, 'tests'),
    ]
labels = ['confirmed', 'deceased', 'recovered', 'hospital', 'intensivecare', 'tests']

areas = {
        'Bgld.': 'Burgenland',
        'Kt.': 'Kärnten',
        'Ktn.': 'Kärnten',
        'NÖ': 'Niederösterreich',
        'OÖ': 'Oberösterreich',
        'Sbg.': 'Salzburg',
        'Stmk.': 'Steiermark',
        'T': 'Tirol',
        'Vbg.': 'Vorarlberg',
        'W': 'Wien'
    }

parses = []

for i, tds in enumerate(trs):
    assert(len(ths) == len(tds))
    mo = re.search(r'Stand (\d\d\.\d\d\.\d\d\d\d),[ \xa0]*(\d\d:\d\d) ?Uhr', tds[0])
    if mo is None:
        print("cannot parse date", file=sys.stderr)
        sys.exit(1)
    parse = fetchhelper.ParseData(update, labels[i])
    datadate = parse.parsedtime = datetime.strptime(mo.group(1) + ' ' + mo.group(2), '%d.%m.%Y %H:%M').replace(tzinfo=datatz)
    with open(parse.parsedfile, 'w') as f:
        cw = csv.writer(f)
        cw.writerow(['Area', 'Date', 'Value'])
        for col in range(1, len(tds)-1):
            area = areas[strip_footnote(ths[col])]
            count = cleannum(tds[col])
            cw.writerow([area, datadate.isoformat(), count])
    parse.deploy_timestamp()
    parses.append(parse)

fetchhelper.git_commit(parses, args)
