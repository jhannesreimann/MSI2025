"""
OONI Data Cleaning Utilities

This module provides functions for cleaning and processing OONI measurement data,
with special attention to OONI-specific data quality issues and anomaly detection.
"""

import pandas as pd
import numpy as np
import re
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm


# ========== BASIC DATA CLEANING FUNCTIONS ==========

def convert_null_indicators(chunk):
    """
    Convert special null indicators (\N) to NaN for consistent processing
    """
    return chunk.replace('\\N', np.nan)


def handle_missing_values(chunk, columns_to_drop, categorical_columns_to_fill, 
                          numerical_columns_to_fill, categorical_fill_values=None):
    """
    Process a chunk to handle missing values according to predetermined strategies
    
    Args:
        chunk: pandas DataFrame chunk
        columns_to_drop: list of columns to drop
        categorical_columns_to_fill: list of categorical columns to fill
        numerical_columns_to_fill: list of numerical columns to fill
        categorical_fill_values: dict of {column_name: fill_value} (if None, will use 'unknown')
    
    Returns:
        Processed DataFrame chunk
    """
    # Make a copy to avoid modifying the original
    processed_chunk = chunk.copy()
    
    # 1. Drop columns with high missing rates
    processed_chunk = processed_chunk.drop(columns=columns_to_drop, errors='ignore')
    
    # 2. Fill missing values in categorical columns
    if categorical_fill_values is None:
        categorical_fill_values = {col: 'unknown' for col in categorical_columns_to_fill}
        
    for col in categorical_columns_to_fill:
        if col in processed_chunk.columns:
            processed_chunk[col] = processed_chunk[col].fillna(categorical_fill_values[col])
    
    # 3. Fill missing values in numerical columns with median
    for col in numerical_columns_to_fill:
        if col in processed_chunk.columns:
            # Convert to numeric first to ensure proper handling
            processed_chunk[col] = pd.to_numeric(processed_chunk[col], errors='coerce')
            # Use the median of the current chunk
            median_value = processed_chunk[col].median()
            if pd.notnull(median_value):
                processed_chunk[col] = processed_chunk[col].fillna(median_value)
    
    return processed_chunk


def normalize_country_codes(chunk):
    """
    Standardize country codes in the dataset
    
    This ensures all country codes are uppercase and follow ISO 3166-1 alpha-2 standard
    """
    country_columns = [
        'probe_cc', 'probe_as_cc', 'resolver_cc', 
        'resolver_as_cc', 'ip_as_cc', 'ip_cc'
    ]
    
    for col in country_columns:
        if col in chunk.columns:
            # Convert to uppercase
            chunk[col] = chunk[col].str.upper()
            
            # Handle any known non-standard codes (examples)
            # Add mappings as needed based on data inspection
            code_mapping = {
                'UK': 'GB',  # United Kingdom to Great Britain standard code
                'UNKNOWN': np.nan,
            }
            
            chunk[col] = chunk[col].replace(code_mapping)
    
    return chunk


def normalize_test_names(chunk):
    """
    Standardize test names and types for consistency
    """
    if 'test_name' in chunk.columns:
        # Convert to lowercase and remove special characters
        chunk['test_name'] = chunk['test_name'].str.lower()
        
        # Map variations to standard names (examples)
        test_mapping = {
            'web_connectivity': 'web_connectivity',
            'web connectivity': 'web_connectivity',
            'http_requests': 'http_requests',
            'http requests': 'http_requests',
            'dns_consistency': 'dns_consistency',
            'dns consistency': 'dns_consistency',
            'facebook_messenger': 'facebook_messenger',
            'fb_messenger': 'facebook_messenger',
            'facebook messenger': 'facebook_messenger',
            # Add more mappings as needed
        }
        
        chunk['test_name'] = chunk['test_name'].replace(test_mapping)
    
    return chunk


def normalize_network_types(chunk):
    """
    Standardize network_type values
    """
    if 'network_type' in chunk.columns:
        # Convert to lowercase
        chunk['network_type'] = chunk['network_type'].str.lower()
        
        # Map variations to standard types
        network_mapping = {
            'wifi': 'wifi',
            'wi-fi': 'wifi',
            'wlan': 'wifi',
            'mobile': 'mobile',
            'cellular': 'mobile',
            '3g': 'mobile',
            '4g': 'mobile',
            '5g': 'mobile',
            'lte': 'mobile',
            'ethernet': 'ethernet',
            'lan': 'ethernet',
            'unknown': 'unknown',
            # Add more mappings as needed
        }
        
        chunk['network_type'] = chunk['network_type'].replace(network_mapping)
    
    return chunk


def normalize_categorical_variables(chunk):
    """Apply all normalization functions to standardize categorical variables"""
    chunk = convert_null_indicators(chunk)
    chunk = normalize_country_codes(chunk)
    chunk = normalize_test_names(chunk)
    chunk = normalize_network_types(chunk)
    return chunk


