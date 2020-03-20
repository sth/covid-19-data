#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

import subprocess, datetime, re, csv, os
from datetime import datetime
from bs4 import BeautifulSoup
import dateutil.tz

def cleannum(s):
    return int(s.replace('.', ''))

datatz = dateutil.tz.gettz('Europe/Vienna')

update = fetchhelper.Updater('https://www.sozialministerium.at/Informationen-zum-Coronavirus/Neuartiges-Coronavirus-(2019-nCov).html')
update.check_fetch(rawfile=args.rawfile)
if args.only_changed:
    if not update.raw_changed():
        print("downloaded raw data unchanged")
        exit(0)

html = BeautifulSoup(update.rawdata, 'html.parser')

def parse_counts(parse, base, lead):
    txt = base.find(string=re.compile(lead)).find_parent('p').get_text()
    mo = re.search(r'Stand (\d\d.\d\d.\d\d\d\d, \d\d:\d\d) Uhr', txt)
    parse.parsedtime = datetime.strptime(mo.group(1), '%d.%m.%Y, %H:%M').replace(tzinfo=datatz)

    mo = re.search(r': ([0-9.]+)(?: Fälle)?, nach Bundesl.*ndern: (.*)\.\s*$', txt)
    total = cleannum(mo.group(1))

    with open(parse.parsedfile, 'w') as outf:
        cout = csv.writer(outf)
        cout.writerow(['Area', 'Date', 'Value'])
        for part in mo.group(2).split(','):
            mop = re.search(r'^(.*) \((.*)\)', part.strip())
            key = mop.group(1).strip()
            value = cleannum(mop.group(2))
            cout.writerow([key, parse.parsedtime.isoformat(), value])

    if args.only_changed:
        if not parse.parseddiff.changed:
            print("parsed content \"%s\" unchanged" % parse.label)
            return

    parse.deploy_timestamp()

infobox = html.find("div", class_="infobox")

parse_c = fetchhelper.ParseData(update, 'confirmed')
parse_counts(parse_c, infobox, "Best.*tigte F.*lle")

parse_r = fetchhelper.ParseData(update, 'recovered')
parse_counts(parse_r, infobox, "Genesene Personen")

parse_d = fetchhelper.ParseData(update, 'deceased')
parse_counts(parse_d, infobox, "Todesf.*lle")

fetchhelper.git_commit([parse_c, parse_r, parse_d], args)
