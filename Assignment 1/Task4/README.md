# Browser Timing Analysis for HTTP/3 vs HTTP/2

This project measures detailed browser timing metrics for websites that support HTTP/3, comparing performance between HTTP/3 and HTTP/2 protocols using Selenium with Chrome.

## Prerequisites

- Python 3.6+
- Selenium WebDriver
- Chrome browser with HTTP/3 support
- ChromeDriver compatible with your Chrome version
- Libraries: `selenium`, `pandas`, `matplotlib`, `numpy`

## Files

- `measure_browser_timing.py`: Uses Selenium to measure browser timing metrics for both HTTP/3 and HTTP/2
- `analyze_browser_timing.py`: Analyzes and visualizes the collected timing data
- `plot_cdf.py`: Generates cumulative distribution function plots of timing metrics
- `http3_top_results.csv`: List of domains that support HTTP/3 (from Task 3)

## Implementation Variants

Two different approaches for enabling HTTP/3 in Chrome are provided:

1. **quic-version approach**: Uses Chrome's `--quic-version` option to try different HTTP/3 QUIC versions (h3-29, h3) until a valid response is received.

2. **origin-to-force-quic-on approach**: Uses Chrome's `--origin-to-force-quic-on=domain:port` option to force QUIC for specific origins, which was suggested in the Moodle Forum post.

## Metrics Collected

The scripts collect the following browser timing metrics as defined in the Navigation Timing API:

1. **responseStart**: Time when the first byte of the response is received
2. **domInteractive**: Time when the browser has parsed the HTML and constructed the DOM
3. **domComplete**: Time when the browser has completed loading all resources and processing

## Usage

### Step 1: Measure Browser Timing

```bash
python3 measure_browser_timing.py
```

Options:
- `--protocol`: Choose which protocol to test (`HTTP/3`, `HTTP/2`, or `both`)
- `--input`: Input CSV file with domains (default: `http3_top_results.csv`)
- `--http3-output`: Output file for HTTP/3 results (default: `browser_timing_http3.csv`)
- `--http2-output`: Output file for HTTP/2 results (default: `browser_timing_http2.csv`)
- `--max-domains`: Maximum number of domains to test (default: 1000)
- `--unlimited-http3-retries`: Keep retrying until HTTP/3 connection succeeds

Additional options for each approach:

**quic-version approach**:
- Uses different QUIC versions (h3-29, h3) to find a working HTTP/3 connection

**origin-to-force-quic-on approach**:
- `--quic-port`: Port number for QUIC connections (default: 443)

### Step 2: Analyze Results

```bash
python3 analyze_browser_timing.py
```

This will:
1. Load and clean the data from both HTTP/3 and HTTP/2 measurements
2. Generate side-by-side boxplots comparing the protocols
3. Calculate delta statistics (HTTP/2 - HTTP/3)
4. Save results to CSV and PNG files

### Step 3: Generate CDF Plots

```bash
python3 plot_cdf.py
```

This will:
1. Generate cumulative distribution function (CDF) plots for timing metrics
2. Compare the distribution of timing values between HTTP/3 and HTTP/2
3. Save the CDF plots to PNG files

## Output Files

- `browser_timing_http3.csv`: Raw timing data for HTTP/3
- `browser_timing_http2.csv`: Raw timing data for HTTP/2
- `browser_timing_comparison.png`: Side-by-side boxplots comparing HTTP/3 and HTTP/2
- `browser_timing_delta.png`: Boxplots of the deltas (HTTP/2 - HTTP/3)
- `browser_timing_stats.csv`: Statistical summary of the comparison
- `browser_timing_cdf.png`: CDF plots comparing HTTP/3 and HTTP/2 timing distributions

## References

- [Selenium Documentation](https://www.selenium.dev/)
- [Navigation Timing API](https://www.w3.org/TR/navigation-timing-2/)
- [Resource Timing API](https://www.w3.org/TR/resource-timing-2/)
- [Chrome Command Line Switches](https://peter.sh/experiments/chromium-command-line-switches/)

## Implementation Notes

The two implementation approaches for enabling HTTP/3 in Chrome were tested:

1. First approach used Chrome's `--quic-version` option, trying different HTTP/3 QUIC versions until a valid response was received.

2. Second approach (based on Moodle Forum post) used Chrome's `--origin-to-force-quic-on=www.example.org:portnumber` option, which forces QUIC for specific origins.

Both approaches successfully enabled HTTP/3 connections, but they use different mechanisms to achieve this, which may affect the connection behavior and performance measurements.
