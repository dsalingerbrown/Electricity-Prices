import os
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick


# ---------------- USER CONFIG ----------------
CSV_FOLDER = r'/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Data/Interconnected_Project_Sites_2025-08-31 (2)'
# ------------------------------------------------


# --- DIRECT COLUMN NAMES YOU PROVIDED ---
# No regex, no guessing
COLUMN_MAP = {
    "system_size_ac": "System Size AC",
    "app_approved_date": "App Approved Date",
    "technology_type": "Technology Type",
    "customer_sector": "Customer Sector",
}


def clean_df(raw):
    df = pd.DataFrame()

    # Map required columns directly
    df["system_size_ac"] = pd.to_numeric(raw[COLUMN_MAP["system_size_ac"]], errors="coerce")
    df["technology_type"] = raw[COLUMN_MAP["technology_type"]].astype(str).str.strip()
    df["customer_sector"] = raw[COLUMN_MAP["customer_sector"]].astype(str).str.strip()

    df["app_approved_date"] = pd.to_datetime(
        raw[COLUMN_MAP["app_approved_date"]],
        errors="coerce",
        infer_datetime_format=True,
    )

    return df


def load_and_concat_csvs(folder):
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

    return pd.concat(dfs, ignore_index=True)


def make_yearly_aggregations(df):
    # --- Filter to Photovoltaic systems ---
    mask_pv = df["technology_type"].str.contains("photovoltaic", case=False, na=False)
    df_pv = df[mask_pv].copy()

    # --- Filter to Residential ---
    mask_res = df_pv["customer_sector"].str.contains("residential", case=False, na=False)
    df_res = df_pv[mask_res].copy()

    # --- Extract approval year ---
    df_res["year"] = df_res["app_approved_date"].dt.year
    df_res = df_res.dropna(subset=["year"])

    # --- Aggregate by year ---
    yearly_capacity = df_res.groupby("year")["system_size_ac"].sum().sort_index().reset_index()
    yearly_count = df_res.groupby("year").size().sort_index().reset_index(name="installations")

    # --- Make cumulative sums ---
    yearly_capacity["system_size_ac_cumu"] = yearly_capacity["system_size_ac"].cumsum()
    yearly_capacity["system_size_mw_cumu"] = yearly_capacity["system_size_ac_cumu"] / 1000

    yearly_count["installations_cumu"] = yearly_count["installations"].cumsum()

    return yearly_capacity, yearly_count


def plot_yearly_capacity(yearly_capacity):
    plt.figure(figsize=(10, 6))
    plt.plot(
        yearly_capacity["year"],
        yearly_capacity["system_size_mw_cumu"],  # cumulative MW
        marker="o",
        linewidth=2
    )
    plt.title("Residential Solar PV Installed Capacity in California (MW, AC)")
    plt.xlabel("Year", fontsize=12)
    plt.ylabel("Installed Capacity AC (MW)", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xlim(yearly_capacity["year"].min(), yearly_capacity["year"].max())  # start at earliest year
    plt.tight_layout()
    plt.show()


def plot_yearly_count(yearly_count):
    plt.figure(figsize=(10, 6))
    plt.plot(
        yearly_count["year"],
        yearly_count["installations_cumu"],  # cumulative installations
        marker="o",
        linewidth=2
    )
    plt.title("Residential Solar PV Installations in California (Count)")
    plt.xlabel("Year", fontsize=12)
    plt.ylabel("Number of Installations (Thousands)", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xlim(yearly_count["year"].min(), yearly_count["year"].max())  # start at earliest year

    # --- Scale y-axis to thousands ---
    plt.gca().yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f'{int(x/1000):,}'))

    plt.tight_layout()
    plt.show()


def main():
    print("Loading raw CSVs...")
    raw = load_and_concat_csvs(CSV_FOLDER)
    print(f"Loaded {len(raw):,} rows.\n")

    print("Cleaning...")
    cleaned = clean_df(raw)

    print("Aggregating by year...")
    yearly_capacity, yearly_count = make_yearly_aggregations(cleaned)

    print("\n--- Yearly Installed Capacity (MW) ---")
    print(yearly_capacity)

    print("\n--- Yearly Installation Count ---")
    print(yearly_count)

    print("\nPlotting capacity...")
    plot_yearly_capacity(yearly_capacity)

    print("Plotting installation count...")
    plot_yearly_count(yearly_count)


if __name__ == "__main__":
    main()
