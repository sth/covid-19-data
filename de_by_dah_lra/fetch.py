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

update = fetchhelper.Updater('https://www.landratsamt-dachau.de/gesundheit-veterinaerwesen-sicherheitsrecht/gesundheit/coronavirus/')
update.check_fetch(rawfile=args.rawfile)

# accidentally duplicated <tr> and other hrml errors
html = BeautifulSoup(update.rawdata, 'html.parser')

parse = fetchhelper.ParseData(update, 'data')

txt = str(html.find(text=re.compile('Landkreis-Statistik ')))
mo = re.search(r'Landkreis-Statistik(?: nach Gemeinden)? für den (\d\d.\d\d.\d\d\d\d)', txt)
datatime = parse.parsedtime = update.contenttime = datetime.datetime.strptime(mo.group(1) + ' 21:30', '%d.%m.%Y %H:%M').replace(tzinfo=datatz)

table = html.find(text=re.compile('Sars-CoV-2 Infizierte')).find_parent('table')
rows = fetchhelper.text_table(table)

ths = rows[0]
assert('Infizierte' in ths[1])
assert('Geheilt' in ths[2])

with open(parse.parsedfile, 'w') as outf:
    cout = csv.writer(outf)
    cout.writerow(['Kommune', 'Timestamp', 'Confirmed', 'Recovered'])

    assert('Gesamt' in rows[-1])
    for tds in rows[1:-1]:
        cout.writerow((tds[0], datatime.isoformat(), int(tds[1]), int(tds[2])))

parse.deploy_timestamp()

fetchhelper.git_commit([parse], args)
