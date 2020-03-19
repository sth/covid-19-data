#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

import subprocess, datetime, re, csv, os
from bs4 import BeautifulSoup
import dateutil.tz

datatz = dateutil.tz.gettz('Europe/Berlin')

update = fetchhelper.Updater('https://www.lgl.bayern.de/gesundheit/infektionsschutz/infektionskrankheiten_a_z/coronavirus/karte_coronavirus/index.htm')
update.check_fetch(rawfile=args.rawfile)
if args.only_changed:
    if not update.raw_changed():
        print("downloaded raw data unchanged")
        exit(0)

html = BeautifulSoup(update.rawdata, 'html.parser')

for p in html.select('.bildunterschrift'):
    text = p.get_text()
    mo = re.search('Stand: (\S* \S*)', text)
    if mo is None:
        continue
    update.contenttime = datetime.datetime.strptime(mo.group(1), '%d.%m.%Y %H:%M') \
        .replace(tzinfo=datatz)
    break

if update.contenttime is None:
    print("Couldn't find content time")
    exit(1)


def parse_table(parse, html, tabselect):
    for tab in html.select('table'):
        if tabselect(tab):
            with open(parse.parsedfile, 'w') as outf:
                cout = csv.writer(outf)
                cout.writerow(['Area', 'Date', 'Confirmed'])
                for tr in tab.select('tr')[1:-1]:
                    tds = tr.select('td')
                    assert(len(tds) == 2)
                    cout.writerow([tds[0].string, parse.parsedtime.isoformat(), tds[1].string])
            parse.diff()
            break
    else:
        print("couldn't find table %s" % parse.label)
        exit(1)

    if args.only_changed:
        if not parse.parseddiff.changed:
            print("parsed content \"%s\" unchanged" % parse.label)
            return

    # It changed. If the current day is later than the contenttime we assume the
    # content time is a mistake and we adjust it to the current day.
    # (This problem has happend before)
    if parse.update.rawtime.date() > parse.parsedtime.date():
        if parse.parseddiff.changed and not parse.parseddiff.first:
            print("Adjust date", parse.parsedtime, "->", parse.update.rawtime)
            parse.parsedtime = parse.update.rawtime

    parse.deploy_day()
    print("written %s" % parse.deployfile)

rparse = fetchhelper.ParseData(update, 'regierungsbezirk')
parse_table(rparse, html,
        (lambda tab: tab.select_one('th').string == 'Regierungsbezirk'))
lparse = fetchhelper.ParseData(update, 'landkreis')
parse_table(lparse, html,
        (lambda tab: tab.select_one('th').string in ['Landkreis', 'Land-/Stadtkreis']))

fetchhelper.git_commit([rparse, lparse], args)
