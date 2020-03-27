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

    txt = txt.replace('\xa0', ' ')
    mo = re.search(r': ([0-9.]+)(?: Fälle)?, nach Bundesl.*ndern: (.*)\.\s*$', txt)
    total = cleannum(mo.group(1))

    with open(parse.parsedfile, 'w') as outf:
        cout = csv.writer(outf)
        cout.writerow(['Area', 'Date', 'Value'])
        for mop in re.finditer(r'(.*?) \((.*?)\),?', mo.group(2)):
            key = mop.group(1).strip()
            value = cleannum(mop.group(2))
            cout.writerow([key, parse.parsedtime.isoformat(), value])

    parse.diff()
    if args.only_changed:
        if not parse.parseddiff.changed:
            print("parsed content \"%s\" unchanged" % parse.label)
            return

    parse.deploy_timestamp()

infobox = html.find("div", class_="infobox")

parses = []
parse_c = fetchhelper.ParseData(update, 'confirmed')
parse_counts(parse_c, infobox, "Best.*tigte F.*lle")
parses.append(parse_c)

parse_r = fetchhelper.ParseData(update, 'recovered')
try:
    parse_counts(parse_r, infobox, "Genesene Personen")
    parses.append(parse_r)
except AttributeError as err:
    # It seems to be removed, we ignore it
    print(err)

parse_d = fetchhelper.ParseData(update, 'deceased')
parse_counts(parse_d, infobox, "Todesf.*lle")
parses.append(parse_d)

fetchhelper.git_commit(parses, args)
