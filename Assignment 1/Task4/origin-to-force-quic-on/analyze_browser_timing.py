#!/usr/bin/env python3
"""
Analyze and visualize browser timing metrics for HTTP/3 vs HTTP/2.
Creates boxplots and computes statistics for comparison.
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import os

# Configuration
INPUT_HTTP3 = 'browser_timing_http3.csv'
INPUT_HTTP2 = 'browser_timing_http2.csv'
OUTPUT_PNG = 'browser_timing_comparison.png'
OUTPUT_DELTA_PNG = 'browser_timing_delta.png'
OUTPUT_STATS_CSV = 'browser_timing_stats.csv'

def load_and_clean_data(http2_file, http3_file):
    """
    Load and clean the timing data from both files.
    
    Args:
        http2_file: Path to HTTP/2 timing CSV
        http3_file: Path to HTTP/3 timing CSV
        
    Returns:
        Tuple of cleaned DataFrames (df2, df3)
    """
    # Load data
    df2 = pd.read_csv(http2_file)
    df3 = pd.read_csv(http3_file)
    
    # Filter successful measurements only
    df2 = df2[df2['successful'] == True]
    df3 = df3[df3['successful'] == True]
    
    # Convert timing values to milliseconds if they're not already
    for col in ['responseStart', 'domInteractive', 'domComplete']:
        for df in [df2, df3]:
            if df[col].max() < 1000:  # If values are in seconds
                df[col] = df[col] * 1000
    
    # Add protocol verification
    df2['protocol_verified'] = df2['nextHopProtocol'].apply(
        lambda x: 'h2' in str(x).lower() if pd.notna(x) else False
    )
    df3['protocol_verified'] = df3['nextHopProtocol'].apply(
        lambda x: 'h3' in str(x).lower() if pd.notna(x) else False
    )
    
    return df2, df3

def compute_statistics(df2, df3):
    """
    Compute statistics for the timing metrics.
    
    Args:
        df2: HTTP/2 DataFrame
        df3: HTTP/3 DataFrame
        
    Returns:
        DataFrame with statistics
    """
    # Metrics to analyze
    metrics = ['responseStart', 'domInteractive', 'domComplete']
    
    # Create a DataFrame to store statistics
    stats = []
    
    # Compute statistics for each metric
    for metric in metrics:
        # HTTP/2 statistics
        http2_mean = df2[metric].mean()
        http2_median = df2[metric].median()
        http2_p25 = df2[metric].quantile(0.25)
        http2_p75 = df2[metric].quantile(0.75)
        http2_iqr = http2_p75 - http2_p25
        
        # HTTP/3 statistics
        http3_mean = df3[metric].mean()
        http3_median = df3[metric].median()
        http3_p25 = df3[metric].quantile(0.25)
        http3_p75 = df3[metric].quantile(0.75)
        http3_iqr = http3_p75 - http3_p25
        
        # Compute delta (HTTP/2 - HTTP/3)
        delta_mean = http2_mean - http3_mean
        delta_median = http2_median - http3_median
        delta_p25 = http2_p25 - http3_p25
        delta_p75 = http2_p75 - http3_p75
        delta_iqr = http2_iqr - http3_iqr
        
        # Percentage improvement
        pct_improvement = ((http2_median - http3_median) / http2_median) * 100 if http2_median != 0 else 0
        
        # Add to statistics
        stats.append({
            'metric': metric,
            'http2_mean': http2_mean,
            'http2_median': http2_median,
            'http2_p25': http2_p25,
            'http2_p75': http2_p75,
            'http2_iqr': http2_iqr,
            'http3_mean': http3_mean,
            'http3_median': http3_median,
            'http3_p25': http3_p25,
            'http3_p75': http3_p75,
            'http3_iqr': http3_iqr,
            'delta_mean': delta_mean,
            'delta_median': delta_median,
            'delta_p25': delta_p25,
            'delta_p75': delta_p75,
            'delta_iqr': delta_iqr,
            'pct_improvement': pct_improvement,
            'http2_count': len(df2),
            'http3_count': len(df3)
        })
    
    return pd.DataFrame(stats)

def compute_paired_deltas(df2, df3):
    """
    Compute deltas for domains that have successful measurements in both protocols.
    Only includes domains with verified HTTP/3 protocol.
    
    Args:
        df2: HTTP/2 DataFrame
        df3: HTTP/3 DataFrame
        
    Returns:
        DataFrame with deltas
    """
    # Filter for verified HTTP/3 domains first
    df3_verified = df3[df3['protocol_verified'] == True]
    
    # Get domains that have verified HTTP/3 and also exist in HTTP/2 data
    verified_h3_domains = set(df3_verified['domain'])
    common_domains = verified_h3_domains.intersection(set(df2['domain']))
    common_domains_list = list(common_domains)  # Convert set to list for DataFrame index
    
    # Filter to common domains with verified HTTP/3
    df2_common = df2[df2['domain'].isin(common_domains)]
    df3_common = df3_verified[df3_verified['domain'].isin(common_domains)]
    
    # Set domain as index for easy subtraction
    df2_common = df2_common.set_index('domain')
    df3_common = df3_common.set_index('domain')
    
    # Metrics to compute deltas for
    metrics = ['responseStart', 'domInteractive', 'domComplete']
    
    # Initialize delta DataFrame
    delta_df = pd.DataFrame(index=common_domains_list)
    
    # Compute deltas for each metric
    for metric in metrics:
        delta_df[metric] = df2_common[metric] - df3_common[metric]
    
    return delta_df.reset_index()

def plot_comparison(df2, df3, output_png):
    """
    Create side-by-side boxplots comparing HTTP/2 and HTTP/3.
    
    Args:
        df2: HTTP/2 DataFrame
        df3: HTTP/3 DataFrame
        output_png: Output PNG file path
    """
    # Metrics to plot
    metrics = [
        ('responseStart', 'Response Start'),
        ('domInteractive', 'DOM Interactive'),
        ('domComplete', 'DOM Complete')
    ]
    
    # Prepare grouped positions
    n = len(metrics)
    group_centers = list(range(1, n*3, 3))  # e.g., [1,4,7,...]
    positions2 = [c - 0.6 for c in group_centers]
    positions3 = [c + 0.6 for c in group_centers]
    
    # Gather data
    data2 = [df2[m].dropna() for m, _ in metrics]
    data3 = [df3[m].dropna() for m, _ in metrics]
    
    # Plot
    plt.figure(figsize=(12, 6))
    b2 = plt.boxplot(data2, positions=positions2, widths=1.0,
                     patch_artist=True, boxprops=dict(facecolor='lightblue'),
                     medianprops=dict(color='blue'), showfliers=False)
    b3 = plt.boxplot(data3, positions=positions3, widths=1.0,
                     patch_artist=True, boxprops=dict(facecolor='lightgreen'),
                     medianprops=dict(color='green'), showfliers=False)
    
    # X-axis labels
    plt.xticks(group_centers, [label for _, label in metrics], rotation=45, ha='right')
    plt.ylabel('Time (ms)')
    plt.title('HTTP/2 vs HTTP/3 Browser Timing Metrics Comparison')
    
    # Legend
    plt.legend([b2['boxes'][0], b3['boxes'][0]], ['HTTP/2', 'HTTP/3'])
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(output_png, dpi=300)
    print(f"Saved comparison boxplot to {output_png}")

def plot_deltas(delta_df, output_png):
    """
    Create boxplots of the deltas (HTTP/2 - HTTP/3).
    
    Args:
        delta_df: DataFrame with deltas
        output_png: Output PNG file path
    """
    # Metrics to plot
    metrics = [
        ('responseStart', 'Response Start'),
        ('domInteractive', 'DOM Interactive'),
        ('domComplete', 'DOM Complete')
    ]
    
    # Get data in the same order as metrics
    data = [delta_df[m].dropna() for m, _ in metrics]
    # Use friendly labels from metrics
    labels = [label for _, label in metrics]
    
    plt.figure(figsize=(12, 6))
    plt.boxplot(data, tick_labels=labels, showfliers=False)
    plt.title('Delta per Metric (HTTP/2 - HTTP/3)')
    plt.ylabel('Delta (ms)')
    plt.axhline(y=0, color='r', linestyle='-', alpha=0.3)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(output_png, dpi=300)
    print(f"Saved delta boxplot to {output_png}")

def main():
    # Parse command line arguments
    http2_file = sys.argv[1] if len(sys.argv) > 1 else INPUT_HTTP2
    http3_file = sys.argv[2] if len(sys.argv) > 2 else INPUT_HTTP3
    stats_file = sys.argv[3] if len(sys.argv) > 3 else OUTPUT_STATS_CSV
    output_png = sys.argv[4] if len(sys.argv) > 4 else OUTPUT_PNG
    delta_png = sys.argv[5] if len(sys.argv) > 5 else OUTPUT_DELTA_PNG
    
    # Check if input files exist
    for f in [http2_file, http3_file]:
        if not os.path.exists(f):
            print(f"Error: Input file {f} not found.")
            sys.exit(1)
    
    # Load and clean data
    df2, df3 = load_and_clean_data(http2_file, http3_file)
    
    # Print basic information
    print(f"HTTP/2 data: {len(df2)} successful measurements")
    print(f"HTTP/3 data: {len(df3)} successful measurements")
    print(f"HTTP/2 protocol verified: {df2['protocol_verified'].sum()} of {len(df2)}")
    print(f"HTTP/3 protocol verified: {df3['protocol_verified'].sum()} of {len(df3)}")
    
    # Filter for verified HTTP/3 domains for comparison
    df3_verified = df3[df3['protocol_verified'] == True]
    verified_h3_domains = set(df3_verified['domain'])
    df2_filtered = df2[df2['domain'].isin(verified_h3_domains)]
    
    print(f"Using {len(verified_h3_domains)} domains with verified HTTP/3 protocol for comparison")
    
    # Compute statistics using filtered data
    stats_df = compute_statistics(df2_filtered, df3_verified)
    stats_df.to_csv(stats_file, index=False)
    print(f"Saved statistics to {stats_file}")
    
    # Plot comparison using filtered data
    plot_comparison(df2_filtered, df3_verified, output_png)
    
    # Compute and plot deltas using verified HTTP/3 domains
    delta_df = compute_paired_deltas(df2_filtered, df3_verified)
    plot_deltas(delta_df, delta_png)
    
    # Print summary
    print("\nSummary Statistics:")
    for _, row in stats_df.iterrows():
        metric = row['metric']
        http2_median = row['http2_median']
        http3_median = row['http3_median']
        delta = row['delta_median']
        pct = row['pct_improvement']
        
        faster = "HTTP/3" if delta > 0 else "HTTP/2"
        abs_pct = abs(pct)
        
        print(f"{metric}: {faster} is faster by {abs_pct:.1f}% ({abs(delta):.1f} ms)")

if __name__ == "__main__":
    main()
