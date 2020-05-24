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

url = 'https://www.landratsamt-dachau.de/gesundheit-veterinaerwesen-sicherheitsrecht/gesundheit/coronavirus/statistik/'

datatz = dateutil.tz.gettz('Europe/Berlin')

update = fetchhelper.Updater(url)
update.check_fetch(rawfile=args.rawfile[0])

# accidentally duplicated <tr> and other hrml errors
html = BeautifulSoup(update.rawdata, 'html.parser')

parse = fetchhelper.ParseData(update, 'data')

txt = str(html.find(text=re.compile('Landkreis-Statistik ')))
mo = re.search(r'Landkreis-Statistik(?: nach Gemeinden)? für den (\d\d.\d\d.\d\d\d\d)', txt)
datatime = parse.parsedtime = update.contenttime = datetime.datetime.strptime(mo.group(1) + ' 21:30', '%d.%m.%Y %H:%M').replace(tzinfo=datatz)

img = html.find('img', src=re.compile(r'/grafik-uebersicht-nach-gemeinden\.png'))
iurl = urllib.parse.urljoin(url, img['src'])

update_pic = fetchhelper.Updater(iurl, ext='png')
update_pic.check_fetch(rawfile=args.rawfile[1], binary=True)

if not os.path.exists('collected'):
    os.mkdir('collected')
shutil.copy(update_pic.rawfile, 'collected/gemeinden_%s.png' % datatime.isoformat(timespec='minutes'))
sys.exit(0)


p = subprocess.run(['tesseract', '--psm', '4', '-l', 'deu', update_pic.rawfile, '-'], capture_output=True, check=True)
print(p.stdout)
update_pic.rawfile

for node in html.find_all(text=re.compile('Sars-CoV-2 Infizierte')):
    table = node.find_parent('table')
    if table is not None:
        break
rows = fetchhelper.text_table(table)

ths = rows[0]
assert('Infizierte' in ths[1])
assert('Geheilt' in ths[2] or 'geheilt' in ths[2])

with open(parse.parsedfile, 'w') as outf:
    cout = csv.writer(outf)
    cout.writerow(['Kommune', 'Timestamp', 'Confirmed', 'Recovered'])

    assert('Gesamt' in rows[-1])
    for tds in rows[1:-1]:
        cout.writerow((tds[0], datatime.isoformat(), int(tds[1]), int(tds[2])))

parse.deploy_timestamp()

fetchhelper.git_commit([parse], args)