# ========== OONI-SPECIFIC DATA QUALITY FUNCTIONS ==========

def convert_timestamps(chunk):
    """
    Convert timestamp columns to proper datetime format
    """
    timestamp_cols = [
        'measurement_start_time', 
        'tls_end_entity_certificate_not_valid_after',
        'tls_end_entity_certificate_not_valid_before'
    ]
    
    for col in timestamp_cols:
        if col in chunk.columns:
            chunk[col] = pd.to_datetime(chunk[col], errors='coerce')
    
    return chunk


def convert_numeric_columns(chunk):
    """
    Convert numerical columns to proper numeric type
    """
    # Identify columns with timing measurements (_t suffix)
    timing_cols = [col for col in chunk.columns if col.endswith('_t')]
    
    # Add other known numeric columns
    numeric_cols = timing_cols + [
        'probe_asn', 'resolver_asn', 'ip_asn', 'dns_answer_asn',
        'http_response_body_length', 'http_response_status_code',
        'http_request_body_length', 'tls_certificate_chain_length',
        'tls_handshake_read_bytes', 'tls_handshake_write_bytes'
    ]
    
    # Convert each column to numeric
    for col in numeric_cols:
        if col in chunk.columns:
            chunk[col] = pd.to_numeric(chunk[col], errors='coerce')
    
    return chunk


def flag_anomalies(chunk):
    """
    Flag potential anomalies in OONI data
    
    Adds boolean flag columns to identify records with unusual or suspicious values
    """
    # Initialize flags dictionary
    flags = {}
    
    # 1. Flag bogon IPs (important for censorship detection)
    if 'ip_is_bogon' in chunk.columns:
        flags['bogon_ip'] = chunk['ip_is_bogon'] == 1
    
    # 2. Flag country code mismatches (from GeoIP mismatch notebook)
    if 'probe_cc' in chunk.columns and 'ip_cc' in chunk.columns:
        cc_cols = [col for col in chunk.columns if col.endswith('_cc')]
        
        # If we have multiple country codes, check for mismatches
        if len(cc_cols) >= 2:
            # First convert to proper types
            for col in cc_cols:
                if col in chunk.columns:
                    chunk[col] = chunk[col].astype(str).str.upper()
            
            # Create flag for any country mismatch (probe_cc vs ip_cc most important)
            flags['geo_mismatch'] = (
                (chunk['probe_cc'] != chunk['ip_cc']) & 
                (chunk['probe_cc'].notna()) & 
                (chunk['ip_cc'].notna())
            )
    
    # 3. Flag software/platform inconsistencies (from Unusual Combinations notebook)
    if 'software_name' in chunk.columns and 'platform' in chunk.columns:
        # Android software on non-Android platform
        flags['android_platform_mismatch'] = (
            chunk['software_name'].str.contains('android', case=False, na=False) & 
            ~chunk['platform'].str.contains('android', case=False, na=False) & 
            (chunk['platform'].notna())
        )
        
        # iOS software on non-iOS platform
        flags['ios_platform_mismatch'] = (
            chunk['software_name'].str.contains('ios', case=False, na=False) & 
            ~chunk['platform'].str.contains('ios', case=False, na=False) & 
            (chunk['platform'].notna())
        )
    
    # 4. Flag architecture inconsistencies
    if 'platform' in chunk.columns and 'architecture' in chunk.columns:
        # Mobile platforms with unexpected architectures
        flags['mobile_arch_mismatch'] = (
            (
                (chunk['platform'].str.contains('android|ios', case=False, na=False)) & 
                (chunk['architecture'].str.contains('amd64|x86_64', case=False, na=False)) &
                (chunk['architecture'].notna())
            )
        )
    
    # 5. Flag timing anomalies
    if 'dns_t' in chunk.columns:
        # Unusually fast DNS lookups (< 1ms) could indicate measurement issues
        flags['unusually_fast_dns'] = (
            (chunk['dns_t'] < 0.001) & (chunk['dns_t'].notna())
        )
    
    if 'tcp_t' in chunk.columns:
        # Unusually fast TCP connections
        flags['unusually_fast_tcp'] = (
            (chunk['tcp_t'] < 0.001) & (chunk['tcp_t'].notna())
        )
    
    # 6. Flag TLS anomalies
    if 'tls_cipher_suite' in chunk.columns and 'tls_version' in chunk.columns:
        # Flag NULL cipher suites (could indicate censorship or MITM)
        flags['null_cipher'] = chunk['tls_cipher_suite'].str.contains('NULL', na=False)
    
    # 7. Flag HTTP status code anomalies
    if 'http_response_status_code' in chunk.columns:
        # Non-standard status codes
        flags['unusual_status_code'] = ~chunk['http_response_status_code'].isin([
            200, 201, 204, 206, 301, 302, 303, 304, 307, 308, 
            400, 401, 403, 404, 405, 406, 408, 410, 429, 
            500, 501, 502, 503, 504
        ])
    
    # Add all flags to the DataFrame
    for flag_name, flag_values in flags.items():
        chunk[f'flag_{flag_name}'] = flag_values
    
    # Add an overall anomaly flag
    flag_cols = [f'flag_{name}' for name in flags.keys()]
    if flag_cols:
        chunk['has_anomaly'] = chunk[flag_cols].any(axis=1)
    
    return chunk


