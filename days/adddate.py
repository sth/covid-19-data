import csv, os, re, datetime

for fn in os.listdir('.'):
    if not fn.endswith('.csv'):
        continue
    with open(fn, 'r') as f:
        cf = csv.reader(f)
        header = next(cf)
        if len(header) not in [3, 5]:
            continue
        d = datetime.datetime.strptime(fn, 'data_%Y-%m-%d.csv')
        d += datetime.timedelta(hours=15)
        dstr = d.isoformat()
        with open(fn + '.fix', 'w') as of:
            cof = csv.writer(of)
            cof.writerow([header[0], 'Date'] + header[1:])

            for line in cf:
                line[1:1] = [dstr]
                cof.writerow(line)
    os.rename(fn + '.fix', fn)
