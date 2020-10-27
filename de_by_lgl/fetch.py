#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

fetchhelper.check_oldfetch(args)

import subprocess, datetime, re, csv, os, sys
from bs4 import BeautifulSoup
import dateutil.tz

# helpers 
re_strip_landkreis = re.compile(r'\ba\. ?|\bam |\bi\. ?|\bim |\bd\. ?|\bder')
rawlabel_regierungsbezirk = {
    "Aichach-Friedberg": "Schwaben",
    "Altötting": "Oberbayern",
    "Amberg Stadt": "Oberpfalz",
    "Amberg-Sulzbach": "Oberpfalz",
    "Ansbach Stadt": "Mittelfranken",
    "Ansbach": "Mittelfranken",
    "Aschaffenburg Stadt": "Unterfranken",
    "Aschaffenburg": "Unterfranken",
    "Augsburg Stadt": "Schwaben",
    "Augsburg": "Schwaben",
    "Bad Kissingen": "Unterfranken",
    "Bad Tölz-Wolfratshausen": "Oberbayern",
    "Bamberg Stadt": "Oberfranken",
    "Bamberg": "Oberfranken",
    "Bayreuth Stadt": "Oberfranken",
    "Bayreuth": "Oberfranken",
    "Berchtesgadener Land": "Oberbayern",
    "Cham": "Oberpfalz",
    "Coburg Stadt": "Oberfranken",
    "Coburg": "Oberfranken",
    "Dachau": "Oberbayern",
    "Deggendorf": "Niederbayern",
    "Dillingen an der Donau": "Schwaben",
    "Dingolfing-Landau": "Niederbayern",
    "Donau-Ries": "Schwaben",
    "Ebersberg": "Oberbayern",
    "Eichstätt": "Oberbayern",
    "Erding": "Oberbayern",
    "Erlangen Stadt": "Mittelfranken",
    "Erlangen-Höchstadt": "Mittelfranken",
    "Forchheim": "Oberfranken",
    "Freising": "Oberbayern",
    "Freyung-Grafenau": "Niederbayern",
    "Fürstenfeldbruck": "Oberbayern",
    "Fürth Stadt": "Mittelfranken",
    "Fürth": "Mittelfranken",
    "Garmisch-Partenkirchen": "Oberbayern",
    "Günzburg": "Schwaben",
    "Haßberge": "Unterfranken",
    "Hof Stadt": "Oberfranken",
    "Hof": "Oberfranken",
    "Ingolstadt Stadt": "Oberbayern",
    "Kaufbeuren Stadt": "Schwaben",
    "Kelheim": "Niederbayern",
    "Kempten Stadt": "Schwaben",
    "Kitzingen": "Unterfranken",
    "Kronach": "Oberfranken",
    "Kulmbach": "Oberfranken",
    "Landsberg am Lech": "Oberbayern",
    "Landshut Stadt": "Niederbayern",
    "Landshut": "Niederbayern",
    "Lichtenfels": "Oberfranken",
    "Lindau (Bodensee)": "Schwaben",
    "Main-Spessart": "Unterfranken",
    "Memmingen Stadt": "Schwaben",
    "Miesbach": "Oberbayern",
    "Miltenberg": "Unterfranken",
    "Mühldorf am Inn": "Oberbayern",
    "München Stadt": "Oberbayern",
    "München": "Oberbayern",
    "Neuburg-Schrobenhausen": "Oberbayern",
    "Neumarkt in der Oberpfalz": "Oberpfalz",
    "Neustadt an der Aisch-Bad Windsheim": "Mittelfranken",
    "Neustadt an der Waldnaab": "Oberpfalz",
    "Neu-Ulm": "Schwaben",
    "Nürnberg Stadt": "Mittelfranken",
    "Nürnberger Land": "Mittelfranken",
    "Oberallgäu": "Schwaben",
    "Ostallgäu": "Schwaben",
    "Passau Stadt": "Niederbayern",
    "Passau": "Niederbayern",
    "Pfaffenhofen an der Ilm": "Oberbayern",
    "Regen": "Niederbayern",
    "Regensburg Stadt": "Oberpfalz",
    "Regensburg": "Oberpfalz",
    "Rhön-Grabfeld": "Unterfranken",
    "Rosenheim Stadt": "Oberbayern",
    "Rosenheim": "Oberbayern",
    "Roth": "Mittelfranken",
    "Rottal-Inn": "Niederbayern",
    "Schwabach Stadt": "Mittelfranken",
    "Schwandorf": "Oberpfalz",
    "Schweinfurt Stadt": "Unterfranken",
    "Schweinfurt": "Unterfranken",
    "Starnberg": "Oberbayern",
    "Straubing Stadt": "Niederbayern",
    "Straubing-Bogen": "Niederbayern",
    "Tirschenreuth": "Oberpfalz",
    "Traunstein": "Oberbayern",
    "Unterallgäu": "Schwaben",
    "Weiden in der Oberpfalz Stadt": "Oberpfalz",
    "Weilheim-Schongau": "Oberbayern",
    "Weißenburg-Gunzenhausen": "Mittelfranken",
    "Wunsiedel im Fichtelgebirge": "Oberfranken",
    "Würzburg Stadt": "Unterfranken",
    "Würzburg": "Unterfranken",
}

rawlabel_landkreis = {
    "Bad Tölz": "Bad Tölz-Wolfratshausen",
    "Dillingen Donau": "Dillingen an der Donau",
    "Landsberg Lech": "Landsberg am Lech",
    "Mühldorf Inn": "Mühldorf am Inn",
    "Neumarkt Opf.": "Neumarkt in der Oberpfalz",
    "Neustadt Aisch-Bad Windsheim": "Neustadt an der Aisch-Bad Windsheim",
    "Neustadt Waldnaab": "Neustadt an der Waldnaab",
    "Pfaffenhofen Ilm": "Pfaffenhofen an der Ilm",
    "Weiden Stadt": "Weiden in der Oberpfalz Stadt",
    "Wunsiedel Fichtelgebirge": "Wunsiedel im Fichtelgebirge",
}

