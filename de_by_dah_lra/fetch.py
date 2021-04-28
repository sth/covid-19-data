#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

fetchhelper.check_oldfetch(args)

if args.rawfile is None:
    rawfiles = (None, None)
else:
    rawfiles = args.rawfile.split(',')

import datetime, re, csv, json, os, sys, shutil
import dateutil.tz

url_cases = 'https://atlas.jifo.co/api/connectors/41be7d71-7260-497f-a60b-adce5aa9445d'
url_recovered = 'https://atlas.jifo.co/api/connectors/2adaf217-e526-492a-bcad-5ed6ec6ad3ad'

datatz = dateutil.tz.gettz('Europe/Berlin')

update = fetchhelper.Updater(url_cases, ext='cases.json')
update.check_fetch(rawfile=rawfiles[0])
jdat = json.loads(update.rawdata)

header = jdat['data'][0][0]
i_kom = header.index("Ort")
i_con = header.index("Gesamtzahl seit Ausbruch")

parses = []

parse = fetchhelper.ParseData(update, 'data')
parse.parsedtime = datetime.datetime.fromtimestamp(jdat['refreshed']/1000, tz=datatz)
with open(parse.parsedfile, 'w') as f:
    cw = csv.writer(f)
    cw.writerow(['Kommune', 'Timestamp', 'Confirmed'])
    for jrow in jdat['data'][0][1:]:
        kom = jrow[i_kom]
        if kom in ('Zuordnung fehlt', 'Gesamt', ''):
            continue
        if kom.startswith('Stand vom'):
            continue
        if jrow[i_kom] == 'Pfaffenhofen a.d.Glonn':
            jrow[i_kom] = 'Pfaffenhofen a.d. Glonn'
        cw.writerow([jrow[i_kom], parse.parsedtime.isoformat(), jrow[i_con]])

parse.deploy_timestamp()

if fetchhelper.csv_equal(parse.deployfile, parse.deployfile_previous(), skip=['Timestamp']):
    os.unlink(parse.deployfile)
else:
    parses.append(parse)


update = fetchhelper.Updater(url_recovered, ext='rec.json')
update.check_fetch(rawfile=rawfiles[1])
jdat = json.loads(update.rawdata)

header = jdat['data'][0][0]
i_kom = header.index("Ort")
i_rec = 1
assert(header[i_rec].startswith("Stand "))

parse = fetchhelper.ParseData(update, 'recovered')
parse.parsedtime = datetime.datetime.fromtimestamp(jdat['refreshed']/1000, tz=datatz)
with open(parse.parsedfile, 'w') as f:
    cw = csv.writer(f)
    cw.writerow(['Kommune', 'Timestamp', 'Recovered'])
    for jrow in jdat['data'][0][1:]:
        if jrow[i_kom] in ('Zuordnung fehlt', 'Gesamt', ''):
            continue
        if jrow[i_kom] == 'Pfaffenhofen a.d.Glonn':
            jrow[i_kom] = 'Pfaffenhofen a.d. Glonn'
        cw.writerow([jrow[i_kom], parse.parsedtime.isoformat(), jrow[i_rec]])

parse.deploy_timestamp()

if fetchhelper.csv_equal(parse.deployfile, parse.deployfile_previous(), skip=['Timestamp']):
    os.unlink(parse.deployfile)
else:
    parses.append(parse)

if parses:
    fetchhelper.git_commit(parses, args)
