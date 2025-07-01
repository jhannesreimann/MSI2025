#!/usr/bin/env python3
"""
Compute raw timing deltas (HTTP/2 - HTTP/3) and plot boxplots.
Also save 25th, 50th, 75th percentiles per metric.
"""
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

# Define metrics and their display labels in the same order as plot_protocol_boxplots.py
events = [
    ('time_redirect', 'Redirect'),
    ('time_namelookup', 'DNS Lookup'),
    ('time_connect', 'TCP Connect'),
    ('time_appconnect', 'TLS Handshake'),
    ('time_pretransfer', 'Pre-Transfer'),
    ('time_starttransfer', 'Time to First Byte'),
    ('time_total', 'Content Transfer'),
]

# Extract just the metric names for processing
METRICS = [m for m, _ in events]

def compute_deltas(df2, df3):
    # Merge on id and domain
    df = pd.merge(df2, df3, on=['id', 'domain'], suffixes=('_http2', '_http3'))
    delta = pd.DataFrame()
    for m in METRICS:
        delta[m] = df[f"{m}_http2"] - df[f"{m}_http3"]
    return delta


def save_percentiles(delta_df, output_csv):
    # Compute 25th, 50th, 75th percentiles
    perc = delta_df.quantile([0.25, 0.5, 0.75]).transpose()
    perc.columns = ['p25', 'p50', 'p75']
    perc.insert(0, 'metric', perc.index)
    perc.to_csv(output_csv, index=False)
    print(f"Saved percentiles to {output_csv}")
    return perc


def plot_deltas(delta_df, output_png):
    # Get data in the same order as events
    data = [delta_df[m].dropna() for m, _ in events]
    # Use friendly labels from events
    labels = [label for _, label in events]
    
    plt.figure(figsize=(12, 6))
    plt.boxplot(data, tick_labels=labels, showfliers=False)
    plt.title('Delta per Metric (HTTP/2 - HTTP/3)')
    plt.ylabel('Delta (ms)')
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(output_png, dpi=300)
    print(f"Saved delta boxplot to {output_png}")


def main():
    # CLI args: http2_csv, http3_csv, percentiles_csv, output_png
    http2_csv = sys.argv[1] if len(sys.argv) > 1 else 'http2_top_results.csv'
    http3_csv = sys.argv[2] if len(sys.argv) > 2 else 'http3_top_results.csv'
    pcsv = sys.argv[3] if len(sys.argv) > 3 else 'delta_percentiles.csv'
    opng = sys.argv[4] if len(sys.argv) > 4 else 'delta_boxplots.png'

    for f in (http2_csv, http3_csv):
        if not os.path.exists(f):
            print(f"ERROR: Input file {f} not found.")
            sys.exit(1)

    df2 = pd.read_csv(http2_csv)
    df3 = pd.read_csv(http3_csv)
    delta_df = compute_deltas(df2, df3)
    save_percentiles(delta_df, pcsv)
    plot_deltas(delta_df, opng)

if __name__ == '__main__':
    main()