def clean_landkreis(rawlabel):
    stripped = re_strip_landkreis.sub('', rawlabel)
    if stripped in rawlabel_landkreis:
        return rawlabel_landkreis[stripped]
    else:
        return rawlabel

def get_regierungsbezirk(rawlabel):
    landkreis = clean_landkreis(rawlabel)
    return rawlabel_regierungsbezirk[landkreis]



datatz = dateutil.tz.gettz('Europe/Berlin')

update = fetchhelper.Updater('https://www.lgl.bayern.de/gesundheit/infektionsschutz/infektionskrankheiten_a_z/coronavirus/karte_coronavirus/index.htm')
update.check_fetch(rawfile=args.rawfile)

# accidentally duplicated <tr> and other hrml errors
#update.rawdata = re.sub(r'<tr>\s*<tr>', r'<tr>', update.rawdata)
update.rawdata = re.sub(r'(<th><span>[^<>]*</span>)</(td|div)>', r'\1</th>', update.rawdata)
html = BeautifulSoup(update.rawdata, 'html.parser')

datenode = html.find('script', text=re.compile(r'var publikationsDatum = '))
if datenode is None:
    print("Cannot find publish date", file=sys.stderr)
    sys.exit(1)
datemo = re.search(r'"(\d\d.\d\d.\d\d\d\d)"', datenode.get_text())
if datemo is None:
    print("Cannot find publish date", file=sys.stderr)
    sys.exit(2)
publishdate = datetime.datetime.strptime(datemo.group(1), '%d.%m.%Y').date()

def get_labeltime(text):
    mo = re.search(r'Stand:.*\);\s*, (\d\d:\d\d) Uhr', text, re.DOTALL)
    if mo is None:
        return None
    stime = datetime.datetime.strptime(mo.group(1), '%H:%M').time()
    return datetime.datetime.combine(publishdate, stime, tzinfo=datatz)

def tab_rows(tab):
    trs = tab.select('tr')
    assert('kreis' in trs[0].find('th').get_text() or 'bezirk' in trs[0].find('th').get_text())
    assert('Gesamt' in trs[-1].find('td').get_text())
    trs = trs[1:-1]

    rows = []
    for tr in trs:
        yield tr.select('td')
    return rows

def clean_num(s):
    if s == '-':
        s = '0'
    s = s.replace('.', '')
    return int(s)


def is_regierungsbezirk(tab):
    return tab.select_one('th').string in ['Regierungsbezirk']

def is_landkreis(tab):
    return tab.select_one('th').string in ['Landkreis', 'Land-/Stadtkreis', 'Landkreis/Stadt']

re_missing = re.compile(r' aus technischen Gründen heute nicht möglich| \*technische Probleme|: technische Probleme \*')
regbez_tainted = set()

def parse_table(parse, html, kind, *, optional=False):
    assert(kind in ('regierungsbezirk', 'landkreis'))
    parse_landkreis = (kind == 'landkreis')

    if parse_landkreis:
        tab = html.select_one('#tableLandkreise')
        if not is_landkreis(tab):
            print("unrecognized table")
            exit(1)
    else:
        tab = html.select_one('#tableRegBez')
        if not is_regierungsbezirk(tab):
            print("unrecognized table")
            exit(1)

    caption = tab.find('caption')
    datatime = parse.parsedtime = get_labeltime(caption.get_text())
    if datatime is None:
        print("couldn't determine datatime for %s" % parse.label, file=sys.stderr)
        exit(1)

    ths = tab.find_all('th')
    assert('Fälle' in ths[1].get_text())
    assert('Todesfälle' in ths[6].get_text())

    with open(parse.parsedfile, 'w') as outf:
        cout = csv.writer(outf)
        if parse_landkreis:
            header = ['Landkreis', 'Regierungsbezirk']
        else:
            header = ['Regierungsbezirk']
        header += ['Timestamp', 'Confirmed', 'Deaths']
        cout.writerow(header)

        txttab = fetchhelper.text_table(tab)
        txttab = txttab[1:-1]
        for tds in txttab:
            if parse_landkreis:
                lk = clean_landkreis(tds[0])
                if re_missing.search(lk):
                    # The sum for the Regierungsbezirk also seems to be wrong
                    rb = get_regierungsbezirk(re_missing.sub('', lk))
                    regbez_tainted.add(rb)
                    continue
                cols = [lk, get_regierungsbezirk(lk)]
            else:
                rb = tds[0]
                if rb in regbez_tainted:
                    # Skip because there is missing data
                    continue
                cols = [rb]
            cols.append(datatime.isoformat())
            cols += [clean_num(tds[1]), clean_num(tds[6])]
            cout.writerow(cols)

    # If the current day is later than the contenttime we assume the
    # content time is a mistake and we adjust it to the current day.
    # (This problem has happend before)
    #if parse.update.rawtime.date() > parse.parsedtime.date():
    #    if parse.parseddiff.changed and not parse.parseddiff.first:
    #        print("Adjust date", parse.parsedtime, "->", parse.update.rawtime)
    #        parse.parsedtime = parse.update.rawtime

    parse.deploy_timestamp()


lparse = fetchhelper.ParseData(update, 'landkreis')
parse_table(lparse, html, 'landkreis')

rparse = fetchhelper.ParseData(update, 'regierungsbezirk')
parse_table(rparse, html, 'regierungsbezirk')

fetchhelper.git_commit([rparse, lparse], args)
