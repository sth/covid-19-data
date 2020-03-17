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



update = Updater('https://www.rki.de/DE/Content/InfAZ/N/Neuartiges_Coronavirus/Fallzahlen.html')
update.check_fetch(rawfile=args.rawfile)
if args.only_changed:
    if not update.raw_changed():
        print("downloaded raw data unchanged")
        exit(0)

html = BeautifulSoup(update.rawdata, 'html.parser')

header = html.find(text="Fallzahlen in Deutschland")
par = header.parent.next_sibling.next_sibling
#print(header)
#print(header.parent.next_sibling.next_sibling)

mo = re.search('Stand: (\S*, \S*) Uhr', par.get_text())
if mo is None:
    print("Couldn't find content time")
    exit(1)
update.contenttime = datetime.datetime.strptime(mo.group(1), '%d.%m.%Y, %H:%M')

def clean_num(numstr):
    return int(numstr.replace('.', '').strip())

def parse_td(content):
    mo = re.search(r'(.*)\((.*)\)\s*', content)
    if mo is None:
        return (clean_num(content), 0)
    else:
        return (clean_num(mo.group(1)), clean_num(mo.group(2)))

parse = ParseData(update, 'data')
for tab in header.parent.parent.select('table'):
    if tab.select('thead th')[0].text != 'Bundesland':
        continue
    with open(parse.parsedfile, 'w') as outf:
        cout = csv.writer(outf)
        cout.writerow(['Area', 'Date', 'EConfirmed', 'EDeaths'])
        for tr in tab.select('table tbody tr')[:-1]:
            tds = tr.select('td')
            assert(len(tds) == 6)
            econfirmed = clean_num(tds[1].get_text())
            edeaths = clean_num(tds[4].get_text())
            cout.writerow([tds[0].string, parse.parsedtime.isoformat(),
                econfirmed, edeaths])
    parse.diff()
    break
else:
    print("couldn't find table %s" % parse.label)
    exit(1)

if args.only_changed:
    if not parse.parseddiff.changed:
        print("parsed content \"%s\" unchanged" % parse.label)
        exit(0)

# It changed. If the current day is later than the contenttime we assume the
# content time is a mistake and we adjust it to the current day.
# (This problem has happend before)
if parse.update.rawtime.date() > parse.parsedtime.date():
    if parse.parseddiff.changed and not parse.parseddiff.first:
        print("Adjust date", parse.parsedtime, "->", parse.update.rawtime)
        parse.parsedtime = parse.update.rawtime

parse.deploy()

if args.git_commit:
    if parse.deployfile is not None and parse.parseddiff.changed:
        subprocess.run(['git', 'add', parse.deployfile], check=True)
        subprocess.run(['git', 'commit', '-m', 'Update data', parse.deployfile], check=True)
        if args.git_push:
            subprocess.run(['git', 'push'], check=True)
