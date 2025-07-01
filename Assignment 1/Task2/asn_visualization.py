#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend (important for servers without display)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Configuration
INPUT_FILE = 'asn_http3_websites.csv'  # Your ASN analysis results
OUTPUT_PNG = 'asn_http3_distribution.png'  # Output image file
TOP_N = 15  # Number of top ASNs to display in the chart

ASN_TO_ORG = {
    'AS13335': 'Cloudflare',
    'AS15169': 'Google',
    'AS16509': 'Amazon AWS',
    'AS8075': 'Microsoft',
    'AS14618': 'Amazon',
    'AS16276': 'OVH',
    'AS24940': 'Hetzner',
    'AS14061': 'DigitalOcean',
    'AS20940': 'Akamai',
    'AS396982': 'Google Cloud',
    'AS32934': 'Facebook',
    'AS54113': 'Fastly',
    'AS4134': 'Chinanet',
    'AS3356': 'Level3/CenturyLink',
    'AS19551': 'Incapsula',
    'AS46606': 'Unified Layer',
    'AS22822': 'Limelight',
    'AS9299': 'Philippine Long Distance',
    'AS37963': 'Alibaba Cloud',
    'AS26496': 'GoDaddy',
    'AS13335': 'Cloudflare'
}

def get_org_for_asn(asn):
    """Fetch organization name for ASN, with caching."""
    # Use static mapping if available
    if asn in ASN_TO_ORG and ASN_TO_ORG[asn] != asn:
        return ASN_TO_ORG[asn]
    # If requests not available, return ASN
    if not HAS_REQUESTS:
        return asn
    try:
        # Query BGPView API for ASN info
        asn_num = asn.lstrip('AS').lstrip('as')
        url = f"https://api.bgpview.io/asn/{asn_num}"
        resp = requests.get(url, timeout=5)
        data = resp.json().get('data', {})
        org_name = data.get('description')
        if org_name:
            # Cache mapping
            ASN_TO_ORG[asn] = org_name
            return org_name
    except Exception:
        pass
    return asn

def format_asn_label(asn, count, total_sites):
    """Format ASN label with organization name if available and percentage"""
    org_name = get_org_for_asn(asn)
    percentage = (count / total_sites) * 100
    return f"{org_name}\n({percentage:.1f}%)"

def visualize_asn_distribution(input_file, output_png, top_n=TOP_N):
    """
    Creates a bar chart of ASN distribution for HTTP/3 websites.
    
    Args:
        input_file (str): Path to the CSV file with ASN counts
        output_png (str): Path to save the output PNG image
        top_n (int): Number of top ASNs to display
    """
    try:
        # Read the CSV file into a pandas DataFrame
        print(f"Reading data from {input_file}...")
        df = pd.read_csv(input_file)
        
        # Sort by number of HTTP/3 websites in descending order
        df = df.sort_values(by='num_http3_websites', ascending=False)
        
        # Calculate total HTTP/3 websites
        total_http3_sites = df['num_http3_websites'].sum()
        print(f"Total HTTP/3 websites: {total_http3_sites}")
        
        # Get the top N ASNs
        top_asns = df.head(top_n)
        
        # Calculate percentage of total for the top ASNs
        top_percentage = top_asns['num_http3_websites'].sum() / total_http3_sites * 100
        print(f"Top {top_n} ASNs account for {top_percentage:.2f}% of all HTTP/3 websites")
        
        # Create a larger figure for better readability
        plt.figure(figsize=(12, 8))
        
        # Create the bar chart
        bars = plt.bar(
            range(len(top_asns)), 
            top_asns['num_http3_websites'],
            color='skyblue',
            edgecolor='navy'
        )
        
        # Add labels and title
        plt.title(f'Top {top_n} ASNs by HTTP/3 Website Count', fontsize=16)
        plt.xlabel('Autonomous System', fontsize=14)
        plt.ylabel('Number of HTTP/3 Websites', fontsize=14)
        
        # Format x-axis labels with ASN and org name
        plt.xticks(
            range(len(top_asns)),
            [format_asn_label(asn, count, total_http3_sites) 
             for asn, count in zip(top_asns['asn'], top_asns['num_http3_websites'])],
            rotation=45,
            ha='right',
            fontsize=10
        )
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width()/2.,
                height + 0.1,
                f'{int(height)}',
                ha='center',
                fontsize=10
            )
        
        # Add a grid for better readability
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Add a note about the total
        plt.figtext(
            0.5, 0.01,
            f"Note: Top {top_n} ASNs represent {top_percentage:.1f}% of all {total_http3_sites} HTTP/3 websites found.",
            ha='center',
            fontsize=10,
            bbox={"facecolor":"lightgrey", "alpha":0.5, "pad":5}
        )
        
        # Tight layout to make everything fit
        plt.tight_layout(rect=[0, 0.03, 1, 0.97])
        
        # Save the figure
        print(f"Saving chart to {output_png}...")
        plt.savefig(output_png, dpi=300, bbox_inches='tight')
        print(f"Chart saved successfully!")
        
        # Display ASN information for the report
        print("\nTop ASNs for HTTP/3 Adoption:")
        for i, (_, row) in enumerate(top_asns.iterrows(), 1):
            asn = row['asn']
            count = row['num_http3_websites']
            percentage = (count / total_http3_sites) * 100
            org_name = get_org_for_asn(asn)
            print(f"{i}. {asn} ({org_name}): {count} websites ({percentage:.2f}%)")
        
    except Exception as e:
        print(f"Error during visualization: {str(e)}")
        sys.exit(1)

def main():
    """
    Main function to create ASN distribution visualization.
    """
    # Check if custom input file was provided
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = INPUT_FILE
    
    # Check if custom output file was provided
    if len(sys.argv) > 2:
        output_png = sys.argv[2]
    else:
        output_png = OUTPUT_PNG
    
    # Check if custom top_n was provided
    if len(sys.argv) > 3:
        try:
            top_n = int(sys.argv[3])
        except ValueError:
            top_n = TOP_N
    else:
        top_n = TOP_N
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"ERROR: Input file {input_file} not found.")
        print(f"Usage: python {sys.argv[0]} [input_csv_file] [output_png_file] [top_n]")
        sys.exit(1)
    
    visualize_asn_distribution(input_file, output_png, top_n)

if __name__ == "__main__":
    main()