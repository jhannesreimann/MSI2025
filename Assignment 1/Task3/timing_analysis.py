#!/usr/bin/env python3
"""
Compute start, end times, and durations for HTTP/3 request segments.
Reads http3_results.csv and writes http3_timing_metrics.csv with detailed timing.
"""
import pandas as pd
import sys
import os

def compute_timing_metrics(input_csv, output_csv):
    # Load data
    df = pd.read_csv(input_csv)
    
    # Filter to only include domains that support HTTP/3
    df = df[df['supports_http3'] == True]
    
    # Ensure numeric and fill missing
    cols = ['time_redirect','time_namelookup','time_connect',
            'time_appconnect','time_pretransfer','time_starttransfer','time_total']
    for c in cols:
        df[c] = pd.to_numeric(df.get(c, 0), errors='coerce').fillna(0.0)

    # Segment calculations
    # Redirect
    df['redirect_start'] = 0.0
    df['redirect_end'] = df['time_redirect']
    df['redirect_duration'] = df['time_redirect']
    # DNS lookup
    df['dns_start'] = df['time_redirect']
    df['dns_end'] = df['time_redirect'] + df['time_namelookup']
    df['dns_duration'] = df['time_namelookup']
    # TCP connect
    df['connect_start'] = df['dns_end']
    df['connect_end'] = df['time_connect']
    df['connect_duration'] = df['time_connect'] - df['time_namelookup']
    # TLS handshake
    df['tls_start'] = df['time_connect']
    df['tls_end'] = df['time_appconnect']
    df['tls_duration'] = df['time_appconnect'] - df['time_connect']
    # Pre-transfer
    df['pretransfer_start'] = df['time_appconnect']
    df['pretransfer_end'] = df['time_pretransfer']
    df['pretransfer_duration'] = df['time_pretransfer'] - df['time_appconnect']
    # Time to first byte
    df['ttfb_start'] = df['time_pretransfer']
    df['ttfb_end'] = df['time_starttransfer']
    df['ttfb_duration'] = df['time_starttransfer'] - df['time_pretransfer']
    # Content transfer
    df['transfer_start'] = df['time_starttransfer']
    df['transfer_end'] = df['time_total']
    df['transfer_duration'] = df['time_total'] - df['time_starttransfer']

    # Write to output
    df.to_csv(output_csv, index=False)
    print(f"Wrote timing metrics to {output_csv}")


def main():
    if len(sys.argv) > 1:
        inp = sys.argv[1]
    else:
        inp = 'http3_results.csv'
    if len(sys.argv) > 2:
        out = sys.argv[2]
    else:
        out = 'http3_timing_metrics.csv'
    if not os.path.exists(inp):
        print(f"ERROR: input file {inp} not found.")
        sys.exit(1)
    compute_timing_metrics(inp, out)

if __name__ == '__main__':
    main()
