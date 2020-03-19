#!/usr/bin/env bash
set -eu

for SUB in de_rki de_by_lgl de_bw_soz; do
	( set -e; cd $SUB; ./fetch.py "$@" )
done
