#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

fetchhelper.check_oldfetch(args)


import subprocess, datetime, re, csv, os, sys
from bs4 import BeautifulSoup
import dateutil.tz

datatz = dateutil.tz.gettz('Europe/Berlin')

update = fetchhelper.Updater('https://www.landkreis-muenchen.de/themen/verbraucherschutz-gesundheit/gesundheit/coronavirus/fallzahlen/')
update.check_fetch(rawfile=args.rawfile)

# accidentally duplicated <tr> and other hrml errors
html = BeautifulSoup(update.rawdata, 'html.parser')

parse = fetchhelper.ParseData(update, 'data')

txt = str(html.find(text=re.compile('(?:Stand|Datenstand): ')))
for timere, timefmt in [
        (r'(?:Stand|Datenstand): (\d\d\.\d\d\.\d\d\d\d, \d\d:\d\d) ?Uhr', '%d.%m.%Y, %H:%M'),
        (r'(?:Stand|Datenstand): (\d\d\.\d\d\.\d\d\d\d, \d\d\.\d\d) ?Uhr', '%d.%m.%Y, %H.%M'),
        (r'(?:Stand|Datenstand): (\d\d\.\d\d\.\d\d\d\d, \d\d) ?Uhr', '%d.%m.%Y, %H'),
        (r'(?:Stand|Datenstand): (\d\d\.\d\d\.\d\d\d\d, \d\d) ?Uhr', '%d.%m.%Y, %H'),
        (r'(?:Stand|Datenstand): (\d\d\.\d\d\.\d\d\d\d)\)', '%d.%m.%Y'),
        ]:
    mo = re.search(timere, txt)
    if mo is None:
        continue
    timestr = mo.group(1)
    if 'Uhr' not in timestr:
        timestr += ' %s' % update.rawtime.time().hour
        timefmt += ' %H'
    datatime = parse.parsedtime = update.contenttime = datetime.datetime.strptime(timestr, timefmt).replace(tzinfo=datatz)
    print(datatime)

if datatime is None:
    print("cannot find datatime in %r" % txt, file=sys.stderr)
    sys.exit(1)

def clean_num(s):
    return int(s.replace('.', '').replace('*', ''))

area_map = {
        'Garching': 'Garching b. München',
        'Kirchheim': 'Kirchheim b. München',
        'Pullach': 'Pullach im Isartal',
    }

def canonical_area(area):
    return area_map.get(area, area)


title = html.find(text=re.compile('Fallzahlen nach Gemeinden')).find_parent('h2')

rows = fetchhelper.text_table(title.find_next_sibling('table'))

assert(len(rows[0]) == 2 or len(rows[0]) == 3)
if rows[0][0] == 'Kommune':
    rows = rows[1:]

with open(parse.parsedfile, 'w') as outf:
    cout = csv.writer(outf)
    header = ('Kommune', 'Timestamp', 'Confirmed')
    cout.writerow(header)
    for tds in rows:
        if not tds[0].strip() and not tds[1].strip():
            continue
        cout.writerow((canonical_area(tds[0]), datatime.isoformat(), clean_num(tds[1])))

parse.deploy_timestamp()

fetchhelper.git_commit([parse], args)
