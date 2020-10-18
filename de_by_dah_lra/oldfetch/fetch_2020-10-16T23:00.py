#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

fetchhelper.check_oldfetch(args)

import subprocess, datetime, re, csv, os, sys, shutil
import urllib.parse
from bs4 import BeautifulSoup
import dateutil.tz

url = 'https://www.landratsamt-dachau.de/bilder/zahlen.jpg'

datatz = dateutil.tz.gettz('Europe/Berlin')

#txt = str(html.find(text=re.compile('Landkreis-Statistik ')))
#mo = re.search(r'Landkreis-Statistik(?: nach Gemeinden)? für den (\d\d.\d\d.\d\d\d\d)', txt)
#datatime = parse.parsedtime = update.contenttime = datetime.datetime.strptime(mo.group(1) + ' 21:30', '%d.%m.%Y %H:%M').replace(tzinfo=datatz)

update = fetchhelper.Updater(url, ext='png')
update.check_fetch(rawfile=args.rawfile, binary=True, remotetime=True)
datatime = datetime.datetime.fromtimestamp(os.stat(update.rawfile).st_mtime)

if not os.path.exists('collected'):
    os.mkdir('collected')
shutil.copy(update.rawfile, 'collected/gemeinden_%s.png' % datatime.isoformat(timespec='minutes'))
