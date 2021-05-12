#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper, csvtools

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

fetchhelper.check_oldfetch(args)

import subprocess, datetime, re, csv, os
from datetime import datetime
from bs4 import BeautifulSoup
import dateutil.tz

def cleannum(s):
    return int(s.replace('.', '').replace(',', '').rstrip('+*^◊'))

datatz = dateutil.tz.gettz('Europe/Vienna')

# page:
url = 'https://www.sozialministerium.at/Informationen-zum-Coronavirus/Neuartiges-Coronavirus-(2019-nCov).html'
# iframe:
url = 'https://info.gesundheitsministerium.gv.at/?re=tabelle'
# csv:
url = 'https://info.gesundheitsministerium.gv.at/data/timeline-faelle-bundeslaender.csv'

update = fetchhelper.Updater(url, ext='csv')
update.check_fetch(rawfile=args.rawfile, checkdh=False)

coldefs = csvtools.CSVColumns(
        timestamp=['Datum'],
        area=['Name'],
        confirmed=['BestaetigteFaelleBundeslaender'],
        deaths=['Todesfaelle'],
        recovered=['Genesen'],
        hospital=["Hospitalisierung"],
        intensive=["Intensivstation"],
        tests=["Testungen"],
    )
coldefs.set_type('timestamp', datetime.fromisoformat)
coldefs.set_type('confirmed', int)
coldefs.set_type('deaths', int)
coldefs.set_type('recovered', int)

with open(update.rawfile, encoding='utf-8-sig') as rf:
    cr = csv.reader(rf, delimiter=';')
    header = next(cr)
    cols = coldefs.build(header)

    newest_ts = None
    newest = []
    for line in cr:
        fields = cols.get(line)
        if newest_ts is None or fields.timestamp > newest_ts:
            newest_ts = fields.timestamp
            newest = []
        newest.append(fields)

parse = fetchhelper.ParseData(update, 'data')
parse.parsedtime = newest_ts
with open(parse.parsedfile, 'w') as f:
    cw = csv.writer(f)
    cw.writerow(['Area', 'Date', 'Confirmed', 'Deaths', 'Recovered', 'Hospital', 'Intensivecare', 'Tests'])
    for fields in newest:
        if fields.area == 'Österreich':
            continue
        cw.writerow([fields.area, fields.timestamp.isoformat(),
            fields.confirmed, fields.deaths, fields.recovered,
            fields.hospital, fields.intensive, fields.tests])
parse.deploy_timestamp()

fetchhelper.git_commit([parse], args)
