import os, re, sys, datetime, subprocess, glob, shutil
from dataclasses import dataclass

def add_arguments(ap):
    ap.add_argument('--rawfile')
    ap.add_argument('--optional', action='store_true')
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

    def check_fetch(self, rawfile=None, *, binary=False, remotetime=False, compressed=False):
        if rawfile is None:
            checkdir('raw')
            self.rawfile = 'raw/%s.%s' % (datetime.datetime.now().isoformat(), self.ext)
            print('fetching raw %s' % self.rawfile)
            opts = []
            if remotetime:
                opts += ['-R']
            if compressed:
                opts += ['--compressed']
            subprocess.run(['curl', '-sS', '-L', '-o', self.rawfile] + opts + [self.fetchurl])
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
            # All parts of gits command line interface are a mess.
            # Git insists on writing updated refs to stderr, making them look like errors.
            cmd = subprocess.run(['git', 'push', ], capture_output=True, check=False)
            sys.stdout.buffer.write(cmd.stdout)
            if cmd.returncode != 0:
                sys.stderr.buffer.write(cmd.stderr)
            else:
                sys.stdout.buffer.write(cmd.stderr)

def text_table(node):
    rows = node.find_all('tr')
    table = []
    for row in rows:
        tds = row.find_all(['th', 'td'])
        table.append([td.get_text().strip() for td in tds])
    return table

re_ts = re.compile(r'\d\d\d\d-\d\d-\d\dT\d\d:\d\d(?::\d\d\.\d*)?')
def check_oldfetch(args):
    if not args.rawfile:
        return
    if not os.path.exists('oldfetch'):
        return
    # Don't do this recursively
    if 'oldfetch' in sys.argv[0]:
        return

    mo = re_ts.search(args.rawfile)
    if mo is None:
        return
    rawts = mo.group()

    oldfetch = sorted(fn for fn in os.listdir('oldfetch') if fn.startswith('fetch_') and fn.endswith('.py'))
    for fold in oldfetch:
        mo = re_ts.search(fold)
        if mo is None:
            print("cannot determine date of old fetch script:", fold, file=sys.stderr)
            continue
        fts = mo.group()
        if fts > rawts:
            # Use this script
            fuse = os.path.join('oldfetch', fold)
            print("using old fetch script", fuse, flush=True)
            # Add helper fir to path
            helperpath = os.path.dirname(__file__)
            chenv = dict(os.environ)
            pp = chenv.get('PYTHONPATH', None)
            if pp is None:
                pp = helperpath
            else:
                pp += os.pathsep + helperpath
            chenv['PYTHONPATH'] = pp
            os.execve(fuse, sys.argv, chenv)
