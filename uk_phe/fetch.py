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

regions = {
    'E06000001': ('Hartlepool', 'North East'),
    'E06000002': ('Middlesbrough', 'North East'),
    'E06000003': ('Redcar and Cleveland', 'North East'),
    'E06000004': ('Stockton-on-Tees', 'North East'),
    'E06000005': ('Darlington', 'North East'),
    'E06000006': ('Halton', 'North West'),
    'E06000007': ('Warrington', 'North West'),
    'E06000008': ('Blackburn with Darwen', 'North West'),
    'E06000009': ('Blackpool', 'North West'),
    'E06000010': ('Kingston upon Hull, City of', 'Yorkshire and The Humber'),
    'E06000011': ('East Riding of Yorkshire', 'Yorkshire and The Humber'),
    'E06000012': ('North East Lincolnshire', 'Yorkshire and The Humber'),
    'E06000013': ('North Lincolnshire', 'Yorkshire and The Humber'),
    'E06000014': ('York', 'Yorkshire and The Humber'),
    'E06000015': ('Derby', 'East Midlands'),
    'E06000016': ('Leicester', 'East Midlands'),
    'E06000017': ('Rutland', 'East Midlands'),
    'E06000018': ('Nottingham', 'East Midlands'),
    'E06000019': ('Herefordshire, County of', 'West Midlands'),
    'E06000020': ('Telford and Wrekin', 'West Midlands'),
    'E06000021': ('Stoke-on-Trent', 'West Midlands'),
    'E06000022': ('Bath and North East Somerset', 'South West'),
    'E06000023': ('Bristol, City of', 'South West'),
    'E06000024': ('North Somerset', 'South West'),
    'E06000025': ('South Gloucestershire', 'South West'),
    'E06000026': ('Plymouth', 'South West'),
    'E06000027': ('Torbay', 'South West'),
    'E06000030': ('Swindon', 'South West'),
    'E06000031': ('Peterborough', 'East of England'),
    'E06000032': ('Luton', 'East of England'),
    'E06000033': ('Southend-on-Sea', 'East of England'),
    'E06000034': ('Thurrock', 'East of England'),
    'E06000035': ('Medway', 'South East'),
    'E06000036': ('Bracknell Forest', 'South East'),
    'E06000037': ('West Berkshire', 'South East'),
    'E06000038': ('Reading', 'South East'),
    'E06000039': ('Slough', 'South East'),
    'E06000040': ('Windsor and Maidenhead', 'South East'),
    'E06000041': ('Wokingham', 'South East'),
    'E06000042': ('Milton Keynes', 'South East'),
    'E06000043': ('Brighton and Hove', 'South East'),
    'E06000044': ('Portsmouth', 'South East'),
    'E06000045': ('Southampton', 'South East'),
    'E06000046': ('Isle of Wight', 'South East'),
    'E06000047': ('County Durham', 'North East'),
    'E06000049': ('Cheshire East', 'North West'),
    'E06000050': ('Cheshire West and Chester', 'North West'),
    'E06000051': ('Shropshire', 'West Midlands'),
    'E06000052': ('Cornwall and Isles of Scilly', 'South West'),
    'E06000054': ('Wiltshire', 'South West'),
    'E06000055': ('Bedford', 'East of England'),
    'E06000056': ('Central Bedfordshire', 'East of England'),
    'E06000057': ('Northumberland', 'North East'),
    'E06000058': ('Bournemouth, Christchurch and Poole', 'South West'),
    'E06000059': ('Dorset', 'South West'),
    'E08000001': ('Bolton', 'North West'),
    'E08000002': ('Bury', 'North West'),
    'E08000003': ('Manchester', 'North West'),
    'E08000004': ('Oldham', 'North West'),
    'E08000005': ('Rochdale', 'North West'),
    'E08000006': ('Salford', 'North West'),
    'E08000007': ('Stockport', 'North West'),
    'E08000008': ('Tameside', 'North West'),
    'E08000009': ('Trafford', 'North West'),
    'E08000010': ('Wigan', 'North West'),
    'E08000011': ('Knowsley', 'North West'),
    'E08000012': ('Liverpool', 'North West'),
    'E08000013': ('St. Helens', 'North West'),
    'E08000014': ('Sefton', 'North West'),
    'E08000015': ('Wirral', 'North West'),
    'E08000016': ('Barnsley', 'Yorkshire and The Humber'),
    'E08000017': ('Doncaster', 'Yorkshire and The Humber'),
    'E08000018': ('Rotherham', 'Yorkshire and The Humber'),
    'E08000019': ('Sheffield', 'Yorkshire and The Humber'),
    'E08000021': ('Newcastle upon Tyne', 'North East'),
    'E08000022': ('North Tyneside', 'North East'),
    'E08000023': ('South Tyneside', 'North East'),
    'E08000024': ('Sunderland', 'North East'),
    'E08000025': ('Birmingham', 'West Midlands'),
    'E08000026': ('Coventry', 'West Midlands'),
    'E08000027': ('Dudley', 'West Midlands'),
    'E08000028': ('Sandwell', 'West Midlands'),
    'E08000029': ('Solihull', 'West Midlands'),
    'E08000030': ('Walsall', 'West Midlands'),
    'E08000031': ('Wolverhampton', 'West Midlands'),
    'E08000032': ('Bradford', 'Yorkshire and The Humber'),
    'E08000033': ('Calderdale', 'Yorkshire and The Humber'),
    'E08000034': ('Kirklees', 'Yorkshire and The Humber'),
    'E08000035': ('Leeds', 'Yorkshire and The Humber'),
    'E08000036': ('Wakefield', 'Yorkshire and The Humber'),
    'E08000037': ('Gateshead', 'North East'),
    'E09000002': ('Barking and Dagenham', 'London'),
    'E09000003': ('Barnet', 'London'),
    'E09000004': ('Bexley', 'London'),
    'E09000005': ('Brent', 'London'),
    'E09000006': ('Bromley', 'London'),
    'E09000007': ('Camden', 'London'),
    'E09000008': ('Croydon', 'London'),
    'E09000009': ('Ealing', 'London'),
    'E09000010': ('Enfield', 'London'),
    'E09000011': ('Greenwich', 'London'),
    'E09000012': ('Hackney and City of London', 'London'),
    'E09000013': ('Hammersmith and Fulham', 'London'),
    'E09000014': ('Haringey', 'London'),
    'E09000015': ('Harrow', 'London'),
    'E09000016': ('Havering', 'London'),
    'E09000017': ('Hillingdon', 'London'),
    'E09000018': ('Hounslow', 'London'),
    'E09000019': ('Islington', 'London'),
    'E09000020': ('Kensington and Chelsea', 'London'),
    'E09000021': ('Kingston upon Thames', 'London'),
    'E09000022': ('Lambeth', 'London'),
    'E09000023': ('Lewisham', 'London'),
    'E09000024': ('Merton', 'London'),
    'E09000025': ('Newham', 'London'),
    'E09000026': ('Redbridge', 'London'),
    'E09000027': ('Richmond upon Thames', 'London'),
    'E09000028': ('Southwark', 'London'),
    'E09000029': ('Sutton', 'London'),
    'E09000030': ('Tower Hamlets', 'London'),
    'E09000031': ('Waltham Forest', 'London'),
    'E09000032': ('Wandsworth', 'London'),
    'E09000033': ('Westminster', 'London'),
    'E10000002': ('Buckinghamshire', 'South East'),
    'E10000003': ('Cambridgeshire', 'East of England'),
    'E10000006': ('Cumbria', 'North West'),
    'E10000007': ('Derbyshire', 'East Midlands'),
    'E10000008': ('Devon', 'South West'),
    'E10000011': ('East Sussex', 'South East'),
    'E10000012': ('Essex', 'East of England'),
    'E10000013': ('Gloucestershire', 'South West'),
    'E10000014': ('Hampshire', 'South East'),
    'E10000015': ('Hertfordshire', 'East of England'),
    'E10000016': ('Kent', 'South East'),
    'E10000017': ('Lancashire', 'North West'),
    'E10000018': ('Leicestershire', 'East Midlands'),
    'E10000019': ('Lincolnshire', 'East Midlands'),
    'E10000020': ('Norfolk', 'East of England'),
    'E10000021': ('Northamptonshire', 'East Midlands'),
    'E10000023': ('North Yorkshire', 'Yorkshire and The Humber'),
    'E10000024': ('Nottinghamshire', 'East Midlands'),
    'E10000025': ('Oxfordshire', 'South East'),
    'E10000027': ('Somerset', 'South West'),
    'E10000028': ('Staffordshire', 'West Midlands'),
    'E10000029': ('Suffolk', 'East of England'),
    'E10000030': ('Surrey', 'South East'),
    'E10000031': ('Warwickshire', 'West Midlands'),
    'E10000032': ('West Sussex', 'South East'),
    'E10000034': ('Worcestershire', 'West Midlands'),
}

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
    if not row[0]:
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
    region: str
    timestamp: datetime.datetime
    confirmed: int = None

