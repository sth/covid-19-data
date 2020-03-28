#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../helper'))

import argparse
import fetchhelper

ap = argparse.ArgumentParser()
fetchhelper.add_arguments(ap)
args = ap.parse_args()

import subprocess, datetime, re, csv, os, sys
from bs4 import BeautifulSoup
import dateutil.tz

datatz = dateutil.tz.gettz('Europe/Berlin')

update = fetchhelper.Updater('https://www.lgl.bayern.de/gesundheit/infektionsschutz/infektionskrankheiten_a_z/coronavirus/karte_coronavirus/index.htm')
update.check_fetch(rawfile=args.rawfile)
if args.only_changed:
    if not update.raw_changed():
        print("downloaded raw data unchanged")
        exit(0)

# accidentally duplicated <tr>
update.rawdata = re.sub(r'<tr>\s*<tr>', r'<tr>', update.rawdata)
update.rawdata = re.sub(r'(<th><span>[^<>]*</span>)</(td|div)>', r'\1</th>', update.rawdata)
#print(update.rawdata)
html = BeautifulSoup(update.rawdata, 'html.parser')

def get_labeltime(text):
    mo = re.search(r'Stand:? (\S* \S*)', text)
    if mo is None:
        return None
    try:
        return datetime.datetime.strptime(mo.group(1), '%d.%m.%Y %H:%M') \
            .replace(tzinfo=datatz)
    except ValueError:
        return datetime.datetime.strptime(mo.group(1), '%d.%m.%Y, %H:%M') \
            .replace(tzinfo=datatz)

for p in html.select('.bildunterschrift'):
    text = p.get_text()
    update.contenttime = get_labeltime(text)
    if update.contenttime is not None:
        break

if update.contenttime is None:
    print("Couldn't find content time", file=sys.stderr)
    exit(1)

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

def parse_table(parse, html, select, *, optional=False):
    tables = []
    for tab in html.select('table'):
        if select(tab):
            tables.append(tab)

    if not tables:
        if optional:
            return
        print("couldn't find table %s" % parse.label, file=sys.stderr)
        exit(1)

    if len(tables) > 1:
        print("found multiple tables %s" % parse.label, file=sys.stderr)
        exit(1)

    combined = is_combined(tables[0])

    caption = tables[0].find('caption')
    if caption is not None:
        datatime = get_labeltime(caption.get_text())
    else:
        datatime = parse.parsedtime
    if datatime is None:
        print("couldn't determine datatime for %s" % parse.label, file=sys.stderr)
        exit(1)

    with open(parse.parsedfile, 'w') as outf:
        cout = csv.writer(outf)
        header = ['Area', 'Date', 'Deaths' if 'deaths' in parse.label else 'Confirmed']
        if combined:
            ths = tables[0].find_all('th')
            assert('Fälle' in ths[1].get_text())
            assert('Todesfälle' in ths[4].get_text())
            header.append('Deaths')
        cout.writerow(header)

        for tds in tab_rows(tables[0]):
            cols = [tds[0].get_text(), datatime.isoformat()]
            if combined:
                cols += [clean_num(tds[1].get_text()), clean_num(tds[4].get_text())]
            else:
                cols.append(clean_num(tds[1].get_text()))

            cout.writerow(cols)
    parse.diff()

    if args.only_changed:
        if not parse.parseddiff.changed:
            print("parsed content \"%s\" unchanged" % parse.label)
            return

    # It changed. If the current day is later than the contenttime we assume the
    # content time is a mistake and we adjust it to the current day.
    # (This problem has happend before)
    #if parse.update.rawtime.date() > parse.parsedtime.date():
    #    if parse.parseddiff.changed and not parse.parseddiff.first:
    #        print("Adjust date", parse.parsedtime, "->", parse.update.rawtime)
    #        parse.parsedtime = parse.update.rawtime

    parse.deploy_day()
    print("written %s" % parse.deployfile)

def is_regierungsbezirk(tab):
    return tab.select_one('th').string in ['Regierungsbezirk']

def is_landkreis(tab):
    return tab.select_one('th').string in ['Landkreis', 'Land-/Stadtkreis', 'Landkreis/Stadt']

def is_confirmed(tab):
    cap = tab.select_one('caption')
    return cap is None or 'Coronavirusinfektionen' in cap.get_text()

def is_combined(tab):
    return len(tab.find_all('th')) == 6

def is_deaths(tab):
    cap = tab.select_one('caption')
    return cap is not None and 'Todesfälle' in cap.get_text()

rparse = fetchhelper.ParseData(update, 'regierungsbezirk')
parse_table(rparse, html, select=(lambda tab: is_regierungsbezirk(tab) and (is_confirmed(tab) or is_combined(tab))))

rdparse = fetchhelper.ParseData(update, 'regierungsbezirk_deaths')
parse_table(rdparse, html, select=(lambda tab: is_regierungsbezirk(tab) and is_deaths(tab)), optional=True)

lparse = fetchhelper.ParseData(update, 'landkreis')
parse_table(lparse, html, select=(lambda tab: is_landkreis(tab) and (is_confirmed(tab) or is_combined(tab))))

ldparse = fetchhelper.ParseData(update, 'landkreis_deaths')
parse_table(ldparse, html, select=(lambda tab: is_landkreis(tab) and is_deaths(tab)), optional=True)

fetchhelper.git_commit([rparse, rdparse, lparse, ldparse], args)
