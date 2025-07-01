# HTTP/3 vs HTTP/2 Performance Analysis

This project analyzes the performance differences between HTTP/3 (QUIC) and HTTP/2 for websites that support both protocols. It builds on the HTTP/3 adoption measurement from Task 2.

## Prerequisites

- Python 3.6+
- Libraries: `pandas`, `matplotlib`, `csv`, `json`, `subprocess`, `concurrent.futures`
- Internet access (LAN)
- `curl` with HTTP/3 and HTTP/2 support

## Files

- `timing_analysis.py`: Computes start/end times and durations for HTTP/3 request segments
- `plot_timing_boxplots.py`: Creates boxplots for HTTP/3 timing metrics
- `measure_protocols.py`: Measures HTTP/2 performance for domains that support HTTP/3
- `plot_protocol_boxplots.py`: Creates side-by-side boxplots comparing HTTP/2 and HTTP/3
- `plot_delta_boxplots.py`: Analyzes the differences (HTTP/2 - HTTP/3) and creates boxplots of deltas

## Usage

### Step 1: Analyze HTTP/3 Timing Metrics
```bash
python3 timing_analysis.py
python3 plot_timing_boxplots.py
```

### Step 2: Compare HTTP/2 and HTTP/3
```bash
python3 measure_protocols.py
python3 plot_protocol_boxplots.py
```

### Step 3: Analyze Performance Differences
```bash
python3 plot_delta_boxplots.py
```