csv_cases_utla = subprocess.run(['xlsx2csv', '-s', '6', update.rawfile], capture_output=True, check=True, encoding='utf-8').stdout
cr = csv.reader(csv_cases_utla.split('\n'))
regdata = {}
skip = True
basecol = 0
for row in cr:
    if not row:
        continue
    if skip:
        if row[0] == 'Area Code':
            skip = False
            assert(row[1] == 'Area Name')
            basecol = 2
            if clean_label(row[2]) == 'NHS region' and clean_label(row[3]) == 'Region (Governement)':
                basecol = 4
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
    region = regions[code][1]
    for n in range(basecol, len(header)):
        # There is no consistent date for these numbers, but we assume there are published at the end of the day
        timestamp = datetime.datetime.strptime(header[n] + ' 23:59', '%m-%d-%y %H:%M').replace(tzinfo=datatz)
        if header[n] == '04-09-20' and header[n] == header[n-1]:
            timestamp += datetime.timedelta(days=1)
        confirmed = clean_num(row[n])
        if timestamp not in regdata:
            regdata[timestamp] = {}
        tsdata = regdata[timestamp]
        assert(utla not in tsdata)
        tsdata[utla] = UTLAData(code, utla, region, timestamp, confirmed=confirmed)

for timestamp, tsdata in sorted(regdata.items()):
    parse = fetchhelper.ParseData(update, 'utla')
    parse.parsedtime = timestamp

    with open(parse.parsedfile, 'w') as f:
        cw = csv.writer(f)
        cw.writerow(['Code', 'UTLA', 'Region', 'Timestamp', 'Confirmed'])
        for _, rdata in sorted(tsdata.items()):
            cw.writerow([rdata.code, rdata.utla, rdata.region, rdata.timestamp.isoformat(), rdata.confirmed])

    parse.diff()
    if args.only_changed:
        if not parse.parseddiff.changed:
            print("parsed content \"%s\" unchanged" % parse.label)
            continue
    parse.deploy_timestamp()
    print("written %s" % parse.deployfile)
    parses.append(parse)

fetchhelper.git_commit(parses, args)
