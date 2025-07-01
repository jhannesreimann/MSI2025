#!/usr/bin/env python3
"""
Measure HTTP/2 timings for domains that support HTTP/3.
Reads http3_results.csv from Task2, filters domains with supports_http3==True,
and runs curl measurements with HTTP/2 only. The HTTP/3 results are copied from
the original file to http3_top_results.csv for comparison.
"""
import csv
import subprocess
import sys
import os
import socket
import ipaddress
import json
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

# Configuration
INPUT_FILE = 'http3_results.csv'  # Path to Task2 results
OUTPUT_HTTP3 = 'http3_top_results.csv'     # Copy of HTTP/3 results
OUTPUT_HTTP2 = 'http2_top_results.csv'     # New HTTP/2 measurements
NUM_WORKERS = 10
TIMEOUT = 4
MAX_TOP = 1000

# Curl JSON format
CURL_FORMAT = '{' + '\n'.join([
    '"time_namelookup": %{time_namelookup},',
    '"time_connect": %{time_connect},',
    '"time_appconnect": %{time_appconnect},',
    '"time_pretransfer": %{time_pretransfer},',
    '"time_redirect": %{time_redirect},',
    '"time_starttransfer": %{time_starttransfer},',
    '"time_total": %{time_total},',
    '"remote_ip": "%{remote_ip}",',
    '"remote_port": "%{remote_port}"',
    '}'
])
CSV_HEADER = ['id','domain','protocol',
              'time_namelookup','time_connect','time_appconnect',
              'time_pretransfer','time_redirect','time_starttransfer',
              'time_total','remote_ip','remote_port']



def test_http2(entry):
    """Test a domain with HTTP/2 protocol"""
    domain_id = entry['id']
    domain = entry['domain']
    if not domain.startswith('www.'):
        domain = f'www.{domain}'
    url = domain if domain.startswith('http') else f'https://{domain}'
    
    print(f"Testing {url} with HTTP/2 (ID: {domain_id})...")
    
    # Use HTTP/2 flag with curl
    cmd = [
        'curl', '--http2',
        '-s', '-m', str(TIMEOUT),
        '-o', '/dev/null', '-w', CURL_FORMAT,
        '-4',  # Force IPv4 but let curl handle DNS resolution
        url
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT+5)
        success = proc.returncode == 0
        metrics = json.loads(proc.stdout) if success else {}
    except Exception as e:
        print(f"Error testing {domain} (ID: {domain_id}): {str(e)}")
        metrics = {}

    row = {
        'id': domain_id,
        'domain': domain,
        'protocol': 'HTTP/2',
    }
    for key in ['time_namelookup','time_connect','time_appconnect',
                'time_pretransfer','time_redirect','time_starttransfer','time_total']:
        row[key] = round(float(metrics.get(key, 0)) * 1000, 2)
    row['remote_ip'] = metrics.get('remote_ip', '')
    row['remote_port'] = metrics.get('remote_port', '')
    return row


def main():
    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Input file {INPUT_FILE} not found.")
        sys.exit(1)
        
    # Read HTTP/3 results from Task2
    http3_domains = []
    http3_results = []
    
    print(f"Reading HTTP/3 results from {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Only process domains that support HTTP/3
            if row.get('supports_http3', '').lower() == 'true':
                # Save the full row for HTTP/3 results
                http3_results.append({
                    'id': row['id'],
                    'domain': row['domain'],
                    'protocol': 'HTTP/3',
                    'time_namelookup': row.get('time_namelookup', '0'),
                    'time_connect': row.get('time_connect', '0'),
                    'time_appconnect': row.get('time_appconnect', '0'),
                    'time_pretransfer': row.get('time_pretransfer', '0'),
                    'time_redirect': row.get('time_redirect', '0'),
                    'time_starttransfer': row.get('time_starttransfer', '0'),
                    'time_total': row.get('time_total', '0'),
                    'remote_ip': row.get('remote_ip', ''),
                    'remote_port': row.get('remote_port', '')
                })
                # Add to the list of domains to test with HTTP/2
                http3_domains.append({
                    'id': row['id'],
                    'domain': row['domain']
                })
    
    # Limit to MAX_TOP domains
    http3_domains = http3_domains[:min(MAX_TOP, len(http3_domains))]
    http3_results = http3_results[:min(MAX_TOP, len(http3_results))]
    
    if not http3_domains:
        print("No HTTP/3-supported domains found.")
        sys.exit(1)
    
    print(f"Found {len(http3_domains)} domains with HTTP/3 support.")
    
    # Save HTTP/3 results to output file
    print(f"Saving HTTP/3 results to {OUTPUT_HTTP3}...")
    with open(OUTPUT_HTTP3, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADER)
        writer.writeheader()
        for result in http3_results:
            writer.writerow(result)
    
    # Run HTTP/2 tests
    print(f"\nTesting {len(http3_domains)} domains with HTTP/2...")
    with open(OUTPUT_HTTP2, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADER)
        writer.writeheader()
        
        # Process domains in parallel
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            for result in executor.map(test_http2, http3_domains):
                writer.writerow(result)
    
    print(f"\nMeasurements completed. Results saved to:")
    print(f"- HTTP/3: {OUTPUT_HTTP3}")
    print(f"- HTTP/2: {OUTPUT_HTTP2}")
    print("\nYou can now run plot_protocol_boxplots.py to compare the results.")



if __name__ == '__main__':
    main()
