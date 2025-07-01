import csv
import requests
import sqlite3
import time

DB_FILE = "Task 2/dns_measurements_dot.sqlite" # change for task 1/2
MEASUREMENT_IDS_CSV = "Task 2/measurement_ids_dot.csv" # change for task 1/2

TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS results (
    msm_id INTEGER,
    domain TEXT,
    resolver TEXT,
    prb_id INTEGER,
    rt REAL,
    size INTEGER,
    src_addr TEXT,
    dst_addr TEXT,
    timestamp INTEGER,
    err BOOLEAN,
    err_msg TEXT
);
"""

def get_measurement_results(measurement_id):
    url = f"https://atlas.ripe.net/api/v2/measurements/{measurement_id}/results/?format=json"
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Retrying {measurement_id} due to error: {e}")
            time.sleep(5)
    return []

def parse_resultset_entry(msm_id, prb_id, domain, resolver, entry):
    # Defaults
    rt = None
    size = None
    src_addr = entry.get("src_addr")
    dst_addr = entry.get("dst_addr")
    timestamp = entry.get("time")  # use the measurement time, not the probe-level timestamp
    err = False
    err_msg = None

    # Successful result
    if "result" in entry:
        rt = entry["result"].get("rt")
        size = entry["result"].get("size")
    # Error
    if "error" in entry:
        err = True
        # error is usually a dict, take the first value as message
        if isinstance(entry["error"], dict):
            err_msg = "; ".join([f"{k}: {v}" for k, v in entry["error"].items()])
        else:
            err_msg = str(entry["error"])

    return (msm_id, domain, resolver, prb_id, rt, size, src_addr, dst_addr, timestamp, err, err_msg)

def main():
    # 1. Read measurement IDs and resolver info
    measurements = []
    with open(MEASUREMENT_IDS_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            measurements.append({
                "msm_id": int(row["measurement_id"]),
                "resolver": row["resolver"],
                "domain": row["domain"],
            })

    # 2. Setup SQLite database
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(TABLE_SCHEMA)
    conn.commit()

    # 3. Download and insert results
    for m in measurements:
        print(f"Fetching results for measurement {m['msm_id']} ({m['resolver']} {m['domain']}) ...")
        results = get_measurement_results(m["msm_id"])
        for result in results:
            msm_id = result.get("msm_id")
            prb_id = result.get("prb_id")
            # Iterate over all entries in resultset (if present)
            resultset = result.get("resultset")
            if resultset is not None:
                for entry in resultset:
                    row = parse_resultset_entry(msm_id, prb_id, m["domain"], m["resolver"], entry)
                    cur.execute(
                        "INSERT INTO results (msm_id, domain, resolver, prb_id, rt, size, src_addr, dst_addr, timestamp, err, err_msg) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        row
                    )
            else:
                # Fallback: handle probes with no resultset (should be rare)
                row = parse_resultset_entry(msm_id, prb_id, m["domain"], m["resolver"], result)
                cur.execute(
                    "INSERT INTO results (msm_id, domain, resolver, prb_id, rt, size, src_addr, dst_addr, timestamp, err, err_msg) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    row
                )
        conn.commit()
    conn.close()
    print(f"Done! Results saved in {DB_FILE}")

if __name__ == "__main__":
    main()