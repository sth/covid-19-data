#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

#fetchhelper.check_oldfetch(args)

import csvtools
import re, csv, os, sys, dataclasses
import datetime, glob
from bs4 import BeautifulSoup
import dateutil.tz

def datedata_exists(d):
    match = d.isoformat()
    if glob.glob('data/*%s*.csv' % match):
        return True
    else:
        return False

if args.optional:
    # Check if we think we need to update
    # We expect data for the previous day
    target = (datetime.datetime.now() - datetime.timedelta(days=1)).date()
    if datedata_exists(target):
        # Looks good.
        print("Data for %s already saved." % target.isoformat())
        sys.exit(0)

datatz = dateutil.tz.gettz('Europe/Berlin')

kreise = {
    '5334': "Aachen & Städteregion Aachen",
    '5711': "Bielefeld",
    '5911': "Bochum",
    '5314': "Bonn",
    '5554': "Borken (Kreis)",
    '5512': "Bottrop",
    '5558': "Coesfeld (Kreis)",
    '5913': "Dortmund",
    '5112': "Duisburg",
    '5358': "Düren (Kreis)",
    '5111': "Düsseldorf",
    '5954': "Ennepe-Ruhr-Kreis",
    '5113': "Essen",
    '5366': "Euskirchen (Kreis)",
    '5513': "Gelsenkirchen",
    '5754': "Gütersloh (Kreis)",
    '5914': "Hagen",
    '5915': "Hamm",
    '5370': "Heinsberg (Kreis)",
    '5758': "Herford (Kreis)",
    '5916': "Herne",
    '5958': "Hochsauerlandkreis",
    '5762': "Höxter (Kreis)",
    '5154': "Kleve (Kreis)",
    '5315': "Köln",
    '5114': "Krefeld",
    '5316': "Leverkusen",
    '5766': "Lippe (Kreis)",
    '5962': "Märkischer Kreis",
    '5158': "Mettmann (Kreis)",
    '5770': "Minden-Lübbecke (Kreis)",
    '5116': "Mönchengladbach",
    '5117': "Mülheim / Ruhr",
    '5515': "Münster",
    '5374': "Oberbergischer Kreis",
    '5119': "Oberhausen",
    '5966': "Olpe (Kreis)",
    '5774': "Paderborn (Kreis)",
    '5562': "Recklinghausen (Kreis)",
    '5120': "Remscheid",
    '5362': "Rhein-Erft-Kreis",
    '5162': "Rhein-Kreis Neuss",
    '5382': "Rhein-Sieg-Kreis",
    '5378': "Rheinisch-Bergischer Kreis",
    '5970': "Siegen-Wittgenstein (Kreis)",
    '5974': "Soest (Kreis)",
    '5122': "Solingen",
    '5566': "Steinfurt (Kreis)",
    '5978': "Unna (Kreis)",
    '5166': "Viersen (Kreis)",
    '5570': "Warendorf (Kreis)",
    '5170': "Wesel (Kreis)",
    '5124': "Wuppertal",
}

coldefs = csvtools.CSVColumns(
        kreis=['kreis'],
        date=['datumstd'],
        confirmed=['anzahlMKumuliert'],
        deaths=['verstorbenKumuliert'],
        recovered=['genesenKumuliert'],
    )
coldefs.set_type('date', datetime.date.fromisoformat)
coldefs.set_type('confirmed', int)
coldefs.set_type('deaths', int)
coldefs.set_type('recovered', int)

targetdate = None

@dataclasses.dataclass
class Cases:
    kreis: str
    confirmed: int = 0
    deaths: int = 0
    recovered: int = 0
    date: None = None

newest = []
for kreisid, name in sorted(kreise.items()):
    update = fetchhelper.Updater(f'https://www.lzg.nrw.de/covid19/daten/covid19_{kreisid}.csv', ext=f'{kreisid}.csv')
    k_rawfile = (None if args.rawfile is None else glob.glob(f'{args.rawfile}.{kreisid}.csv')[0])
    update.check_fetch(rawfile=k_rawfile)
    with open(update.rawfile, 'r', encoding='utf-8-sig') as rf:
        cf = csv.reader(rf)
        header = next(cf)
        cols = coldefs.build(header)
        # newest line is last, so iterate through whole file
        # The data contains several "kummuliert" columns, but those sometimes seem to be rounded
        # Lets hope thats no longer the case
        cases = Cases(kreisid)
        for line in cf:
            fields = cols.get(line)
            cases.confirmed = fields.confirmed
            cases.deaths = fields.deaths
            cases.recovered = fields.recovered
            cases.date = fields.date
        if args.optional and fields.kreis == '5111':
            # Check if this is old already known data
            if datedata_exists(cases.date):
                # Already exists.
                # We abort immediately instead of downloading all other data files
                print("Found old data for %s." % cases.date.isoformat())
                sys.exit(0)
        newest.append(cases)

# All data should be for the same date
targetdate = newest[0].date
assert(all(n.date == targetdate for n in newest))
datats = datetime.datetime.combine(targetdate, datetime.time(23, 59), tzinfo=datatz)

# TODO: Having to pass an `update` here is not convenient. Improve that interface.
# We use the `update` leaked from the above loop for now :(
parse = fetchhelper.ParseData(update, 'data')
parse.parsedtime = datats

with open(parse.parsedfile, 'w') as outf:
    cout = csv.writer(outf)
    cout.writerow(['Area', 'AreaID', 'Date', 'EConfirmed', 'EDeaths', 'Recovered'])
    for fields in sorted(newest, key=(lambda n: int(n.kreis))):
        cout.writerow([kreise[fields.kreis], fields.kreis, datats.isoformat(), fields.confirmed, fields.deaths, fields.recovered])

parse.deploy_timestamp()

fetchhelper.git_commit([parse], args)
