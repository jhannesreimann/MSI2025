#!/usr/bin/env python3
import csv
import sys
from collections import Counter
import subprocess
import socket
import ipaddress
import os
from concurrent.futures import ThreadPoolExecutor

# Configuration
INPUT_FILE = 'http3_results.csv'  # Your existing results from the curl task
OUTPUT_FILE = 'asn_http3_websites.csv'  # Output file for ASN analysis
BATCH_SIZE = 100  # Number of IPs to process in each batch for whois method
MAX_WORKERS = 20  # Maximum number of parallel workers

def get_asn_using_whois(ip):
    """
    Gets the ASN for an IP address using the whois command.
    Much faster than online APIs.
    
    Args:
        ip (str): The IP address to look up
        
    Returns:
        str: ASN number (format: "ASxxxxx") or empty string if not found
    """
    try:
        # Validate IP
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return ""
            
        # Run whois command
        result = subprocess.run(['whois', ip], capture_output=True, text=True, timeout=5)
        output = result.stdout
        
        # Look for ASN in the output
        for line in output.split('\n'):
            line = line.strip().lower()
            if 'origin' in line or 'originas' in line or 'asn' in line:
                parts = line.split(':')
                if len(parts) > 1:
                    value = parts[1].strip()
                    # Extract just the ASN number
                    if value.lower().startswith('as'):
                        return value.upper()
                    else:
                        return f"AS{value}"
        return ""
    except Exception as e:
        return ""

def get_asn_using_cymru(ip):
    """
    Gets the ASN for an IP address using Team Cymru's whois service.
    Very fast and reliable.
    
    Args:
        ip (str): The IP address to look up
        
    Returns:
        str: ASN number (format: "ASxxxxx") or empty string if not found
    """
    try:
        # Validate IP
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return ""
            
        # Format the query for Team Cymru's whois service
        query = f"-v {ip}"
        
        # Connect to Team Cymru's whois service
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("whois.cymru.com", 43))
        s.send(query.encode() + b'\r\n')
        
        # Receive and process the response
        response = b""
        while True:
            data = s.recv(1024)
            if not data:
                break
            response += data
        s.close()
        
        # Parse the response
        response_text = response.decode('utf-8', errors='ignore')
        lines = response_text.strip().split('\n')
        if len(lines) < 2:
            return ""
            
        # The second line contains the ASN
        parts = lines[1].strip().split('|')
        if len(parts) >= 1:
            asn = parts[0].strip()
            if asn and asn.isdigit():
                return f"AS{asn}"
        return ""
    except Exception as e:
        return ""

def batch_process_ips(ips):
    """
    Process a batch of IP addresses using bgptools bulk lookup.
    This is the fastest method for bulk lookups.
    
    Args:
        ips (list): List of IP addresses to look up
        
    Returns:
        dict: Dictionary mapping IPs to ASNs
    """
    results = {}
    
    # Use parallel processing for the lookups
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Use Team Cymru's service for each IP
        future_to_ip = {executor.submit(get_asn_using_cymru, ip): ip for ip in ips}
        for future in future_to_ip:
            ip = future_to_ip[future]
            try:
                asn = future.result()
                results[ip] = asn
            except Exception:
                results[ip] = ""
    
    return results

def analyze_asns(input_file, output_file):
    """
    Analyzes HTTP/3 results to count websites per ASN.
    
    Args:
        input_file (str): Path to the HTTP/3 results CSV file
        output_file (str): Path to save the ASN analysis results
    """
    print(f"Reading data from {input_file}...")
    
    # Collect all the IP addresses to look up
    http3_ips = []
    domains_by_ip = {}
    total_domains = 0
    http3_supported = 0
    
    # Read the CSV file with HTTP/3 measurement results
    with open(input_file, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # Check if required columns exist
        required_columns = ['supports_http3', 'remote_ip']
        for col in required_columns:
            if col not in reader.fieldnames:
                print(f"Error: Required column '{col}' not found in {input_file}")
                return
        
        # Process each row
        for row in reader:
            total_domains += 1
            
            # Only analyze domains that support HTTP/3
            if row['supports_http3'].lower() == 'true':
                http3_supported += 1
                ip = row['remote_ip']
                
                if not ip:
                    continue
                
                # Store the IP for lookup
                if ip not in http3_ips:
                    http3_ips.append(ip)
                
                # Map IP to domains (for counting later)
                if ip not in domains_by_ip:
                    domains_by_ip[ip] = []
                domains_by_ip[ip].append(row.get('domain', ''))
    
    print(f"Found {http3_supported} domains with HTTP/3 support across {len(http3_ips)} unique IP addresses")
    print(f"Starting ASN lookups...")
    
    # Process IPs in batches for efficiency
    ip_to_asn = {}
    for i in range(0, len(http3_ips), BATCH_SIZE):
        batch = http3_ips[i:i+BATCH_SIZE]
        print(f"Processing batch {i//BATCH_SIZE + 1}/{(len(http3_ips)+BATCH_SIZE-1)//BATCH_SIZE} ({len(batch)} IPs)")
        
        # Get ASNs for this batch
        batch_results = batch_process_ips(batch)
        ip_to_asn.update(batch_results)
    
    # Count websites per ASN
    asn_counts = Counter()
    for ip, asn in ip_to_asn.items():
        if asn:
            # Count each domain with this IP
            asn_counts[asn] += len(domains_by_ip.get(ip, []))
    
    # Sort ASNs by count in descending order
    sorted_asns = sorted(asn_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Write ASN counts to CSV
    print(f"Writing results to {output_file}...")
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['asn', 'num_http3_websites'])
        for asn, count in sorted_asns:
            writer.writerow([asn, count])
    
    # Calculate percentage of successful lookups
    success_rate = sum(1 for ip, asn in ip_to_asn.items() if asn) / len(http3_ips) * 100 if http3_ips else 0
    
    # Display top ASNs
    print(f"\nASN lookup success rate: {success_rate:.2f}%")
    print("\nTop 10 ASNs hosting HTTP/3 websites:")
    total_classified = sum(count for _, count in sorted_asns)
    for i, (asn, count) in enumerate(sorted_asns[:10], 1):
        print(f"{i}. {asn}: {count} websites ({count/http3_supported*100:.2f}%)")
        
    print(f"\nFull results saved to {output_file}")

def main():
    """
    Main function to perform ASN analysis on existing HTTP/3 measurement results.
    """
    # Check if custom input file was provided
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = INPUT_FILE
    
    # Check if custom output file was provided
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        output_file = OUTPUT_FILE
    
    try:
        analyze_asns(input_file, output_file)
    except FileNotFoundError:
        print(f"ERROR: Input file {input_file} not found.")
        print(f"Usage: python {sys.argv[0]} [input_csv_file] [output_csv_file]")
        sys.exit(1)
    except Exception as e:
        print(f"Error during ASN analysis: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()