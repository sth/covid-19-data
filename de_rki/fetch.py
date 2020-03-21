#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

import datetime, re, csv, os
from bs4 import BeautifulSoup
import dateutil.tz

datatz = dateutil.tz.gettz('Europe/Berlin')

update = fetchhelper.Updater('https://www.rki.de/DE/Content/InfAZ/N/Neuartiges_Coronavirus/Fallzahlen.html')
update.check_fetch(rawfile=args.rawfile)
if args.only_changed:
    if not update.raw_changed():
        print("downloaded raw data unchanged")
        exit(0)

html = BeautifulSoup(update.rawdata, 'html.parser')

header = html.find(text="Fallzahlen in Deutschland")
par = header.parent.next_sibling.next_sibling

mo = re.search('Stand: (\S*, \S*) Uhr', par.get_text())
if mo is None:
    print("Couldn't find content time")
    exit(1)
update.contenttime = datetime.datetime.strptime(mo.group(1), '%d.%m.%Y, %H:%M') \
    .replace(tzinfo=datatz)

def clean_num(numstr):
    return int(numstr.replace('.', '').strip())

def parse_td(content):
    mo = re.search(r'(.*)\((.*)\)\s*', content)
    if mo is None:
        return (clean_num(content), 0)
    else:
        return (clean_num(mo.group(1)), clean_num(mo.group(2)))

parse = fetchhelper.ParseData(update, 'data')
for tab in header.parent.parent.select('table'):
    # There was a stray character in the middle of the word
    if not re.search(r'^Bundes.?land', tab.select('thead th')[0].text):
        continue
    with open(parse.parsedfile, 'w') as outf:
        cout = csv.writer(outf)
        cout.writerow(['Area', 'Date', 'EConfirmed', 'EDeaths'])
        for tr in tab.select('table tbody tr')[:-1]:
            tds = tr.select('td')
            assert(len(tds) == 6)
            econfirmed = clean_num(tds[1].get_text())
            edeaths = clean_num(tds[4].get_text())
            cout.writerow([tds[0].string, parse.parsedtime.isoformat(),
                econfirmed, edeaths])
    parse.diff()
    break
else:
    print("couldn't find table %s" % parse.label)
    exit(1)

if args.only_changed:
    if not parse.parseddiff.changed:
        print("parsed content \"%s\" unchanged" % parse.label)
        exit(0)

# It changed. If the current day is later than the contenttime we assume the
# content time is a mistake and we adjust it to the current day.
# (This problem has happend before)
if parse.update.rawtime.date() > parse.parsedtime.date():
    if parse.parseddiff.changed and not parse.parseddiff.first:
        print("Adjust date", parse.parsedtime, "->", parse.update.rawtime)
        parse.parsedtime = parse.update.rawtime

parse.deploy_day()
print("written %s" % parse.deployfile)

fetchhelper.git_commit([parse], args)
