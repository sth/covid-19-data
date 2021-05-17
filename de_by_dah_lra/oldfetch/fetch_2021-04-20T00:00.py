#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

fetchhelper.check_oldfetch(args)

import datetime, re, csv, json, os, sys, shutil
import dateutil.tz

url = 'https://www.landratsamt-dachau.de/bilder/zahlen.jpg'
url = 'https://atlas.jifo.co/api/connectors/c3a4b965-0e10-46db-aec6-cceffdb74857'

datatz = dateutil.tz.gettz('Europe/Berlin')

update = fetchhelper.Updater(url, ext='json')
update.check_fetch(rawfile=args.rawfile)
jdat = json.loads(update.rawdata)

header = jdat['data'][0][0]
i_kom = header.index("Gemeinde")
i_con = header.index("Fälle insgesamt")
i_rec = header.index("Genesen")

parse = fetchhelper.ParseData(update, 'data')
parse.parsedtime = datetime.datetime.fromtimestamp(jdat['refreshed']/1000, tz=datatz)
with open(parse.parsedfile, 'w') as f:
    cw = csv.writer(f)
    cw.writerow(['Kommune', 'Timestamp', 'Confirmed', 'Recovered'])
    for jrow in jdat['data'][0][1:]:
        if jrow[i_kom] == 'Pfaffenhofen a.d.Glonn':
            jrow[i_kom] = 'Pfaffenhofen a.d. Glonn'
        cw.writerow([jrow[i_kom], parse.parsedtime.isoformat(), jrow[i_con], jrow[i_rec]])

parse.deploy_timestamp()
if fetchhelper.csv_equal(parse.deployfile, parse.deployfile_previous(), skip=['Timestamp']):
    os.unlink(parse.deployfile)
else:
    fetchhelper.git_commit([parse], args)

