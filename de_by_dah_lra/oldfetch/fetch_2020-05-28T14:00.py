#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

fetchhelper.check_oldfetch(args)

if args.rawfile:
    args.rawfile = args.rawfile.split(',', 1)
else:
    args.rawfile = (None, None)

import subprocess, datetime, re, csv, os, sys, shutil
import urllib.parse
from bs4 import BeautifulSoup
import dateutil.tz

url = 'https://www.landratsamt-dachau.de/gesundheit-veterinaerwesen-sicherheitsrecht/gesundheit/coronavirus/corona-statistiken/'

datatz = dateutil.tz.gettz('Europe/Berlin')

update = fetchhelper.Updater(url)
update.check_fetch(rawfile=args.rawfile[0])

html = BeautifulSoup(update.rawdata, 'html.parser')

parse = fetchhelper.ParseData(update, 'data')

#txt = str(html.find(text=re.compile('Landkreis-Statistik ')))
#mo = re.search(r'Landkreis-Statistik(?: nach Gemeinden)? für den (\d\d.\d\d.\d\d\d\d)', txt)
#datatime = parse.parsedtime = update.contenttime = datetime.datetime.strptime(mo.group(1) + ' 21:30', '%d.%m.%Y %H:%M').replace(tzinfo=datatz)

iframe = html.find('iframe')
furl = urllib.parse.urljoin(url, iframe['src'])

update_f = fetchhelper.Updater(furl, ext='iframe.html')
update_f.check_fetch(rawfile=args.rawfile[1], remotetime=True)
datatime = datetime.datetime.fromtimestamp(os.stat(update_f.rawfile).st_mtime, tz=datatz)

html = BeautifulSoup(update_f.rawdata, 'html.parser')
parse = fetchhelper.ParseData(update, 'data')
# page claims updates are at 16:30 and shortly before midnight
if datatime.time() < datetime.time(hour=16):
    parse.parsedtime = (datatime - datetime.timedelta(day=1)).replace(hour=23, minute=50)
elif datatime.time() < datetime.time(hour=23):
    parse.parsedtime = datatime.replace(hour=16, minute=30)
else:
    parse.parsedtime = datatime

txt = html.find(text=re.compile('Statistik nach Gemeinden'))
if not txt:
    print("iframe content doesn't look correct", file=sys.stderr)
    sys.exit(1)

rows = fetchhelper.text_table(html)

# The structure of the document is currently a mess. Let's wait if it improves in the future.
for row in rows:
    if row[0] == '':
        del row[0]

headers = []
while rows[0][0] != 'Altomünster':
    headers.append(rows[0])
    del rows[0]

footers = []
while rows[-1][0] != 'Weichs':
    footers.insert(0, rows[-1])
    del rows[-1]

#print(headers)
#assert(any('Infizierte' in (ths + ['', ''])[1] for ths in headers))
#assert(any('geheilt' in (ths + ['', ''])[2] for ths in headers))

with open(parse.parsedfile, 'w') as outf:
    cout = csv.writer(outf)
    cout.writerow(['Kommune', 'Timestamp', 'Confirmed', 'Recovered'])

    for tds in rows:
        tds = [td for td in tds if td]
        cout.writerow((tds[0], datatime.isoformat(), int(tds[1]), int(tds[2])))

parse.deploy_timestamp()

fetchhelper.git_commit([parse], args)
