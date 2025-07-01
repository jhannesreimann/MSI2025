#!/usr/bin/env python3
import subprocess
import csv
import time
import socket
import ipaddress
from concurrent.futures import ThreadPoolExecutor
import os
import sys
from urllib.parse import urlparse

# Configuration parameters
INPUT_FILE = 'domains.csv'  # Input file with id,www.url format
OUTPUT_FILE = 'http3_results.csv'  # Output file for results
NUM_WORKERS = 10  # Number of parallel threads for measurements
TIMEOUT = 4  # Timeout for curl in seconds

# Format string for curl metrics
# This defines the JSON structure that curl will output with timing data
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
    '}'])

# Header fields for the output CSV file
CSV_HEADER = [
    'id', 'domain', 'supports_http3', 
    'time_namelookup', 'time_connect', 'time_appconnect', 
    'time_pretransfer', 'time_redirect', 'time_starttransfer', 
    'time_total', 'remote_ip', 'remote_port'
]

def test_http3(row):
    """
    Tests HTTP/3 connection for a domain and returns the results.
    
    Args:
        row (list): A list containing domain ID and domain name
        
    Returns:
        dict: Dictionary containing all measurement results and metrics
    """
    domain_id = row[0]
    domain = row[1]
    
    # Ensure domain has www prefix if not already present
    if not domain.startswith('www.'):
        domain = f'www.{domain}'
    
    # Ensure domain has https:// prefix
    if not domain.startswith('http'):
        url = f'https://{domain}'
    else:
        url = domain
    
    print(f"Testing {url} (ID: {domain_id})...")
    
    # Prepare result dictionary with default values
    result = {
        'id': domain_id,
        'domain': domain,
        'supports_http3': False,
        'time_namelookup': 0,
        'time_connect': 0,
        'time_appconnect': 0,
        'time_pretransfer': 0,
        'time_redirect': 0,
        'time_starttransfer': 0,
        'time_total': 0,
        'remote_ip': '',
        'remote_port': ''
    }
    
    # Prepare the curl command with HTTP/3-only flag and IPv4 enforcement
    cmd = [
        'curl',
        '--http3-only',                                 # Enable HTTP/3 without fallback
        '-s',                                           # Silent mode
        '-m', str(TIMEOUT),                             # Set timeout
        '-o', '/dev/null',                              # Discard content output
        '-w', CURL_FORMAT,                              # Use our metric format
        '-4',                                           # Force IPv4 (but let curl handle DNS lookup)
        url
    ]
    
    try:
        # Execute curl command
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT+5)
        
        if process.returncode == 0:
            # HTTP/3 connection successful
            result['supports_http3'] = True
            
            # Parse curl output
            curl_output = process.stdout.strip()
            try:
                # Convert JSON string to Python dictionary
                metrics = eval(curl_output.replace('null', 'None'))
                
                # Convert timing metrics from seconds to milliseconds
                for key in ['time_namelookup', 'time_connect', 'time_appconnect', 
                           'time_pretransfer', 'time_redirect', 'time_starttransfer', 
                           'time_total']:
                    result[key] = round(float(metrics.get(key, 0)) * 1000, 2)  # Convert seconds to ms
                
                # Get network information
                result['remote_ip'] = metrics.get('remote_ip', '')
                result['remote_port'] = metrics.get('remote_port', '')
            except (SyntaxError, ValueError) as e:
                # Handle parsing errors
                print(f"Error for {domain} (ID: {domain_id}): Failed to parse curl output: {str(e)}")
        else:
            # HTTP/3 connection failed
            error_msg = f'HTTP/3 not supported (curl exit code: {process.returncode})'
            if process.stderr:
                error_msg += f' - {process.stderr.strip()}'
            print(f"Error for {domain} (ID: {domain_id}): {error_msg}")
    except subprocess.TimeoutExpired:
        # Handle timeout
        print(f"Error for {domain} (ID: {domain_id}): Timeout after {TIMEOUT} seconds")
    except Exception as e:
        # Handle any other exceptions
        print(f"Error for {domain} (ID: {domain_id}): {str(e)}")
    
    return result

def main():
    """
    Main function to orchestrate the HTTP/3 adoption measurement.
    - Checks curl availability and HTTP/3 support
    - Reads domains from input file
    - Processes domains in parallel
    - Writes results to output file
    - Displays summary statistics
    """
    # Check if curl is available and supports HTTP/3
    try:
        curl_version = subprocess.run(['curl', '--version'], capture_output=True, text=True)
        if 'HTTP3' not in curl_version.stdout:
            print("WARNING: Your curl version might not support HTTP/3.")
            print("Make sure curl was compiled with HTTP/3 support.")
            print("Current curl version:")
            print(curl_version.stdout.split('\n')[0])
            response = input("Do you want to continue anyway? (y/n): ")
            if response.lower() != 'y':
                sys.exit(1)
    except FileNotFoundError:
        print("ERROR: curl not found. Please install curl.")
        sys.exit(1)
    
    try:
        # Read input file with domains
        with open(INPUT_FILE, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header
            domains = list(reader)
        
        total_domains = len(domains)
        print(f"Starting tests for {total_domains} domains...")
        
        # Prepare output file
        with open(OUTPUT_FILE, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADER)
            writer.writeheader()
            
            # Test domains in parallel
            count = 0
            with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
                for result in executor.map(test_http3, domains):
                    writer.writerow(result)
                    count += 1
                    if count % 100 == 0:
                        print(f"Progress: {count}/{total_domains} ({count/total_domains*100:.2f}%)")
        
        # Calculate statistics
        with open(OUTPUT_FILE, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            results = list(reader)
            
            http3_supported = sum(1 for row in results if row['supports_http3'] == 'True')
            
            print(f"\nDone! Results saved to {OUTPUT_FILE}")
            print(f"HTTP/3 is supported by {http3_supported} out of {total_domains} domains ({http3_supported/total_domains*100:.2f}%)")
    
    except FileNotFoundError:
        print(f"ERROR: Input file {INPUT_FILE} not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()