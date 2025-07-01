#!/usr/bin/env python3
"""
Generate CDF plots comparing HTTP/2 and HTTP/3 browser timing metrics.
Uses data from measure_browser_timing.py (browser_timing_http2.csv and browser_timing_http3.csv).
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import os

# Configuration
INPUT_HTTP3 = 'browser_timing_http3.csv'
INPUT_HTTP2 = 'browser_timing_http2.csv'
OUTPUT_PNG = 'browser_timing_cdf.png'
OUTPUT_HTTP2_FILTERED_CSV = 'browser_timing_http2_filtered.csv'
OUTPUT_HTTP3_FILTERED_CSV = 'browser_timing_http3_filtered.csv'

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

def plot_cdf(df2, df3, output_png):
    """
    Create CDF plots for HTTP/2 and HTTP/3 timing metrics.
    
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
    
    # Colors for each metric
    colors = ['blue', 'green', 'red']
    
    # Create figure
    plt.figure(figsize=(12, 8))
    
    # Plot CDFs for each metric
    for i, (metric, label) in enumerate(metrics):
        color = colors[i]
        
        # Sort values for CDF
        http2_values = sorted(df2[metric].dropna())
        http3_values = sorted(df3[metric].dropna())
        
        # Calculate CDF points
        http2_y = np.arange(1, len(http2_values) + 1) / len(http2_values)
        http3_y = np.arange(1, len(http3_values) + 1) / len(http3_values)
        
        # Plot HTTP/2 (dashed line)
        plt.plot(http2_values, http2_y, linestyle='--', color=color, 
                 label=f'{label} - HTTP/2', linewidth=2)
        
        # Plot HTTP/3 (solid line)
        plt.plot(http3_values, http3_y, linestyle='-', color=color, 
                 label=f'{label} - HTTP/3', linewidth=2)
    
    # Add grid, labels, and legend
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xlabel('Time (ms)', fontsize=12)
    plt.ylabel('Cumulative Probability', fontsize=12)
    plt.title('CDF of Browser Timing Metrics: HTTP/2 vs HTTP/3', fontsize=14)
    plt.legend(loc='lower right', fontsize=10)
    
    # Set x-axis limits to focus on relevant range (0 to 95th percentile)
    all_values = []
    for metric, _ in metrics:
        all_values.extend(df2[metric].dropna())
        all_values.extend(df3[metric].dropna())
    
    x_max = np.percentile(all_values, 95)
    plt.xlim(0, x_max)
    
    # Save figure
    plt.tight_layout()
    plt.savefig(output_png, dpi=300)
    print(f"Saved CDF plot to {output_png}")
    
    # Create a zoomed-in version focusing on the first 1000ms
    plt.xlim(0, min(1000, x_max))
    plt.savefig(output_png.replace('.png', '_zoom.png'), dpi=300)
    print(f"Saved zoomed CDF plot to {output_png.replace('.png', '_zoom.png')}")

def print_summary_statistics(df2, df3):
    """
    Print summary statistics for the timing metrics.
    
    Args:
        df2: HTTP/2 DataFrame
        df3: HTTP/3 DataFrame
    """
    metrics = ['responseStart', 'domInteractive', 'domComplete']
    
    print("\nSummary Statistics (in milliseconds):")
    print("=" * 80)
    print(f"{'Metric':<20} {'Protocol':<10} {'Count':<8} {'Median':<10} {'Mean':<10} {'P25':<10} {'P75':<10}")
    print("-" * 80)
    
    for metric in metrics:
        for df, protocol in [(df2, 'HTTP/2'), (df3, 'HTTP/3')]:
            count = len(df[metric].dropna())
            median = df[metric].median()
            mean = df[metric].mean()
            p25 = df[metric].quantile(0.25)
            p75 = df[metric].quantile(0.75)
            
            print(f"{metric:<20} {protocol:<10} {count:<8} {median:<10.1f} {mean:<10.1f} {p25:<10.1f} {p75:<10.1f}")
        print("-" * 80)

def save_filtered_results(df2_filtered, df3_verified, http2_csv, http3_csv):
    """
    Save the filtered HTTP/2 and HTTP/3 results to CSV files.
    
    Args:
        df2_filtered: Filtered HTTP/2 DataFrame
        df3_verified: Verified HTTP/3 DataFrame
        http2_csv: Output CSV file for HTTP/2 filtered data
        http3_csv: Output CSV file for HTTP/3 verified data
    """
    # Save filtered HTTP/2 data
    df2_filtered.to_csv(http2_csv, index=False)
    print(f"Saved filtered HTTP/2 data to {http2_csv}")
    
    # Save verified HTTP/3 data
    df3_verified.to_csv(http3_csv, index=False)
    print(f"Saved verified HTTP/3 data to {http3_csv}")

def main():
    # Parse command line arguments
    http2_file = sys.argv[1] if len(sys.argv) > 1 else INPUT_HTTP2
    http3_file = sys.argv[2] if len(sys.argv) > 2 else INPUT_HTTP3
    output_png = sys.argv[3] if len(sys.argv) > 3 else OUTPUT_PNG
    http2_filtered_csv = sys.argv[4] if len(sys.argv) > 4 else OUTPUT_HTTP2_FILTERED_CSV
    http3_filtered_csv = sys.argv[5] if len(sys.argv) > 5 else OUTPUT_HTTP3_FILTERED_CSV
    
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
    
    # Print summary statistics using filtered data
    print_summary_statistics(df2_filtered, df3_verified)
    
    # Plot CDF using filtered data
    plot_cdf(df2_filtered, df3_verified, output_png)
    
    # Save filtered results to CSV files
    save_filtered_results(df2_filtered, df3_verified, http2_filtered_csv, http3_filtered_csv)
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main()
