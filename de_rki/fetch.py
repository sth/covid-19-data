#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

fetchhelper.check_oldfetch(args)

import datetime, re, csv, os
from bs4 import BeautifulSoup
import dateutil.tz

datatz = dateutil.tz.gettz('Europe/Berlin')

update = fetchhelper.Updater('https://www.rki.de/DE/Content/InfAZ/N/Neuartiges_Coronavirus/Fallzahlen.html')
update.check_fetch(rawfile=args.rawfile)

html = BeautifulSoup(update.rawdata, 'html.parser')

header = html.find(text="Fallzahlen in Deutschland")
par = header.parent.next_sibling.next_sibling

mo = re.search('Stand: (\S*, \S*) Uhr', par.get_text())
if mo is None:
    print("Couldn't find content time", file=sys.stderr)
    exit(1)
update.contenttime = datetime.datetime.strptime(mo.group(1), '%d.%m.%Y, %H:%M') \
    .replace(tzinfo=datatz)

aliases = {
    'Branden-burg': 'Brandenburg',
    'Meck-lenburg-Vorpommern': 'Mecklenburg-Vorpommern',
    'Nord-rhein-Westfalen': 'Nordrhein-Westfalen',
    'Nieder-sachsen': 'Niedersachsen',
}

good = set([
    'Baden-Württemberg', 'Bayern', 'Berlin', 'Brandenburg', 'Bremen', 'Hamburg', 'Hessen',
    'Mecklenburg-Vorpommern', 'Niedersachsen', 'Nordrhein-Westfalen', 'Rheinland-Pfalz',
    'Saarland', 'Sachsen', 'Sachsen-Anhalt', 'Schleswig-Holstein', 'Thüringen',
])

def clean_label(lstr):
    lstr = lstr.replace('\n', '').replace('\xad', '').replace('*', '')
    return aliases.get(lstr, lstr)

def clean_num(numstr):
    return int(numstr.replace('.', '').strip() or '0')

def parse_td(content):
    mo = re.search(r'(.*)\((.*)\)\s*', content)
    if mo is None:
        return (clean_num(content), 0)
    else:
        return (clean_num(mo.group(1)), clean_num(mo.group(2)))

parse = fetchhelper.ParseData(update, 'data')
for tab in header.parent.parent.select('table'):
    if clean_label(tab.select('thead th')[0].text) != 'Bundesland':
        continue
    with open(parse.parsedfile, 'w') as outf:
        cout = csv.writer(outf)
        cout.writerow(['Bundesland', 'Timestamp', 'EConfirmed', 'EDeaths'])
        for tr in tab.select('table tbody tr')[:-1]:
            tds = tr.select('td')
            assert(len(tds) in [5, 6])
            area = clean_label(tds[0].get_text())
            if area not in good:
                print("unknown area:", area, file=sys.stderr)
                sys.exit(1)
            econfirmed = clean_num(tds[1].get_text())
            edeaths = clean_num(tds[5].get_text())
            cout.writerow([area, parse.parsedtime.isoformat(),
                econfirmed, edeaths])
    break
else:
    print("couldn't find table %s" % parse.label, file=sys.stderr)
    exit(1)

# If the current day is later than the contenttime we assume the
# content time is a mistake and we adjust it to the current day.
# (This problem has happend before)
# Let's hope it doesn't happen again.
#if parse.update.rawtime.date() > parse.parsedtime.date():
#    if parse.parseddiff.changed and not parse.parseddiff.first:
#        print("Adjust date", parse.parsedtime, "->", parse.update.rawtime)
#        parse.parsedtime = parse.update.rawtime

parse.deploy_timestamp()

fetchhelper.git_commit([parse], args)
