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

def fetch_probes():
    """Fetch all connected probes in Germany."""
    probes = []
    url = f"{BASE_URL}/probes/?country_code={GERMANY_COUNTRY_CODE}&status_name=Connected"
    while url:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        probes.extend(data["results"])
        url = data["next"]
    return probes

def get_top_asns(probes, top_n):
    """Return top N ASNs by probe count."""
    asn_counts = Counter([p["asn_v4"] for p in probes if p["asn_v4"]])
    return [asn for asn, _ in asn_counts.most_common(top_n)]

def select_probes_by_asn(probes, asns, per_asn):
    """Select up to per_asn probes per ASN."""
    probes_by_asn = defaultdict(list)
    for p in probes:
        asn = p["asn_v4"]
        if asn in asns:
            probes_by_asn[asn].append(p)
    selected = []
    mapping = []
    for asn in asns:
        chosen = probes_by_asn[asn][:per_asn]
        selected.extend([p["id"] for p in chosen])
        mapping.extend([(p["id"], asn) for p in chosen])
    return selected, mapping

def create_measurement(probe_ids, resolver, domain):
    """Create a DNS measurement for the given probes and resolver."""
    # For local resolver: target=None, for external resolver: target=domain
    definition = {
        "af": 4,
        "query_class": "IN",
        "query_type": "A",
        "protocol": "UDP",
        "udp_payload_size": 512,
        "retry": 0,
        "query_argument": domain,
        "description": f"DNS {domain} via {resolver['name']}",
        "interval": MEASUREMENT_INTERVAL,
        "type": "dns",  # Part of RIPE Atlas measurement definition
        "is_oneoff": False,  # Part of RIPE Atlas measurement definition
        "resolve_on_probe": False,  # Legacy parameter, set to False as in the example
        "use_probe_resolver": resolver["resolve_on_probe"],  # This is the controlling parameter
        "use_macros": False,
        "skip_dns_check": False,
        "include_qbuf": False,
        "include_abuf": True,
        "prepend_probe_id": False,
        "set_rd_bit": True,
        "set_do_bit": False,
        "set_cd_bit": False,
        "timeout": 5000,
        "set_nsid_bit": True,
    }

    # Set target correctly based on whether a specific resolver is used
    if resolver["resolve_on_probe"]:
        # For local resolver (use_probe_resolver is True), 'target' is not needed or should be None.
        definition["target"] = None
    else:
        # For specific external resolver (use_probe_resolver is False)
        if resolver["address"]:
            definition["target"] = resolver["address"]

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
    probes = fetch_probes()
    asns = get_top_asns(probes, TOP_N_ASNS)
    selected_probe_ids, probe_asn_mapping = select_probes_by_asn(probes, asns, PROBES_PER_ASN)

    # Save probe-ASN mapping
    with open("probe_asn_mapping.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["probe_id", "asn_v4"])
        writer.writerows(probe_asn_mapping)

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
                print(f"Created measurement {m_id} for {resolver['name']} {domain}")
                time.sleep(1)  # avoid rate limits
            except Exception as e:
                print(f"Failed to create measurement for {resolver['name']} {domain}: {e}")
                time.sleep(10)

    # Save measurement info
    with open("measurement_ids.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["measurement_id", "resolver", "domain"])
        writer.writeheader()
        writer.writerows(measurement_records)

if __name__ == "__main__":
    main()