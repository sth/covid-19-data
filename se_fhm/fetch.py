#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

import subprocess, datetime, re, csv, os, sys
import dateutil.tz

datatz = dateutil.tz.gettz('Europe/Stockholm')

#https://services5.arcgis.com/fsYDFeRKu1hELJJs/arcgis/rest/services/FOHM_Covid_19_FME_1/FeatureServer/1/query?f=json&where=Statistikdatum%3E%3Dtimestamp%20%272020-03-26%2023%3A00%3A00%27%20AND%20Statistikdatum%3C%3Dtimestamp%20%272020-03-27%2022%3A59%3A59%27&returnGeometry=false&spatialRel=esriSpatialRelIntersects&outFields=*&orderByFields=Statistikdatum%20desc&outSR=102100&resultOffset=0&resultRecordCount=2000&cacheHint=true

update = fetchhelper.Updater('https://services5.arcgis.com/fsYDFeRKu1hELJJs/arcgis/rest/services/FOHM_Covid_19_FME_1/FeatureServer/1/query?f=json&where=1%3d1&returnGeometry=false&spatialRel=esriSpatialRelIntersects&outFields=*&orderByFields=Statistikdatum%20desc&outSR=102100&resultOffset=0&resultRecordCount=2000&cacheHint=true', ext='json')
update.check_fetch(rawfile=args.rawfile)

import json
with open(update.rawfile) as f:
    jd = json.load(f)

#'Statistikdatum': 1581552000000,
areasum = {
    'Blekinge': 0,
    'Dalarna': 0,
    'Gotland': 0,
    'Gävleborg': 0,
    'Halland': 0,
    'Jämtland': 0,
    'Jönköping': 0,
    'Kalmar': 0,
    'Kronoberg': 0,
    'Norrbotten': 0,
    'Skåne': 0,
    'Stockholm': 0,
    'Södermanland': 0,
    'Uppsala': 0,
    'Värmland': 0,
    'Västerbotten': 0,
    'Västernorrland': 0,
    'Västmanland': 0,
    'Västra_Götaland': 0,
    'Örebro': 0,
    'Östergötland': 0,
}

parses = []
datatime = None
for feat in sorted(jd['features'], key=(lambda f: f['attributes']['Statistikdatum'])):
    attrs = feat['attributes']
    datatime = datetime.datetime.utcfromtimestamp(attrs['Statistikdatum']/1000).replace(hour=11, minute=30, tzinfo=datatz)
    for attr, value in attrs.items():
        if attr in areasum:
            areasum[attr] += value

parse = fetchhelper.ParseData(update, 'data', variant=datatime.isoformat())
parse.parsedtime = datatime
with open(parse.parsedfile, 'w') as outf:
    cw = csv.writer(outf)
    header = ['Area', 'Timestamp', 'Confirmed']
    cw.writerow(header)
    for area, count in sorted(areasum.items()):
        cw.writerow([area.replace('_', ' '), datatime.isoformat(), count])

parse.deploy_timestamp()
parses.append(parse)

fetchhelper.git_commit(parses, args)
