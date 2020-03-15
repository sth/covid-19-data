#!/usr/bin/env python3

import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--rawfile')
args = ap.parse_args()

import subprocess, datetime, re, csv
from bs4 import BeautifulSoup

def parse_table(tab, stand, outf):
    cout = csv.writer(outf)
    for tr in tab.select('tr')[1:-1]:
        tds = tr.select('td')
        assert(len(tds) == 2)
        cout.writerow([tds[0].string, stand.isoformat(), tds[1].string])
        #outf.write('%s,%s,%s\n' % (tds[0].string, tds[1].string, stand.isoformat()))

if args.rawfile is None:
    ts = datetime.datetime.utcnow()
    args.rawfile = 'raw/%s.html' % ts.isoformat()

    print('fetching to %s' % args.rawfile)
    subprocess.run(['curl', '-sS', '-o', args.rawfile,
            'https://www.lgl.bayern.de/gesundheit/infektionsschutz/infektionskrankheiten_a_z/coronavirus/karte_coronavirus/index.htm'
            ])

with open(args.rawfile) as f:
    raw = f.read()


html = BeautifulSoup(raw, 'html.parser')

stand = None
bezirk = stadt = None

for p in html.select('.bildunterschrift'):
    text = p.get_text()
    mo = re.search('Stand: (\S* \S*)', text)
    if mo is None:
        continue
    stand = datetime.datetime.strptime(mo.group(1), '%d.%m.%Y %H:%M')
    break

if stand is None:
    print("Couldn't find date")
    exit(1)

day = stand.strftime('%F')
with open('days/regierungsbezirk_%s.csv' % day, 'w') as outf:
    for tab in html.select('table'):
        if tab.select_one('th').string == 'Regierungsbezirk':
            parse_table(tab, stand, outf)
            break

with open('days/landkreis_%s.csv' % day, 'w') as outf:
    for tab in html.select('table'):
        if tab.select_one('th').string == 'Landkreis':
            parse_table(tab, stand, outf)
            break

_comment = '''
def compile_timeseries(areagroup):
    re_fn = re.compile('data_' + areagroup + r'_(\d\d\d\d-\d\d-\d\d)\.csv')

    datasets = {}

    lastdate = None
    for fn in sorted(os.listdir('.')):
        mo = re_fn.match(fn)
        if mo is None:
            continue

        thisdate = datetime.datetime.strptime(mo.group(1)).date()

        with open(fn) as f:
            cf = csv.reader(f)

            for area, timestamp, count in cf:
                if thisdate is None:
                    # First entry

        if lastdate is None:
            # This is the first line
            lastdate.strftime('%F')
        if lastdate is not None:
            # Check for missing days
            and lastdate + datetime.timedelta(days=1) < thisdate:
            lastdate = 

    with open('timeseries_' + areagroup + '.csv', 'w') as fts:
        cts = csv.writer(fts)
'''
