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
    return int(s.replace(' ', ''))

datatz = dateutil.tz.gettz('Europe/Paris')

update = fetchhelper.Updater('https://www.santepubliquefrance.fr/maladies-et-traumatismes/maladies-et-infections-respiratoires/infection-a-coronavirus/articles/infection-au-nouveau-coronavirus-sars-cov-2-covid-19-france-et-monde')
update.check_fetch(rawfile=args.rawfile)
if args.only_changed:
    if not update.raw_changed():
        print("downloaded raw data unchanged")
        exit(0)

html = BeautifulSoup(update.rawdata, 'html.parser')

tab = html.find(string=re.compile('R.*gion de notification')).find_parent('table')

datestr = tab.find_previous('h4').get_text()
mo = re.search('(\d\d/\d\d/\d\d\d\d) à (\d\d)h', datestr)

parse = fetchhelper.ParseData(update, 'data')
parse.parsedtime = datetime.strptime(mo.group(1) + ' ' + mo.group(2), '%d/%m/%Y %H').replace(tzinfo=datatz)

with open(parse.parsedfile, 'w') as outf:
    cw = csv.writer(outf)
    cw.writerow(['Area', 'Region', 'Date', 'Confirmed'])

    group = 'Métropole'
    for tr in tab.find('tbody').find_all('tr'):
        tds = tr.find_all('td')
        area = tds[0].get_text()
        counttxt = tds[1].get_text()
        if '**' in counttxt:
            continue
        count = cleannum(tds[1].get_text())
        if area == 'Total Métropole':
            group = 'Outre Mer'
            continue
        if area == 'Total Outre Mer':
            area = '???'
            continue
        cw.writerow([area, group, parse.parsedtime, count])

parse.diff()
if args.only_changed:
    if not parse.parseddiff.changed:
        print("parsed content \"%s\" unchanged" % parse.label)
        #return

parse.deploy_day()

fetchhelper.git_commit([parse], args)
