#!/usr/bin/env python3
"""
Generate side-by-side boxplots comparing HTTP/2 and HTTP/3 timing metrics.
Reads CSVs from measure_protocols.py and computes event durations.
"""
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

def compute_durations(df):
    # Compute segment durations (ms) from cumulative times
    df['redirect_duration'] = df['time_redirect']
    df['dns_duration'] = df['time_namelookup']
    df['connect_duration'] = df['time_connect'] - df['time_namelookup']
    df['tls_duration'] = df['time_appconnect'] - df['time_connect']
    df['pretransfer_duration'] = df['time_pretransfer'] - df['time_appconnect']
    df['ttfb_duration'] = df['time_starttransfer'] - df['time_pretransfer']
    df['transfer_duration'] = df['time_total'] - df['time_starttransfer']
    return df

def plot_protocol_boxplots(http2_csv, http3_csv, output_png):
    # Load data
    df2 = pd.read_csv(http2_csv)
    df3 = pd.read_csv(http3_csv)
    # Compute durations
    df2 = compute_durations(df2)
    df3 = compute_durations(df3)

    # Define events and labels
    events = [
        ('redirect_duration', 'Redirect'),
        ('dns_duration', 'DNS Lookup'),
        ('connect_duration', 'TCP Connect'),
        ('tls_duration', 'TLS Handshake'),
        ('pretransfer_duration', 'Pre-Transfer'),
        ('ttfb_duration', 'Time to First Byte'),
        ('transfer_duration', 'Content Transfer'),
    ]

    # Prepare grouped positions
    n = len(events)
    group_centers = list(range(1, n*3, 3))  # e.g., [1,4,7,...]
    positions2 = [c - 0.6 for c in group_centers]
    positions3 = [c + 0.6 for c in group_centers]

    # Gather data
    data2 = [df2[col].dropna() for col, _ in events]
    data3 = [df3[col].dropna() for col, _ in events]

    # Plot
    plt.figure(figsize=(14, 8))
    b2 = plt.boxplot(data2, positions=positions2, widths=1.0,
                     patch_artist=True, boxprops=dict(facecolor='lightblue'),
                     medianprops=dict(color='blue'), showfliers=False)
    b3 = plt.boxplot(data3, positions=positions3, widths=1.0,
                     patch_artist=True, boxprops=dict(facecolor='lightgreen'),
                     medianprops=dict(color='green'), showfliers=False)

    # X-axis labels
    plt.xticks(group_centers, [label for _, label in events], rotation=45, ha='right')
    plt.ylabel('Duration (ms)')
    plt.title('HTTP/2 vs HTTP/3 Timing Metrics Comparison')
    # Legend
    plt.legend([b2['boxes'][0], b3['boxes'][0]], ['HTTP/2', 'HTTP/3'])
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(output_png, dpi=300)
    print(f"Saved comparison boxplot to {output_png}")


def main():
    http2_csv = sys.argv[1] if len(sys.argv) > 1 else 'http2_top_results.csv'
    http3_csv = sys.argv[2] if len(sys.argv) > 2 else 'http3_top_results.csv'
    output_png = sys.argv[3] if len(sys.argv) > 3 else 'protocol_comparison_boxplots.png'
    if not os.path.exists(http2_csv) or not os.path.exists(http3_csv):
        print(f"ERROR: Input files not found: {http2_csv}, {http3_csv}")
        sys.exit(1)
    plot_protocol_boxplots(http2_csv, http3_csv, output_png)

if __name__ == '__main__':
    main()
