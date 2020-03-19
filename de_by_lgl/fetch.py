#!/usr/bin/env python3

import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--rawfile')
ap.add_argument('--only-changed', action="store_true")
ap.add_argument('--git-commit', action='store_true')
ap.add_argument('--git-push', action='store_true')
args = ap.parse_args()

import subprocess, datetime, re, csv, os, glob, shutil
from bs4 import BeautifulSoup
from dataclasses import dataclass
import dateutil.tz

@dataclass
class DiffState:
    first : bool
    changed : bool

def diff_previous(filename, globpattern=None):
    # try to find previous file name
    if globpattern is None:
        globpattern = os.path.join(os.path.dirname(filename), '*' + os.path.splitext(filename)[1])
    names = sorted(glob.glob(globpattern))
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

class Updater(object):
    def __init__(self, fetchurl):
        self.fetchurl = fetchurl
        self.rawfile = self.rawdiff = self.rawname = self.rawtime = self.rawdata = None
        self.contenttime = None

    def check_fetch(self, rawfile=None):
        if rawfile is None:
            self.rawfile = 'raw/%s.html' % datetime.datetime.now().isoformat()
            print('fetching raw %s' % self.rawfile)
            subprocess.run(['curl', '-sS', '-o', self.rawfile, self.fetchurl])
        else:
            self.rawfile = rawfile

        self.rawdiff = diff_previous(self.rawfile, 'raw/*.html')
        self.rawname = os.path.splitext(os.path.basename(self.rawfile))[0]
        try:
            self.rawtime = datetime.datetime.fromisoformat(self.rawname)
        except:
            self.rawtime = None

        with open(self.rawfile) as f:
            self.rawdata = f.read()

    def raw_changed(self):
        return self.rawdiff.changed

class ParseData(object):
    def __init__(self, update, label):
        self.update = update
        self.label = label
        self.parsedfile = 'parsed/%s_%s.csv' % (update.rawname, label)
        self.parsedtime = update.contenttime
        self.parseddiff = None
        self.deployfile = None

    def diff(self):
        self.parseddiff = diff_previous(self.parsedfile, 'parsed/*_%s.csv' % self.label)
        return self.parseddiff

    def deploy(self):
        self.deployfile = 'days/%s_%s.csv' % (self.label, self.parsedtime.date().isoformat())
        shutil.copy(self.parsedfile, self.deployfile)



update = Updater('https://www.lgl.bayern.de/gesundheit/infektionsschutz/infektionskrankheiten_a_z/coronavirus/karte_coronavirus/index.htm')
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
        .replace(tzinfo=dateutil.tz.gettz('Europe/Berlin'))
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

    parse.deploy()
    print("written %s" % parse.deployfile)

rparse = ParseData(update, 'regierungsbezirk')
parse_table(rparse, html,
        (lambda tab: tab.select_one('th').string == 'Regierungsbezirk'))
lparse = ParseData(update, 'landkreis')
parse_table(lparse, html,
        (lambda tab: tab.select_one('th').string in ['Landkreis', 'Land-/Stadtkreis']))

if args.git_commit:
    addfiles = []
    if rparse.deployfile is not None and rparse.parseddiff.changed:
        addfiles.append(rparse.deployfile)
    if lparse.deployfile is not None and lparse.parseddiff.changed:
        addfiles.append(lparse.deployfile)
    if addfiles:
        subprocess.run(['git', 'add', *addfiles], check=True)
        subprocess.run(['git', 'commit', '-m', 'Update data', *addfiles], check=True)
        if args.git_push:
            subprocess.run(['git', 'push'], check=True)
