import os
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt

# ---------------- USER CONFIG ----------------
CSV_FOLDER = r'/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Interconnected_Project_Sites_2025-08-31 (2)'   # <- change if needed
# ------------------------------------------------

# Column patterns to automatically detect names across datasets
WANTED_COL_PATTERNS = {
    "system_size_dc": [r"system\s*size.*dc", r"system.*dc", r"system_size_dc", r"systemsize.*dc", r"system_size"],
    "technology_type": [r"technology.*type", r"technology", r"tech.*type"],
    "service_county": [r"service.*county", r"county"]
}

def find_best_cols(df):
    """Automatically find best-matching column names by regex pattern."""
    colmap = {}
    cols = list(df.columns)
    for key, patterns in WANTED_COL_PATTERNS.items():
        found = None
        for pat in patterns:
            regex = re.compile(pat, flags=re.I)
            for c in cols:
                if regex.search(c):
                    found = c
                    break
            if found:
                break
        colmap[key] = found
    return colmap

def load_and_concat_csvs(folder):
    """Combine all CSVs in a folder into one DataFrame."""
    paths = glob.glob(os.path.join(folder, "*.csv"))
    if not paths:
        raise FileNotFoundError(f"No CSVs found in {folder}")
    dfs = []
    for p in paths:
        try:
            df = pd.read_csv(p, low_memory=False)
            df["__source_file"] = os.path.basename(p)
            dfs.append(df)
        except Exception as e:
            print(f"WARNING: failed to read {p}: {e}")
    combined = pd.concat(dfs, ignore_index=True)
    return combined

def prepare_df(raw):
    """Extract and clean relevant columns."""
    colmap = find_best_cols(raw)
    clean = pd.DataFrame()
    for k, c in colmap.items():
        if c is not None:
            clean[k] = raw[c]
        else:
            clean[k] = pd.NA

    clean["system_size_dc"] = pd.to_numeric(clean["system_size_dc"], errors="coerce")
    clean["technology_type"] = clean["technology_type"].astype(str).str.strip()
    clean["service_county"] = clean["service_county"].astype(str).str.strip().str.lower()
    return clean

def plot_histograms(df):
    """Generate histograms of PV system sizes."""
    # Filter to photovoltaic systems
    pv_df = df[df["technology_type"].str.contains("photovoltaic", case=False, na=False)].copy()
    pv_df = pv_df.dropna(subset=["system_size_dc"])
    print("\nSummary statistics:")
    print(pv_df["system_size_dc"].describe(percentiles=[0.5, 0.9, 0.95, 0.99, 0.999]))

    # Show some largest values to see if a few huge systems dominate
    print("\nLargest 10 system sizes:")
    print(pv_df["system_size_dc"].nlargest(10))


    print(f"Total photovoltaic records: {len(pv_df):,}")
    print("Summary statistics for system size (kW DC):")
    print(pv_df["system_size_dc"].describe(percentiles=[0.5, 0.9, 0.95, 0.99]))

    # --- Histogram 1: full range ---
    plt.figure(figsize=(8,5))
    plt.hist(pv_df["system_size_dc"], bins=100, color='orange', edgecolor='black')
    plt.xlabel('System Size (kW DC)')
    plt.ylabel('Number of Installations')
    plt.title('Distribution of Solar PV System Sizes in California (Full Range)')
    plt.tight_layout()
    plt.show()

    # --- Histogram 2: log scale ---
    plt.figure(figsize=(8,5))
    plt.hist(pv_df["system_size_dc"], bins=100, color='orange', edgecolor='black')
    plt.xscale('log')
    plt.xlabel('System Size (kW DC, log scale)')
    plt.ylabel('Number of Installations')
    plt.title('Distribution of Solar PV System Sizes (Log Scale)')
    plt.tight_layout()
    plt.show()

    # --- Histogram 3: zoomed-in (<1 MW) ---
    plt.figure(figsize=(8,5))
    pv_under_1mw = pv_df[pv_df["system_size_dc"] < 1000]
    plt.hist(pv_under_1mw["system_size_dc"], bins=100, color='orange', edgecolor='black')
    plt.xlabel('System Size (kW DC)')
    plt.ylabel('Number of Installations')
    plt.title('Distribution of Solar PV System Sizes (<1 MW only)')
    plt.tight_layout()
    plt.show()

def main():
    raw = load_and_concat_csvs(CSV_FOLDER)
    print(f"Loaded combined CSV rows: {len(raw):,}")
    cleaned = prepare_df(raw)
    plot_histograms(cleaned)

if __name__ == "__main__":
    main()
