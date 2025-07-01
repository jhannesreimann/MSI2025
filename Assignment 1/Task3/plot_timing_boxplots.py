#!/usr/bin/env python3
"""
Generate boxplots for HTTP/3 timing metrics.
Reads output from timing_analysis.py (http3_timing_metrics.csv) and creates
boxplots for each event duration across all measurements.
"""
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

def plot_timing_boxplots(input_csv, output_png):
    # Load timing metrics
    df = pd.read_csv(input_csv)
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
    # Extract data and labels
    data = [df[col] for col, _ in events]
    labels = [label for _, label in events]

    # Plot boxplots
    plt.figure(figsize=(12, 6))
    plt.boxplot(data, tick_labels=labels, showfliers=False)
    plt.title('HTTP/3 Request Timing Metrics Boxplots')
    plt.ylabel('Duration (ms)')
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(output_png, dpi=300)
    print(f"Saved boxplot to {output_png}")

def main():
    # Argument parsing
    input_csv = sys.argv[1] if len(sys.argv) > 1 else 'http3_timing_metrics.csv'
    output_png = sys.argv[2] if len(sys.argv) > 2 else 'http3_timing_boxplots.png'
    if not os.path.exists(input_csv):
        print(f"ERROR: Input file {input_csv} not found.")
        sys.exit(1)
    plot_timing_boxplots(input_csv, output_png)

if __name__ == '__main__':
    main()
