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
    return int(s.replace('.', '').rstrip('+').rstrip('*'))

datatz = dateutil.tz.gettz('Europe/Vienna')

update = fetchhelper.Updater('https://www.sozialministerium.at/Informationen-zum-Coronavirus/Neuartiges-Coronavirus-(2019-nCov).html')
update.check_fetch(rawfile=args.rawfile)

html = BeautifulSoup(update.rawdata, 'html.parser')

class NotFound(Exception):
    pass

def parse_counts(parse, base, lead):
    infotext = base.find("div", class_="infobox").find(string=re.compile(lead))
    if infotext is None:
        infotext = base.find("main", id="content").find(string=re.compile(lead))
    txtp = infotext.find_parent('p')
    if txtp is None:
        raise NotFound()
    txt = txtp.get_text()
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

    parse.deploy_timestamp()

def parse_v1(parses, html):
    parse_c = fetchhelper.ParseData(update, 'confirmed')
    parse_counts(parse_c, html, "Best.*tigte F.*lle")
    parses.append(parse_c)

    # Seems to be removed for good
    #parse_r = fetchhelper.ParseData(update, 'recovered')
    #try:
    #    parse_counts(parse_r, infobox, "Genesene Personen")
    #    parses.append(parse_r)
    #except AttributeError as err:
    #    # It seems to be removed, we ignore it
    #    print(err)

    parse_d = fetchhelper.ParseData(update, 'deceased')
    parse_counts(parse_d, html, "Todesf.*lle")
    parses.append(parse_d)

def parse_v2(parses, html):
    table = fetchhelper.text_table(html.find('table'))
    ths = table[0]
    assert('Bundesland' in ths[0])
    assert('gesamt' in ths[-1])
    trs = table[1:]
    assert('tigte' in trs[0][0])
    assert('Todesf' in trs[1][0])
    assert('Genesen' in trs[2][0])
    assert('Hospital' in trs[3][0])
    assert('Intensiv' in trs[4][0])
    assert('Testungen' in trs[5][0])
    parse = [
            fetchhelper.ParseData(update, 'confirmed'),
            fetchhelper.ParseData(update, 'deaths'),
            fetchhelper.ParseData(update, 'recovered'),
            fetchhelper.ParseData(update, 'hospital'),
            fetchhelper.ParseData(update, 'intensivecare'),
            fetchhelper.ParseData(update, 'tests'),
        ]
    labels = ['confirmed', 'deceased', 'recovered', 'hospital', 'intensivecare', 'tests']

    areas = {
            'Bgld.': 'Burgenland',
            'Kt.': 'Kärnten',
            'Ktn.': 'Kärnten',
            'NÖ': 'Niederösterreich',
            'OÖ': 'Oberösterreich',
            'Sbg.': 'Salzburg',
            'Stmk.': 'Steiermark',
            'T': 'Tirol',
            'Vbg.': 'Vorarlberg',
            'W': 'Wien'
        }

    for i, tds in enumerate(trs):
        assert(len(ths) == len(tds))
        mo = re.search(r'Stand (\d\d.\d\d.\d\d\d\d), *(\d\d:\d\d) ?Uhr', tds[0])
        if mo is None:
            print("cannot parse date")
            sys.exit(1)
        parse = fetchhelper.ParseData(update, labels[i])
        datadate = parse.parsedtime = datetime.strptime(mo.group(1) + ' ' + mo.group(2), '%d.%m.%Y %H:%M').replace(tzinfo=datatz)
        with open(parse.parsedfile, 'w') as f:
            cw = csv.writer(f)
            cw.writerow(['Area', 'Date', 'Value'])
            for col in range(1, len(tds)-1):
                area = areas[ths[col]]
                count = cleannum(tds[col])
                cw.writerow([area, datadate.isoformat(), count])
        parse.deploy_timestamp()
        parses.append(parse)

def parse_all(parses, html):
    try:
        parse_v1(parses, html)
        return
    except NotFound:
        pass

    parse_v2(parses, html)

parses = []
parse_all(parses, html)

fetchhelper.git_commit(parses, args)
