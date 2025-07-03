import pandas as pd
import requests, io, tarfile, sys, os
import tempfile
from io import StringIO
from md2csv import process, entry_to_row, csv

# 1. Download Tor user counts (relay users) for all countries and specifically Germany.
url_all = "https://metrics.torproject.org/userstats-relay-country.csv?country=all&start=2023-01-01&end=2023-12-31"
url_de  = "https://metrics.torproject.org/userstats-relay-country.csv?country=de&start=2023-01-01&end=2023-12-31"
df_global = pd.read_csv(url_all, comment='#')
df_germany = pd.read_csv(url_de, comment='#')
print(df_global.head(), df_germany.head())

# 2. Download TorPerf performance data (public server, 50 KiB file).
url_perf = "https://metrics.torproject.org/torperf.csv?filesize=50kb&server=public&start=2023-01-01&end=2023-12-31"
df_perf = pd.read_csv(url_perf, comment='#')
print(df_perf.head())

'''
# 3. Fetch a sample OnionPerf archive from CollecTor and extract.
tor_url = "https://collector.torproject.org/archive/onionperf/onionperf-2023-01.tar.xz"
res = requests.get(tor_url, headers={"User-Agent": "Mozilla/5.0"})
open('onionperf-2023-01.tar.xz','wb').write(res.content)
with tarfile.open('onionperf-2023-01.tar.xz') as tar:
    tar.extractall()  # extracts CSV analysis files
# Parse the extracted OnionPerf CSV (example filename below; adjust if needed).
df_onion = pd.read_csv('onionperf_2023-01/analysis/throughput_onion_2023-01.csv')
print(df_onion.head())
'''

# 4. Fetch a sample Onionoo archive from CollecTor and extract.
onnx_url = "https://onionoo.torproject.org/summary?flag=Exit&country=DE"
resp = requests.get(onnx_url)
exits_de = resp.json()['relays']
print(exits_de)