def summarize_anomalies(chunk):
    """
    Print a summary of flagged anomalies in the data
    """
    flag_cols = [col for col in chunk.columns if col.startswith('flag_')]
    
    if flag_cols:
        print("\n===== Anomaly Summary =====")
        for col in flag_cols:
            flag_count = chunk[col].sum()
            flag_percent = (flag_count / len(chunk)) * 100
            print(f"{col}: {flag_count} records ({flag_percent:.2f}%)")
        
        # Print overall anomaly rate
        if 'has_anomaly' in chunk.columns:
            overall = chunk['has_anomaly'].sum()
            overall_percent = (overall / len(chunk)) * 100
            print(f"\nTotal records with anomalies: {overall} ({overall_percent:.2f}%)")
    
    return chunk


# ========== MAIN PROCESSING FUNCTIONS ==========

def process_chunk(chunk, columns_to_drop=None, categorical_cols_to_fill=None, 
                 numerical_cols_to_fill=None, flag_anomalies_only=False):
    """
    Apply all cleaning steps to a chunk of OONI data
    
    Args:
        chunk: pandas DataFrame chunk
        columns_to_drop: list of columns to drop
        categorical_cols_to_fill: list of categorical columns to fill
        numerical_cols_to_fill: list of numerical columns to fill
        flag_anomalies_only: if True, only flag anomalies without dropping/filling
    
    Returns:
        Processed DataFrame chunk
    """
    # Initialize empty lists if None
    if columns_to_drop is None:
        columns_to_drop = []
    if categorical_cols_to_fill is None:
        categorical_cols_to_fill = []
    if numerical_cols_to_fill is None:
        numerical_cols_to_fill = []
    
    # 1. Basic normalization
    chunk = normalize_categorical_variables(chunk)
    
    # 2. Convert data types
    chunk = convert_timestamps(chunk)
    chunk = convert_numeric_columns(chunk)
    
    # 3. Flag anomalies
    chunk = flag_anomalies(chunk)
    
    # 4. Handle missing values (if not in flag-only mode)
    if not flag_anomalies_only:
        chunk = handle_missing_values(
            chunk, 
            columns_to_drop, 
            categorical_cols_to_fill,
            numerical_cols_to_fill
        )
    
    return chunk


def process_full_dataset(input_file, output_file, chunk_size=10000,
                        columns_to_drop=None, categorical_cols_to_fill=None,
                        numerical_cols_to_fill=None, flag_anomalies_only=False,
                        remove_anomalies=False):
    """
    Process the entire dataset in chunks and save to a new file
    
    Args:
        input_file: Path to the original CSV file
        output_file: Path to save the cleaned CSV file
        chunk_size: Number of rows to process at once
        columns_to_drop: list of columns to drop
        categorical_cols_to_fill: list of categorical columns to fill
        numerical_cols_to_fill: list of numerical columns to fill
        flag_anomalies_only: If True, only flag anomalies without other cleaning
        remove_anomalies: If True, filter out records flagged as anomalies
    """
    # Initialize counters
    total_rows_processed = 0
    chunks_processed = 0
    total_anomalies = 0
    
    # Process the file in chunks
    for i, chunk in enumerate(tqdm(pd.read_csv(input_file, chunksize=chunk_size))):
        # Apply all processing steps
        processed_chunk = process_chunk(
            chunk,
            columns_to_drop,
            categorical_cols_to_fill,
            numerical_cols_to_fill,
            flag_anomalies_only
        )
        
        # Count anomalies
        if 'has_anomaly' in processed_chunk.columns:
            anomalies_in_chunk = processed_chunk['has_anomaly'].sum()
            total_anomalies += anomalies_in_chunk
            
            # Filter out anomalies if requested
            if remove_anomalies:
                processed_chunk = processed_chunk[~processed_chunk['has_anomaly']]
        
        # Save the chunk (append if not the first chunk)
        if i == 0:
            processed_chunk.to_csv(output_file, index=False, mode='w')
        else:
            processed_chunk.to_csv(output_file, index=False, mode='a', header=False)
        
        # Update counters
        total_rows_processed += len(chunk)
        chunks_processed += 1
        
        # Print progress every 10 chunks
        if chunks_processed % 10 == 0:
            print(f"Processed {chunks_processed} chunks ({total_rows_processed:,} rows)")
    
    # Print summary
    print(f"\nCompleted processing {total_rows_processed:,} rows in {chunks_processed} chunks")
    if 'has_anomaly' in processed_chunk.columns:
        anomaly_percent = (total_anomalies / total_rows_processed) * 100
        print(f"Found {total_anomalies:,} anomalies ({anomaly_percent:.2f}%)")
        if remove_anomalies:
            print(f"Removed anomalies from output file")
    print(f"Cleaned data saved to: {output_file}")


