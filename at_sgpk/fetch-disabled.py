#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper, csvtools

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

fetchhelper.check_oldfetch(args)

if args.rawfile is not None:
    args.rawfile = args.rawfile.split(',')
else:
    args.rawfile = (None, None)

import subprocess, re, csv, os
from datetime import datetime
from collections import defaultdict
from bs4 import BeautifulSoup
import dateutil.tz

def cleannum(s):
    return int(s.replace('.', '').replace(',', '').rstrip('+*^◊'))

datatz = dateutil.tz.gettz('Europe/Vienna')

# source https://www.data.gv.at/katalog/dataset/ef8e980b-9644-45d8-b0e9-c6aaf0eff0c0
url_cases = 'https://covid19-dashboard.ages.at/data/CovidFaelle_Timeline.csv'
url_hospital = 'https://covid19-dashboard.ages.at/data/Hospitalisierung.csv'

def fetch_cases():
    update = fetchhelper.Updater(url_cases, ext='cases.csv')
    update.check_fetch(rawfile=args.rawfile[0], checkdh=False)

    coldefs = csvtools.CSVColumns(
            timestamp=['Time'],
            area=['Bundesland'],
            confirmed=['AnzahlFaelleSum'],
            deaths=['AnzahlTotSum'],
            recovered=['AnzahlGeheiltSum'],
            #hospital=["Hospitalisierung"],
            #intensive=["Intensivstation"],
            #tests=["Testungen"],
        )
    coldefs.set_type('timestamp', (lambda s: datetime.strptime(s, '%d.%m.%Y %H:%M:%S').replace(tzinfo=datatz)))
    coldefs.set_type('confirmed', int)
    coldefs.set_type('deaths', int)
    coldefs.set_type('recovered', int)

    cases = defaultdict(list)
    with open(update.rawfile, encoding='utf-8-sig') as rf:
        cr = csv.reader(rf, delimiter=';')
        header = next(cr)
        cols = coldefs.build(header)

        for line in cr:
            fields = cols.get(line)
            cases[fields.timestamp].append(fields)

    return update, cases

def fetch_hospitals():
    update = fetchhelper.Updater(url_hospital, ext='hospital.csv')
    update.check_fetch(rawfile=args.rawfile[1], checkdh=False)

    # Meldedatum;BundeslandID;Bundesland;NormalBettenBelCovid19;IntensivBettenKapGes;IntensivBettenBelCovid19;IntensivBettenBelNichtCovid19;IntensivBettenFrei;TestGesamt

    coldefs = csvtools.CSVColumns(
            timestamp=['Meldedatum'],
            area=['Bundesland'],
            hospital=["NormalBettenBelCovid19"],
            intensive=["IntensivBettenBelCovid19"],
            tests=["TestGesamt"],
        )
    coldefs.set_type('timestamp', (lambda s: datetime.strptime(s, '%d.%m.%Y %H:%M:%S').replace(tzinfo=datatz)))
    coldefs.set_type('hospital', int)
    coldefs.set_type('intensive', int)
    coldefs.set_type('tests', int)

    tests = defaultdict(list)
    with open(update.rawfile, encoding='utf-8-sig') as rf:
        cr = csv.reader(rf, delimiter=';')
        header = next(cr)
        cols = coldefs.build(header)

        for line in cr:
            fields = cols.get(line)
            tests[fields.timestamp].append(fields)

    return tests


# We assume `hospital` is updated not later than `cases`

update, cases = fetch_cases()
hospitals = fetch_hospitals()

case_ts = sorted(cases.keys())[-1]
case_lines = cases[case_ts]
hospital_lines = hospitals[case_ts]

hospital_lines_area = {hl.area: hl for hl in hospital_lines}

parse = fetchhelper.ParseData(update, 'data')
parse.parsedtime = case_ts
with open(parse.parsedfile, 'w') as f:
    cw = csv.writer(f)
    cw.writerow(['Area', 'Date', 'Confirmed', 'Deaths', 'Recovered', 'Hospital', 'Intensivecare', 'Tests'])
    for fields in case_lines:
        if fields.area == 'Österreich':
            continue
        hfields = hospital_lines_area[fields.area]
        cw.writerow([fields.area, fields.timestamp.isoformat(),
            fields.confirmed, fields.deaths, fields.recovered,
            hfields.hospital, hfields.intensive, hfields.tests])
parse.deploy_timestamp()

fetchhelper.git_commit([parse], args)
