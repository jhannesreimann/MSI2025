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
        "target": None if resolver["resolve_on_probe"] else domain,
        "af": 4,
        "type": "dns",
        "is_oneoff": False,
        "query_class": "IN",
        "query_type": "A",
        "protocol": "TCP",           # DoT requires TCP
        "tls": True,                  # Enable DNS over TLS
        "port": 853 if not resolver["resolve_on_probe"] else None,  # 853 for DoT, only for external resolvers
        "interval": MEASUREMENT_INTERVAL,
        "resolve_on_probe": resolver["resolve_on_probe"],
        "use_probe_resolver": resolver["resolve_on_probe"],
        "retry": 2,
        "udp_payload_size": 512,
        "description": f"DNS-over-TLS {domain} via {resolver['name']}",
        "query_argument": domain,
    }
    # 'resolver' only set for external resolvers
    if not resolver["resolve_on_probe"] and resolver["address"]:
        definition["resolver"] = resolver["address"]
    # Remove 'port' if None (for local resolver)
    if definition["port"] is None:
        del definition["port"]

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
