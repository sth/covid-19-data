#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

fetchhelper.check_oldfetch(args)

import csvtools
import re, csv, os, sys
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
    '5334': "Aachen & Aachen (Städteregion)",
    '5711': "Bielefeld",
    '5911': "Bochum",
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
    '5158': "Mettmann (Kreis (Kreis))",
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
        confirmed=['anzahlEM'],
        deaths=['verstorben'],
        recovered=['genesen'],
    )
coldefs.set_type('date', datetime.date.fromisoformat)
coldefs.set_type('confirmed', int)
coldefs.set_type('deaths', int)
coldefs.set_type('recovered', int)

targetdate = None

newest = []
for kreisid, name in sorted(kreise.items()):
    update = fetchhelper.Updater(f'https://www.lzg.nrw.de/covid19/daten/covid19_{kreisid}.csv', ext=f'{kreisid}.csv')
    update.check_fetch(rawfile=(None if args.rawfile is None else args.rawfile + f'.k{kreisid}.csv'))
    with open(update.rawfile, 'r', encoding='utf-8-sig') as rf:
        cf = csv.reader(rf)
        header = next(cf)
        cols = coldefs.build(header)
        # newest line is last, so iterate through whole file
        for line in cf:
            continue
        fields = cols.get(line) # using `line` here is basically a hack
        if args.optional and fields.kreis == '5111':
            # Check if this is old already known data
            if datedata_exists(fields.date):
                # Already exists.
                # We abort immediately instead of downloading all other data files
                print("Found old data for %s." % fields.date.isoformat())
                sys.exit(0)
        newest.append(fields)

# All data should be for the same date
targetdate = newest[0].date
assert(all(n.date == targetdate for n in newest))

# TODO: Having to pass an `update` here is not convenient. Improve that interface.
# We use the `update` leaked from the above loop for now :(
parse = fetchhelper.ParseData(update, 'data')
parse.parsedtime = datetime.datetime.combine(targetdate, datetime.time(23, 59), tzinfo=datatz)

with open(parse.parsedfile, 'w') as outf:
    cout = csv.writer(outf)
    cout.writerow(['Area', 'AreaID', 'Date', 'EConfirmed', 'EDeaths', 'Recovered'])
    for fields in sorted(newest, key=(lambda n: int(n.kreis))):
        ts = datetime.datetime.combine(fields.date, datetime.time(23, 59), tzinfo=datatz)
        cout.writerow([kreise[fields.kreis], fields.kreis, ts.isoformat(), fields.confirmed, fields.deaths, fields.recovered])

parse.deploy_timestamp()

fetchhelper.git_commit([parse], args)
