#!/usr/bin/env python3

# Extracts the table from a Metrics Timeline Markdown file and outputs it as
# CSV.

import csv
import datetime
import getopt
import sys

import parser

def usage(file=sys.stdout):
    print(f"""\
Usage: {sys.argv[0]} [FILENAME]...

Extracts the table from a Metrics Timeline Markdown file and outputs it
in CSV.

  -h, --help  show this help\
""", file=file)

def format_bool(b):
    if b:
        return "T"
    else:
        return "F"

def format_date(d):
    if d is None:
        return ""
    elif isinstance(d, datetime.datetime):
        return d.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return d.strftime("%Y-%m-%d")

def entry_to_row(entry):
    return {
        "start_date": format_date(entry.start_date),
        "start_date_is_approx": format_bool(entry.start_date_is_approx),
        "end_date": format_date(entry.end_date),
        "end_date_is_approx": format_bool(entry.end_date_is_approx),
        "places": " ".join(sorted(entry.places)),
        "protocols": " ".join(sorted(entry.protocols)),
        "description": entry.description.to_markdown(),
        "links": " ".join(link.to_markdown() for link in entry.links),
        "is_unknown": format_bool(entry.is_unknown),
    }

def process(r, csv_w):
    for x in parser.parse(r):
        if isinstance(x, str):
            # Ignore non-table parts of the markup.
            continue
        for entry in x:
            csv_w.writerow(entry_to_row(entry))

opts, filenames = getopt.gnu_getopt(sys.argv[1:], "h", ["help"])
for o, a in opts:
    if o == "-h" or o == "--help":
        usage()
        sys.exit()

csv_w = csv.DictWriter(sys.stdout, [
    "start_date",
    "start_date_is_approx",
    "end_date",
    "end_date_is_approx",
    "places",
    "protocols",
    "description",
    "links",
    "is_unknown",
])
csv_w.writeheader()

if not filenames:
    process(sys.stdin, csv_w)
else:
    for filename in filenames:
        with open(filename) as r:
            process(r, csv_w)
