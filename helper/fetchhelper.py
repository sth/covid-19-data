import os, re, datetime, subprocess, glob, shutil
from dataclasses import dataclass

def add_arguments(ap):
    ap.add_argument('--rawfile')
    ap.add_argument('--git-commit', action='store_true')
    ap.add_argument('--git-push', action='store_true')


def checkdir(path):
    if not os.path.exists(path):
        os.mkdir(path)

class Updater(object):
    def __init__(self, fetchurl, ext='html'):
        self.fetchurl = fetchurl
        self.ext = ext
        self.rawfile = self.rawname = self.rawtime = self.rawdata = None
        self.contenttime = None

    def check_fetch(self, rawfile=None, binary=False):
        if rawfile is None:
            checkdir('raw')
            self.rawfile = 'raw/%s.%s' % (datetime.datetime.now().isoformat(), self.ext)
            print('fetching raw %s' % self.rawfile)
            subprocess.run(['curl', '-sS', '-o', self.rawfile, self.fetchurl])
        else:
            self.rawfile = rawfile

        self.rawname = os.path.splitext(os.path.basename(self.rawfile))[0]
        try:
            self.rawtime = datetime.datetime.fromisoformat(self.rawname)
        except:
            self.rawtime = None

        mode = 'r'
        if binary:
            mode += 'b'
        with open(self.rawfile, mode) as f:
            self.rawdata = f.read()

class ParseData(object):
    def __init__(self, update, label, variant=''):
        self.update = update
        self.label = label
        self.variant = variant
        checkdir('parsed')
        self.parsedfile = 'parsed/%s_%s%s.csv' % (update.rawname, self.label, self.variant)
        self.parsedtime = update.contenttime
        self.deployfile = None

    def deploy_day(self):
        checkdir('days')
        self.deployfile = 'days/%s_%s.csv' % (self.label, self.parsedtime.date().isoformat())
        shutil.copy(self.parsedfile, self.deployfile)

    def deploy_timestamp(self):
        checkdir('data')
        parsedutc = self.parsedtime.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        self.deployfile = 'data/%s_%s.csv' % (self.label, parsedutc.isoformat(timespec='minutes'))
        shutil.copy(self.parsedfile, self.deployfile)

    def deploy_combined(self):
        checkdir('data')
        self.deployfile = 'data/%s.csv' % (self.label,)
        shutil.copy(self.parsedfile, self.deployfile)

def git_commit(parsedlist, args):
    if not args.git_commit:
        return
    addfiles = []
    for parse in parsedlist:
        if parse.deployfile is not None:
            addfiles.append(parse.deployfile)
    if addfiles:
        subprocess.run(['git', 'add', *addfiles], check=True)
        cmd = subprocess.run(['git', 'status', '--porcelain', *addfiles], capture_output=True, check=True)
        modified = []
        for line in cmd.stdout.split(b'\n'):
            if not line:
                continue
            if line[0] in b'MARC':
                modified = True
                break
        if not modified:
            print("data unchanged")
            return
        subprocess.run(['git', 'status', *addfiles], check=True)
        subprocess.run(['git', 'commit', '-m', 'Update data', *addfiles], check=True)
        if args.git_push:
            subprocess.run(['git', 'push'], check=True)