# ========== VISUALIZATION FUNCTIONS ==========

def visualize_anomalies(chunk):
    """
    Create visualizations to understand anomalies in the data
    """
    flag_cols = [col for col in chunk.columns if col.startswith('flag_')]
    
    if not flag_cols:
        print("No anomaly flags found in the data")
        return
    
    # 1. Plot anomaly distribution by flag type
    flag_counts = chunk[flag_cols].sum().sort_values(ascending=False)
    
    plt.figure(figsize=(12, 6))
    sns.barplot(x=flag_counts.index, y=flag_counts.values)
    plt.title('Distribution of Anomalies by Type')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()
    
    # 2. If country data exists, plot geographic distribution of anomalies
    if 'probe_cc' in chunk.columns and 'has_anomaly' in chunk.columns:
        # Count anomalies by country
        anomalies_by_country = chunk[chunk['has_anomaly']].groupby('probe_cc').size()
        top_countries = anomalies_by_country.sort_values(ascending=False).head(15)
        
        plt.figure(figsize=(12, 6))
        sns.barplot(x=top_countries.index, y=top_countries.values)
        plt.title('Top Countries with Anomalies')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    
    # 3. Plot anomalies by software and platform if available
    if 'software_name' in chunk.columns and 'has_anomaly' in chunk.columns:
        # Count anomalies by software
        anomalies_by_software = chunk[chunk['has_anomaly']].groupby('software_name').size()
        top_software = anomalies_by_software.sort_values(ascending=False).head(10)
        
        plt.figure(figsize=(12, 6))
        sns.barplot(x=top_software.index, y=top_software.values)
        plt.title('Anomalies by Software')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.show()


def visualize_timing_distributions(chunk):
    """
    Create visualizations of timing measurements
    """
    # Identify timing columns
    timing_cols = [col for col in chunk.columns if col.endswith('_t') 
                  and chunk[col].dtype in [np.float64, np.int64]]
    
    if not timing_cols:
        print("No timing columns found in the data")
        return
    
    # Set up the figure
    n_cols = min(2, len(timing_cols))
    n_rows = (len(timing_cols) + n_cols - 1) // n_cols
    
    plt.figure(figsize=(14, n_rows * 4))
    
    # Plot each timing distribution
    for i, col in enumerate(timing_cols):
        plt.subplot(n_rows, n_cols, i+1)
        
        # Filter extreme outliers for better visualization
        q1 = chunk[col].quantile(0.25)
        q3 = chunk[col].quantile(0.75)
        iqr = q3 - q1
        upper_bound = q3 + 1.5 * iqr
        
        filtered_data = chunk[chunk[col] <= upper_bound][col].dropna()
        
        # Create distribution plot
        sns.histplot(filtered_data, kde=True)
        plt.title(f'Distribution of {col}')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Count')
    
    plt.tight_layout()
    plt.show()


# ========== EXAMPLE USAGE ==========

def example_usage():
    """
    Example of how to use these functions
    """
    # Define sample parameters
    input_file = 'ooni_measurements.csv'  # Replace with your input file
    output_file = 'cleaned_ooni_data.csv'  # Output file
    
    # Example columns to handle
    columns_to_drop = []  # No columns to drop by default
    
    categorical_columns_to_fill = [
        'resolver_ip', 'resolver_cc', 'resolver_as_org_name', 
        'resolver_as_cc', 'tls_server_name', 'tls_version', 
        'tls_cipher_suite', 'dns_answer_as_org_name'
    ]
    
    numerical_columns_to_fill = []  # Add any numerical columns that need filling
    
    # Process the data
    process_full_dataset(
        input_file, 
        output_file, 
        chunk_size=10000,
        columns_to_drop=columns_to_drop, 
        categorical_cols_to_fill=categorical_columns_to_fill,
        numerical_cols_to_fill=numerical_columns_to_fill,
        flag_anomalies_only=False,  # Apply full cleaning
        remove_anomalies=False  # Keep anomalies but flag them
    )


if __name__ == "__main__":
    # This section will only run if the script is executed directly
    print("OONI Data Cleaner")
    print("To use this module, import it and call the functions as needed.")
    print("For a usage example, run example_usage()")
