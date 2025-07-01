# HTTP/3 Adoption Measurement

This project measures the adoption of HTTP/3 (QUIC) among the top 10k domains from the Tranco list.

## Prerequisites

- Python 3.6+
- Standard Python libraries: `urllib`, `zipfile`, `csv`, `argparse`, `matplotlib`, `pandas`
- Internet access (LAN)
- `curl` with HTTP/3 support

## Files

- `prepare_domains.py`: Downloads the Tranco Top-1M list, extracts the top 10k domains, prepends `www.` to each domain, and creates `domains.csv`.
- `measure_http3.py`: Tests HTTP/3 support for domains in `domains.csv` using `curl --http3` and outputs `http3_results.csv`.
- `asn_analysis.py`: Analyzes the ASNs (Autonomous System Numbers) of HTTP/3-supporting domains using Team Cymru’s whois service.
- `asn_visualization.py`: Visualizes ASN distribution data from `asn_http3_websites.csv` and `http3_results.csv` using Matplotlib.

## Usage

### prepare_domains.py

Example:
```bash
python3 prepare_domains.py
```

### measure_http3.py

Example:
```bash
python3 measure_http3.py
```

### asn_analysis.py

Example:
```bash
python3 asn_analysis.py [INPUT_HTTP3] [OUTPUT_ASN]
```
Options:
- Input CSV file with HTTP/3 results (default: `http3_results.csv`).
- Output CSV file for ASN analysis (default: `asn_http3_websites.csv`).

### asn_visualization.py

Example:
```bash
python3 asn_visualization.py [INPUT_FILE] [OUTPUT_PNG] [TOP_N]
```
Options:
- Input CSV file with ASN analysis (default: `asn_http3_websites.csv`).
- Output image file for the plot (default: `asn_http3_distribution.png`).
- Number of top ASNs to display (default: 15).