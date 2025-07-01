#!/usr/bin/env python3
import urllib.request
import zipfile
import io
import csv
import sys

def main():
    TRANCO_ZIP_URL = 'https://tranco-list.eu/top-1m.csv.zip'
    ZIP_FILE = 'top-1m.csv.zip'
    OUTPUT_FILE = 'domains.csv'
    TOP_N = 10000

    print('Downloading Tranco Top-1M list...')
    try:
        urllib.request.urlretrieve(TRANCO_ZIP_URL, ZIP_FILE)
    except Exception as e:
        sys.exit(f'Error downloading file: {e}')

    print(f'Extracting CSV and preparing top {TOP_N} domains...')
    try:
        with zipfile.ZipFile(ZIP_FILE, 'r') as z:
            csv_name = next((name for name in z.namelist() if name.endswith('.csv')), None)
            if csv_name is None:
                sys.exit('No CSV file found in the zip archive')
            with z.open(csv_name) as f:
                reader = csv.reader(io.TextIOWrapper(f))
                with open(OUTPUT_FILE, 'w', newline='') as outfile:
                    writer = csv.writer(outfile)
                    writer.writerow(['id', 'domain'])
                    count = 0
                    for row in reader:
                        if not row or len(row) < 2:
                            continue
                        rank, domain = row[0], row[1]
                        if not rank.isdigit():
                            continue
                        if int(rank) > TOP_N:
                            break
                        if not domain.startswith('www.'):
                            domain = f'www.{domain}'
                        writer.writerow([rank, domain])
                        count += 1
        print(f'{OUTPUT_FILE} created with {count} domains')
    except Exception as e:
        sys.exit(f'Error processing ZIP file: {e}')

if __name__ == '__main__':
    main()
