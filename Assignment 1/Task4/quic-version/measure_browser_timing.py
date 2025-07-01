#!/usr/bin/env python3
"""
Measure browser timing statistics for HTTP/3 and HTTP/2 using Selenium.
Extracts responseStart, domInteractive, and domComplete metrics.
"""
import csv
import time
import argparse
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException

# ChromeDriver path - modify this to point to your ChromeDriver location
CHROME_DRIVER_PATH = "/usr/bin/chromedriver"  # Default location on many Linux systems

# Configuration
INPUT_FILE = 'http3_top_results.csv'
OUTPUT_HTTP3 = 'browser_timing_http3.csv'
OUTPUT_HTTP2 = 'browser_timing_http2.csv'
TIMEOUT = 30  # Timeout in seconds
MAX_RETRIES = 5
UNLIMITED_HTTP3_RETRIES = False  # Set to True to keep retrying until HTTP/3 succeeds
MAX_WEBSITES = 1000

# QUIC versions to try (in order)
QUIC_VERSIONS = ['h3-29', 'h3']

# CSV Headers
CSV_HEADER = [
    'id', 'domain', 'protocol', 'responseStart', 'domInteractive', 
    'domComplete', 'nextHopProtocol', 'successful'
]

def setup_chrome_driver(enable_quic=True, quic_version='h3-29'):
    """
    Set up Chrome WebDriver with appropriate options.
    
    Args:
        enable_quic: Whether to enable QUIC/HTTP/3 protocol
        quic_version: QUIC version to use (e.g., 'h3-29', 'h3')
        
    Returns:
        WebDriver instance
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Control QUIC/HTTP/3 support
    if enable_quic:
        # Enable QUIC and HTTP/3
        chrome_options.add_argument('--enable-quic')
        chrome_options.add_argument(f'--quic-version={quic_version}')
    else:
        # Disable QUIC to force HTTP/2
        chrome_options.add_argument('--disable-quic')
    
    # Create and return the driver
    try:
        # Create a Service object with the specified ChromeDriver path
        service = Service(executable_path=CHROME_DRIVER_PATH)
        
        # Create the driver with the service and options
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(TIMEOUT)
        return driver
    except Exception as e:
        print(f"Error setting up Chrome driver: {str(e)}")
        print("\nPossible solutions:")
        print(f"1. Make sure ChromeDriver is installed at {CHROME_DRIVER_PATH}")
        print("2. Install Chrome browser if not already installed")
        print("3. Update the CHROME_DRIVER_PATH variable in the script to point to your ChromeDriver location")
        print("\nTo install ChromeDriver on Kali Linux:")
        print("   sudo apt update")
        print("   sudo apt install chromium-driver")
        sys.exit(1)

def get_timing_metrics(driver, domain, protocol, domain_id, quic_version=None):
    """
    Visit a website and extract timing metrics.
    
    Args:
        driver: WebDriver instance
        domain: Domain to visit
        protocol: Protocol being used (HTTP/3 or HTTP/2)
        domain_id: ID of the domain
        
    Returns:
        Dictionary with timing metrics
    """
    url = f"https://{domain}" if not domain.startswith('http') else domain
    
    # Initialize result with default values
    result = {
        'id': domain_id,
        'domain': domain,
        'protocol': protocol,
        'responseStart': 0,
        'domInteractive': 0,
        'domComplete': 0,
        'nextHopProtocol': '',
        'successful': False
    }
    
    # Try to load the page with retries (unlimited for HTTP/3 if enabled)
    attempt = 0
    while True:
        try:
            quic_version_info = f" using QUIC version {quic_version}" if quic_version else ""
            print(f"Testing {url} with {protocol}{quic_version_info} (Attempt {attempt+1}/{MAX_RETRIES+1 if not (protocol == 'HTTP/3' and UNLIMITED_HTTP3_RETRIES) else 'unlimited'})...")
            driver.get(url)
            
            # Wait for page to fully load
            time.sleep(2)
            
            # Extract navigation timing metrics
            timing = driver.execute_script("""
                var performance = window.performance;
                var timing = performance.timing;
                var entries = performance.getEntriesByType('navigation');
                
                if (entries && entries.length > 0) {
                    // Navigation Timing API v2
                    return {
                        responseStart: entries[0].responseStart,
                        domInteractive: entries[0].domInteractive,
                        domComplete: entries[0].domComplete,
                        nextHopProtocol: entries[0].nextHopProtocol || ''
                    };
                } else {
                    // Fall back to older Navigation Timing API
                    var navigationStart = timing.navigationStart;
                    return {
                        responseStart: timing.responseStart - navigationStart,
                        domInteractive: timing.domInteractive - navigationStart,
                        domComplete: timing.domComplete - navigationStart,
                        nextHopProtocol: ''
                    };
                }
            """)
            
            # Update result with timing metrics
            if timing:
                result['responseStart'] = timing.get('responseStart', 0)
                result['domInteractive'] = timing.get('domInteractive', 0)
                result['domComplete'] = timing.get('domComplete', 0)
                result['nextHopProtocol'] = timing.get('nextHopProtocol', '')
                result['successful'] = True
            
            # Verify protocol if testing HTTP/3
            if protocol == 'HTTP/3' and 'h3' not in result['nextHopProtocol'].lower():
                print(f"Warning: Expected HTTP/3 but got {result['nextHopProtocol']} for {domain}")
                if UNLIMITED_HTTP3_RETRIES:
                    print(f"Retrying... (attempt {attempt+1})")
                    attempt += 1
                    continue
                elif attempt < MAX_RETRIES:
                    print("Retrying...")
                    attempt += 1
                    continue
            
            # If we got here, we're done with this domain
            break
            
        except (TimeoutException, WebDriverException) as e:
            print(f"Error loading {url}: {str(e)}")
            if protocol == 'HTTP/3' and UNLIMITED_HTTP3_RETRIES:
                print(f"Retrying... (attempt {attempt+1})")
                attempt += 1
                time.sleep(1)
            elif attempt < MAX_RETRIES:
                print("Retrying...")
                attempt += 1
                time.sleep(1)
            else:
                print("Max retries reached, moving on.")
                break
    
    return result

def measure_websites(domains, protocol, output_file):
    """
    Measure timing metrics for a list of domains.
    
    Args:
        domains: List of domain dictionaries with 'id' and 'domain' keys
        protocol: Protocol to test ('HTTP/3' or 'HTTP/2')
        output_file: Output CSV file path
    """
    enable_quic = (protocol == 'HTTP/3')
    
    try:
        # Prepare output file
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADER)
            writer.writeheader()
            
            # Process each domain
            for i, domain_info in enumerate(domains):
                domain_id = domain_info['id']
                domain = domain_info['domain']
                
                # For HTTP/3, try different QUIC versions if needed
                if protocol == 'HTTP/3':
                    result = None
                    for quic_version in QUIC_VERSIONS:
                        # Create a new driver for each QUIC version
                        driver = setup_chrome_driver(enable_quic=True, quic_version=quic_version)
                        try:
                            # Try with this QUIC version
                            print(f"Trying {domain} with QUIC version {quic_version}...")
                            result = get_timing_metrics(driver, domain, protocol, domain_id, quic_version)
                            
                            # If we successfully got HTTP/3, break the loop
                            if 'h3' in result['nextHopProtocol'].lower() and result['successful']:
                                print(f"Successfully connected to {domain} using QUIC version {quic_version}")
                                break
                            
                            # If we didn't get HTTP/3 and unlimited retries is off, move to next version
                            if not UNLIMITED_HTTP3_RETRIES:
                                print(f"Failed to connect with HTTP/3 using QUIC version {quic_version}, trying next version...")
                        finally:
                            # Clean up the driver before trying the next version
                            driver.quit()
                    
                    # If we couldn't connect with any QUIC version, use the last result
                    if not result:
                        print(f"Could not connect to {domain} with any QUIC version")
                        # Create a default failed result
                        result = {
                            'id': domain_id,
                            'domain': domain,
                            'protocol': protocol,
                            'responseStart': 0,
                            'domInteractive': 0,
                            'domComplete': 0,
                            'nextHopProtocol': '',
                            'successful': False
                        }
                else:
                    # For HTTP/2, just use a single driver
                    driver = setup_chrome_driver(enable_quic=False)
                    try:
                        result = get_timing_metrics(driver, domain, protocol, domain_id)
                    finally:
                        driver.quit()
                
                # Write result to CSV
                writer.writerow(result)
                
                # Flush to ensure data is written
                csvfile.flush()
                
                # Print progress
                print(f"Progress: {i+1}/{len(domains)} domains processed")
    except Exception as e:
        print(f"Error in measure_websites: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Measure browser timing for HTTP/3 and HTTP/2')
    parser.add_argument('--protocol', choices=['HTTP/3', 'HTTP/2', 'both'], default='both',
                      help='Protocol to test (HTTP/3, HTTP/2, or both)')
    parser.add_argument('--input', default=INPUT_FILE,
                      help=f'Input CSV file with domains (default: {INPUT_FILE})')
    parser.add_argument('--http3-output', default=OUTPUT_HTTP3,
                      help=f'Output CSV file for HTTP/3 results (default: {OUTPUT_HTTP3})')
    parser.add_argument('--http2-output', default=OUTPUT_HTTP2,
                      help=f'Output CSV file for HTTP/2 results (default: {OUTPUT_HTTP2})')
    parser.add_argument('--max-domains', type=int, default=MAX_WEBSITES,
                      help=f'Maximum number of domains to test (default: {MAX_WEBSITES})')
    parser.add_argument('--unlimited-http3-retries', action='store_true',
                      help='Keep retrying until HTTP/3 connection succeeds')
    
    args = parser.parse_args()
    
    # Set global UNLIMITED_HTTP3_RETRIES based on argument
    global UNLIMITED_HTTP3_RETRIES
    UNLIMITED_HTTP3_RETRIES = args.unlimited_http3_retries
    if UNLIMITED_HTTP3_RETRIES:
        print("Unlimited HTTP/3 retries enabled - will keep trying until HTTP/3 succeeds")
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found.")
        return
    
    # Read domains from input file
    domains = []
    with open(args.input, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            domains.append({
                'id': row['id'],
                'domain': row['domain']
            })
    
    # Limit to max_domains
    domains = domains[:min(len(domains), args.max_domains)]
    
    print(f"Found {len(domains)} domains to test")
    
    # Run measurements based on protocol choice
    if args.protocol in ['HTTP/3', 'both']:
        print(f"\nTesting with HTTP/3 protocol...")
        measure_websites(domains, 'HTTP/3', args.http3_output)
        print(f"HTTP/3 results saved to {args.http3_output}")
    
    if args.protocol in ['HTTP/2', 'both']:
        print(f"\nTesting with HTTP/2 protocol...")
        measure_websites(domains, 'HTTP/2', args.http2_output)
        print(f"HTTP/2 results saved to {args.http2_output}")

if __name__ == "__main__":
    main()
