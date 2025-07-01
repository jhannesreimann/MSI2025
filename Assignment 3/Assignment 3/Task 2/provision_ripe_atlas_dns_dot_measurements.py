import os
import requests
import time
import csv
from collections import Counter, defaultdict

API_KEY = os.getenv("RIPE_ATLAS_API_KEY")
HEADERS = {"Authorization": f"Key {API_KEY}"}
BASE_URL = "https://atlas.ripe.net/api/v2"

GERMANY_COUNTRY_CODE = "DE"
TOP_N_ASNS = 40
PROBES_PER_ASN = 25
DOMAINS = ["google.com", "facebook.com", "amazon.com", "wikipedia.org", "baidu.com"]
RESOLVERS = [
    {"name": "local", "address": None, "resolve_on_probe": True},
    {"name": "google", "address": "8.8.8.8", "resolve_on_probe": False},
    {"name": "q9", "address": "9.9.9.9", "resolve_on_probe": False},
    {"name": "cloudflare", "address": "1.1.1.1", "resolve_on_probe": False},
]
MEASUREMENT_INTERVAL = 21600  # 6 hours in seconds
MEASUREMENT_COUNT = 4         # 4 runs in a day


def load_probe_ids_from_csv(filename):
    probe_ids = []
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            probe_ids.append(int(row['probe_id']))
    return probe_ids


def create_measurement(probe_ids, resolver, domain):
    """Create a DNS-over-TLS measurement for the given probes and resolver."""
    definition = {
        "af": 4,
        "query_class": "IN",
        "query_type": "A",
        "protocol": "TCP",  # DoT requires TCP
        "tls": True,  # Enable DNS over TLS
        "udp_payload_size": 512, # This is typically for UDP, but often included. Friend's code has it.
        "retry": 0,
        "query_argument": domain,
        "description": f"DNS-over-TLS {domain} via {resolver['name']}",
        "interval": MEASUREMENT_INTERVAL,
        "type": "dns",
        "is_oneoff": False,
        "resolve_on_probe": False,  # Legacy parameter, set to False as in the example
        "use_probe_resolver": resolver["resolve_on_probe"],  # This is the controlling parameter
        "use_macros": False,
        "skip_dns_check": False,
        "include_qbuf": False,
        "include_abuf": True,
        "prepend_probe_id": False,
        "set_rd_bit": True,
        "set_do_bit": False, # For DoT, DNSSEC is handled by the TLS channel, so DO bit might be less relevant or handled differently.
        "set_cd_bit": False,
        "timeout": 5000,
        "set_nsid_bit": True, # NSID is less common with DoT but friend's code has it.
    }

    if resolver["resolve_on_probe"]:
        # For local resolver (use_probe_resolver is True), 'target' is not needed.
        definition["target"] = None
    else:
        # For specific external resolver (use_probe_resolver is False)
        if resolver["address"]:
            definition["target"] = resolver["address"]
        # The port is not set explicitly, as RIPE Atlas defaults to 853 for DoT.

    measurement = {
        "definitions": [definition],
        "probes": [{
            "requested": len(probe_ids),
            "type": "probes",
            "value": ",".join(map(str, probe_ids)),
        }],
        "is_oneoff": False,
        "start_time": int(time.time()),
        "stop_time": int(time.time()) + 24 * 3600,
    }
    try:
        resp = requests.post(f"{BASE_URL}/measurements/", json=measurement, headers=HEADERS)
        resp.raise_for_status()
        return resp.json()["measurements"][0]
    except requests.exceptions.HTTPError as e:
        print(f"Measurement creation failed for {resolver['name']} {domain}.")
        if e.response is not None:
            print("API response:", e.response.text)
        raise


def main():
    # load exactly the same probe ids as for UDP from the mapping file
    selected_probe_ids = load_probe_ids_from_csv("../Task 1/probe_asn_mapping.csv")

    measurement_records = []
    for resolver in RESOLVERS:
        for domain in DOMAINS:
            try:
                m_id = create_measurement(selected_probe_ids, resolver, domain)
                measurement_records.append({
                    "measurement_id": m_id,
                    "resolver": resolver["name"],
                    "domain": domain,
                })
                print(f"Created DoT measurement {m_id} for {resolver['name']} {domain}")
                time.sleep(1)  # avoid rate limits
            except Exception as e:
                print(f"Failed to create DoT measurement for {resolver['name']} {domain}: {e}")
                time.sleep(10)

    # Save measurement info for DoT
    with open("measurement_ids_dot.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["measurement_id", "resolver", "domain"])
        writer.writeheader()
        writer.writerows(measurement_records)

if __name__ == "__main__":
    main()
