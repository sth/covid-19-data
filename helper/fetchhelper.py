import os, re, datetime, subprocess, glob, shutil
from dataclasses import dataclass

def add_arguments(ap):
    ap.add_argument('--rawfile')
    ap.add_argument('--only-changed', action="store_true")
    ap.add_argument('--git-commit', action='store_true')
    ap.add_argument('--git-push', action='store_true')


def checkdir(path):
    if not os.path.exists(path):
        os.mkdir(path)

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
    def __init__(self, fetchurl, ext='html'):
        self.fetchurl = fetchurl
        self.ext = ext
        self.rawfile = self.rawdiff = self.rawname = self.rawtime = self.rawdata = None
        self.contenttime = None

    def check_fetch(self, rawfile=None, binary=False):
        if rawfile is None:
            checkdir('raw')
            self.rawfile = 'raw/%s.%s' % (datetime.datetime.now().isoformat(), self.ext)
            print('fetching raw %s' % self.rawfile)
            subprocess.run(['curl', '-sS', '-o', self.rawfile, self.fetchurl])
        else:
            self.rawfile = rawfile

        self.rawdiff = diff_previous(self.rawfile, 'raw/*.%s' % self.ext)
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

    def raw_changed(self):
        return self.rawdiff.changed

class ParseData(object):
    def __init__(self, update, label, variant=''):
        self.update = update
        self.label = label
        self.variant = variant
        checkdir('parsed')
        self.parsedfile = 'parsed/%s_%s%s.csv' % (update.rawname, self.label, self.variant)
        self.parsedtime = update.contenttime
        self.parseddiff = None
        self.deployfile = None

    def diff(self):
        self.parseddiff = diff_previous(self.parsedfile, 'parsed/*_%s%s.csv' % (self.label, self.variant))
        return self.parseddiff

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

