import pandas as pd

# files
USED_PROBES_FILE = "used_dot_probes.txt"
MAPPING_FILE = "../Task 1/probe_asn_mapping.csv"
OUTPUT_FILE = "probe_asn_mapping_dot.csv"

# 1. load used probe ids
with open(USED_PROBES_FILE) as f:
    used_probes = set(int(line.strip()) for line in f if line.strip().isdigit())

# 2. load mapping file
mapping_df = pd.read_csv(MAPPING_FILE)

# 3. filter only used probes
filtered_df = mapping_df[mapping_df['probe_id'].isin(used_probes)]

# 4. save result
filtered_df.to_csv(OUTPUT_FILE, index=False)

print(f"Fertig. {len(filtered_df)} Zuordnungen nach {OUTPUT_FILE} geschrieben.")
