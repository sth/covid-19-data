#!/usr/bin/env python3

import argparse

ap = argparse.ArgumentParser()
ap.add_argument('filename', nargs='+')
args = ap.parse_args()

import csv

for fn in args.filename:
    sum_2 = 0
    sum_3 = 0
    with open(fn) as inf:
        for row in csv.reader(inf):
            if row[1] == 'Timestamp':
                continue
            sum_2 += int(row[2])
            sum_3 += int(row[3])
    if len(args.filename) > 1:
        print(fn, end=' ')
    print(sum_2, sum_3)
