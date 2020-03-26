#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

import subprocess, csv
from datetime import datetime, timedelta
import dateutil.tz

datatz = dateutil.tz.gettz('Europe/Berlin')

update = fetchhelper.Updater('https://sozialministerium.baden-wuerttemberg.de/fileadmin/redaktion/m-sm/intern/downloads/Downloads_Gesundheitsschutz/Tabelle_Coronavirus-Faelle-BW.xlsx', ext='xlsx')

update.check_fetch(args.rawfile, binary=True)

parse = fetchhelper.ParseData(update, 'timeline')

proc = subprocess.Popen(['xlsx2csv', update.rawfile],
        stdout=subprocess.PIPE, encoding='utf-8')
cr = csv.reader(proc.stdout)

with open(parse.parsedfile, 'w') as pf:
    cpf = csv.writer(pf)
    start = False
    dates = None
    for row in cr:
        if not start:
            if row and row[0] == 'Stadt-/Landkreis':
                start = True
            continue
        if dates is None:
            dates = [
                    datetime.strptime(d, '%m-%d-%y').replace(tzinfo=datatz) + timedelta(hours=15)
                    for d in row[1:]]
            cpf.writerow(['Dates'] + [d.isoformat() for d in dates])
            continue
        if row and row[0] == 'Summe':
            break

        area = row[0]
        values = [(int(v) if v else 0) for v in row[1:]]
        cpf.writerow([area] + values)
parse.diff()

if args.only_changed:
    if not parse.parseddiff.changed:
        print("parsed content \"%s\" unchanged" % parse.label)
        exit(0)

parse.deploy_combined()
print("written %s" % parse.deployfile)

fetchhelper.git_commit([parse], args)
