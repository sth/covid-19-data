#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

fetchhelper.check_oldfetch(args)

if args.rawfile is not None:
    args.rawfile = args.rawfile.split(',')
else:
    args.rawfile = (None, None)

import datetime, re, csv, os
import json
import dateutil.tz

datatz = dateutil.tz.gettz('Europe/Berlin')

# Bundesländer
url_bl = 'https://services7.arcgis.com/mOBPykOjAyBO2ZKk/ArcGIS/rest/services/Coronaf%c3%a4lle_in_den_Bundesl%c3%a4ndern/FeatureServer/0/query?where=1%3D1&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&resultType=none&distance=0.0&units=esriSRUnit_Meter&returnGeodetic=false&outFields=LAN_ew_GEN%2CAktualisierung%2CFallzahl%2CDeath%2CLAN_ew_AGS&returnGeometry=false&returnCentroid=false&featureEncoding=esriDefault&multipatchOption=xyFootprint&maxAllowableOffset=&geometryPrecision=&outSR=&datumTransformation=&applyVCSProjection=false&returnIdsOnly=false&returnUniqueIdsOnly=false&returnCountOnly=false&returnExtentOnly=false&returnQueryGeometry=false&returnDistinctValues=false&cacheHint=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&having=&resultOffset=&resultRecordCount=&returnZ=false&returnM=false&returnExceededLimitFeatures=true&quantizationParameters=&sqlFormat=none&f=pjson&token='

updatebl = fetchhelper.Updater(url_bl, ext='bl.json')
updatebl.check_fetch(rawfile=args.rawfile[0])

jdat = json.loads(updatebl.rawdata)

parsebl = fetchhelper.ParseData(updatebl, 'data')
parsebl.parsedtime = None
with open(parsebl.parsedfile, 'w') as outf:
    cout = csv.writer(outf)
    cout.writerow(['Bundesland', 'AGS', 'Timestamp', 'EConfirmed', 'EDeaths'])
    for jfeat in sorted(jdat['features'], key=(lambda f: f['attributes']['LAN_ew_GEN'])):
        ts = datetime.datetime.fromtimestamp(jfeat['attributes']['Aktualisierung']/1000, tz=datatz)
        if parsebl.parsedtime is None or ts > parsebl.parsedtime:
            parsebl.parsedtime = ts
        cout.writerow([
            jfeat['attributes']['LAN_ew_GEN'],
            jfeat['attributes']['LAN_ew_AGS'],
            ts.isoformat(),
            jfeat['attributes']['Fallzahl'],
            jfeat['attributes']['Death'],
        ])

parsebl.deploy_timestamp()

# Landkreise

label_areas = set([
    'Ansbach', 'Aschaffenburg', 'Augsburg', 'Bamberg', 'Bayreuth', 'Coburg',
    'Fürth', 'Heilbronn', 'Hof', 'Kaiserslautern', 'Karlsruhe', 'Kassel',
    'Landshut', 'Leipzig', 'München', 'Osnabrück', 'Passau', 'Regensburg',
    'Rosenheim', 'Rostock', 'Schweinfurt', 'Würzburg',

    'Baden-Baden', 'Freiburg im Breisgau', 'Heidelberg', 'Mannheim',
    'Pforzheim', 'Ulm',

    'Borken', 'Kleve', 'Viersen', 'Wesel', 'Düren', 'Euskirchen', 'Heinsberg',
    'Coesfeld', 'Recklinghausen', 'Steinfurt', 'Warendorf',
    'Gütersloh', 'Herford', 'Höxter', 'Lippe', 'Minden-Lübbecke', 'Paderborn',
    'Olpe', 'Siegen-Wittgenstein', 'Soest', 'Unna',
])

bez_label = {
    'Stadtkreis': 'Stadtkreis',
    'Landkreis': 'Landkreis',
    'Kreis': 'Kreis',
    'Kreisfreie Stadt': 'Stadt',
}


url_lk = 'https://services7.arcgis.com/mOBPykOjAyBO2ZKk/ArcGIS/rest/services/RKI_Landkreisdaten/FeatureServer/0/query?where=1%3D1&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&resultType=none&distance=0.0&units=esriSRUnit_Meter&returnGeodetic=false&outFields=Bl%2Ccounty%2CGEN%2Clast_update%2Ccases%2Cdeaths%2Crecovered%2CAGS_0%2CBEZ&returnGeometry=false&returnCentroid=false&featureEncoding=esriDefault&multipatchOption=xyFootprint&maxAllowableOffset=&geometryPrecision=&outSR=&datumTransformation=&applyVCSProjection=false&returnIdsOnly=false&returnUniqueIdsOnly=false&returnCountOnly=false&returnExtentOnly=false&returnQueryGeometry=false&returnDistinctValues=false&cacheHint=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&having=&resultOffset=&resultRecordCount=&returnZ=false&returnM=false&returnExceededLimitFeatures=true&quantizationParameters=&sqlFormat=none&f=pjson&token='

updatelk = fetchhelper.Updater(url_lk, ext='lk.json')
updatelk.check_fetch(rawfile=args.rawfile[1])

jdat = json.loads(updatelk.rawdata)

parselk = fetchhelper.ParseData(updatelk, 'lk')
parselk.parsedtime = None
with open(parselk.parsedfile, 'w') as outf:
    cout = csv.writer(outf)
    cout.writerow(['Area', 'Bundesland', 'AGS', 'Timestamp', 'Confirmed', 'Deaths'])
    for jfeat in sorted(jdat['features'], key=(lambda f: (f['attributes']['BL'], f['attributes']['GEN']))):
        ts = datetime.datetime.strptime(jfeat['attributes']['last_update'], "%d.%m.%Y, %H:%M Uhr").astimezone(datatz)
        if parselk.parsedtime is None or ts > parselk.parsedtime:
            parselk.parsedtime = ts
        area = jfeat['attributes']['GEN']
        if area in label_areas:
            area += ' (%s)' % bez_label[jfeat['attributes']['BEZ']]
        cout.writerow([
            area,
            jfeat['attributes']['BL'],
            jfeat['attributes']['AGS_0'],
            ts.isoformat(),
            jfeat['attributes']['cases'],
            jfeat['attributes']['deaths'],
        ])

parselk.deploy_timestamp()

fetchhelper.git_commit([parsebl], args)
