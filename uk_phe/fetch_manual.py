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
from dataclasses import dataclass

datatz = dateutil.tz.gettz('Europe/London')

# Public Health England
update = fetchhelper.Updater('https://fingertips.phe.org.uk/documents/Historic%20COVID-19%20Dashboard%20Data.xlsx', ext='xlsx')
update.check_fetch(rawfile=args.rawfile, binary=True)
if args.only_changed:
    if not update.raw_changed():
        print("downloaded raw data unchanged")
        exit(0)


def clean_num(s):
    if not s:
        return 0
    return int(s)

def clean_label(s):
    return s.strip()

@dataclass
class CountryData:
    code: str
    name: str
    timestamp: datetime.datetime
    confirmed: int = None
    deaths: int = None

countrydata = {}

# sheet 4: confirmed per country
csv_confirmed_country = subprocess.run(['xlsx2csv', '-s', '4', update.rawfile], capture_output=True, check=True, encoding='utf-8').stdout
cr = csv.reader(csv_confirmed_country.split('\n'))
skip = True
header = None
for row in cr:
    if skip:
        if row[0] == 'Area Code':
            skip = False
            assert(row[1] == 'Area Name')
            header = row
            continue
        else:
            continue
    if row[1] == 'UK':
        break

    code = clean_label(row[0])
    country = clean_label(row[1])
    for n in range(2, len(header)):
        # There is no consistent date for these numbers, but we assume there are published at the end of the day
        timestamp = datetime.datetime.strptime(header[n] + ' 23:59', '%m-%d-%y %H:%M').replace(tzinfo=datatz)
        confirmed = clean_num(row[n])
        if timestamp not in countrydata:
            countrydata[timestamp] = {}
        tsdata = countrydata[timestamp]
        assert(country not in tsdata)
        tsdata[country] = CountryData(code, country, timestamp)
        tsdata[country].confirmed = confirmed


# sheet 3: deaths per country
# sheets 3 and 4 have completely different structure
csv_deaths_country = subprocess.run(['xlsx2csv', '-s', '3', update.rawfile], capture_output=True, check=True, encoding='utf-8').stdout
cr = csv.reader(csv_deaths_country.split('\n'))
skip = True
header = None
for row in cr:
    if skip:
        if row[0] == 'Date':
            skip = False
            assert(row[1] == 'Deaths')
            assert(row[2] == 'UK')
            header = row
            continue
        else:
            continue
    if not row:
        continue

    # There is no consistent date for these numbers, but we assume there are published at the end of the day
    timestamp = datetime.datetime.strptime(row[0] + ' 23:59', '%m-%d-%y %H:%M').replace(tzinfo=datatz)
    for n in [3, 4, 5, 6]:
        country = clean_label(header[n])
        if row[n] == '':
            continue
        deaths = clean_num(row[n])
        countrydata[timestamp][country].deaths = deaths

parses = []
for timestamp, tsdata in sorted(countrydata.items()):
    parse = fetchhelper.ParseData(update, 'countries')
    parse.parsedtime = timestamp

    has_deaths = any(cdata.deaths is not None for cdata in tsdata.values())

    with open(parse.parsedfile, 'w') as f:
        cw = csv.writer(f)
        header = ['Code', 'Country', 'Timestamp', 'Confirmed']
        if has_deaths:
            header.append('Deaths')
        cw.writerow(header)
        for _, cdata in sorted(tsdata.items()):
            row = [cdata.code, cdata.name, cdata.timestamp.isoformat(), cdata.confirmed]
            if cdata.deaths is not None:
                row.append(cdata.deaths)
            cw.writerow(row)

    parse.diff()
    if args.only_changed:
        if not parse.parseddiff.changed:
            print("parsed content \"%s\" unchanged" % parse.label)
            continue
    parse.deploy_timestamp()
    print("written %s" % parse.deployfile)
    parses.append(parse)


# sheet 6: cases per UTLA
@dataclass
class UTLAData:
    code: str
    utla: str
    nhsregion: str
    region: str
    timestamp: datetime.datetime
    confirmed: int = None

csv_cases_utla = subprocess.run(['xlsx2csv', '-s', '6', update.rawfile], capture_output=True, check=True, encoding='utf-8').stdout
cr = csv.reader(csv_cases_utla.split('\n'))
regdata = {}
skip = True
for row in cr:
    if not row:
        continue
    if skip:
        if row[0] == 'Area Code':
            skip = False
            assert(row[1] == 'Area Name')
            assert(row[2] == 'NHS region')
            assert(clean_label(row[3]) == 'Region (Governement)')
            header = row
            continue
        else:
            continue
    if clean_label(row[1]) == 'England':
        break
    if clean_label(row[1]) == 'Unconfirmed':
        continue

    code = clean_label(row[0])
    utla = clean_label(row[1])
    nhsregion = clean_label(row[2])
    region = clean_label(row[3])
    for n in range(4, len(header)):
        # There is no consistent date for these numbers, but we assume there are published at the end of the day
        timestamp = datetime.datetime.strptime(header[n] + ' 23:59', '%m-%d-%y %H:%M').replace(tzinfo=datatz)
        confirmed = clean_num(row[n])
        if timestamp not in regdata:
            regdata[timestamp] = {}
        tsdata = regdata[timestamp]
        assert(utla not in tsdata)
        tsdata[utla] = UTLAData(code, utla, nhsregion, region, timestamp, confirmed=confirmed)

for timestamp, tsdata in sorted(regdata.items()):
    parse = fetchhelper.ParseData(update, 'utla')
    parse.parsedtime = timestamp

    with open(parse.parsedfile, 'w') as f:
        cw = csv.writer(f)
        cw.writerow(['Code', 'UTLA', 'NHSRegion', 'Region', 'Timestamp', 'Confirmed'])
        for _, rdata in sorted(tsdata.items()):
            cw.writerow([rdata.code, rdata.utla, rdata.nhsregion, rdata.region, rdata.timestamp.isoformat(), rdata.confirmed])

    parse.diff()
    if args.only_changed:
        if not parse.parseddiff.changed:
            print("parsed content \"%s\" unchanged" % parse.label)
            continue
    parse.deploy_timestamp()
    print("written %s" % parse.deployfile)
    parses.append(parse)

fetchhelper.git_commit(parses, args)
