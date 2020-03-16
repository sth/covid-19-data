#!/usr/bin/env python3

import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--rawfile')
ap.add_argument('--only-changed', action="store_true")
args = ap.parse_args()

import subprocess, datetime, re, csv, os, glob, shutil
from bs4 import BeautifulSoup
from dataclasses import dataclass

@dataclass
class DiffState:
    first : bool
    changed : bool

def diff_previous(filename):
    # try to find previous file name
    pat = os.path.join(os.path.dirname(filename), '*' + os.path.splitext(filename)[1])
    names = sorted(glob.glob(pat))
    idx = names.index(filename)
    if idx == -1:
        # Something went wrong but ignore this
        print("error checking for changed data")
        return True
    if idx == 0:
        # First file
        return DiffState(True, True)
    diff = subprocess.run(['diff', '-q', names[idx-1], filename], stdout=subprocess.DEVNULL)
    if diff.returncode == 2:
        raise Exception("Diff failed")
    return DiffState(False, diff.returncode == 1)


if args.rawfile is None:
    args.rawfile = 'raw/%s.html' % datetime.datetime.now().isoformat()
    print('fetching raw %s' % args.rawfile)
    subprocess.run(['curl', '-sS', '-o', args.rawfile,
            'https://www.lgl.bayern.de/gesundheit/infektionsschutz/infektionskrankheiten_a_z/coronavirus/karte_coronavirus/index.htm'
            ])

if args.only_changed:
    if not diff_previous(args.rawfile).changed:
        print("downloaded raw data unchanged")
        exit(0)


rawname = os.path.splitext(os.path.basename(args.rawfile))[0]
try:
    rawtime = datetime.datetime.fromisoformat(rawname)
except:
    rawtime = None

with open(args.rawfile) as f:
    raw = f.read()


html = BeautifulSoup(raw, 'html.parser')

contenttime = None
for p in html.select('.bildunterschrift'):
    text = p.get_text()
    mo = re.search('Stand: (\S* \S*)', text)
    if mo is None:
        continue
    contenttime = datetime.datetime.strptime(mo.group(1), '%d.%m.%Y %H:%M')
    break

if contenttime is None:
    print("Couldn't find content time")
    exit(1)

bezirk = stadt = None

def parse_table(html, contenttime, group, tabselect):
    parsedfn = 'parsed/%s_%s.csv' % (rawname, group)
    for tab in html.select('table'):
        if tabselect(tab):
            with open(parsedfn, 'w') as outf:
                cout = csv.writer(outf)
                cout.writerow(['Area', 'Date', 'Confirmed'])
                for tr in tab.select('tr')[1:-1]:
                    tds = tr.select('td')
                    assert(len(tds) == 2)
                    cout.writerow([tds[0].string, contenttime.isoformat(), tds[1].string])
            break
    else:
        print("couldn't find table %s" % group)
        exit(1)

    if args.only_changed:
        if not diff_previous(parsedfn).changed:
            print("parsed content \"%s\" unchanged" % group)
            return

    # It changed. If the current day is later than the contenttime we assume the
    # content time is a mistake and we adjust it to the current day.
    # (This problem has happend before)
    if rawtime.date() > contenttime.date():
        if not diff_previous(parsedfn).first:
            print("Adjust date", contenttime, "->", rawtime)
            contenttime = rawtime

    shutil.copy(parsedfn, 'days/%s_%s.csv' % (group, contenttime.date().isoformat()))

parse_table(html, contenttime, 'regierungsbezirk', (lambda tab: tab.select_one('th').string == 'Regierungsbezirk'))
parse_table(html, contenttime, 'landkreis', (lambda tab: tab.select_one('th').string in ['Landkreis', 'Land-/Stadtkreis']))
