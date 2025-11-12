import os
import glob
import re
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

# ---------------- USER CONFIG ----------------
CSV_FOLDER = r'/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Interconnected_Project_Sites_2025-08-31 (2)'
ZIP_SHP_PATH = r'/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/tl_2025_us_zcta520/tl_2025_us_zcta520.shp'
COUNTY_ZIP_CROSSWALK = None  # optional fallback CSV path, or None
# ------------------------------------------------

WANTED_COL_PATTERNS = {
    "system_size_ac": [r"system\s*size.*ac", r"system.*ac", r"system_size_ac", r"systemsize.*ac", r"system_size"],
    "service_zip": [r"service\s*zip", r"service_zip", r"zip\s*code", r"zipcode", r"service\s*zipcode"],
    "app_approved_date": [r"app.*approved.*date", r"approved.*date", r"application.*approved", r"approval.*date", r"app_approved_date"],
    "technology_type": [r"technology.*type", r"technology", r"tech.*type"],
    "service_county": [r"service.*county", r"county"]
}

def find_best_cols(df):
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

def normalize_zip(z):
    if pd.isna(z):
        return None
    s = None
    if isinstance(z, float) and not pd.isna(z) and z.is_integer():
        s = str(int(z))
    else:
        s = str(z).strip()
    s = re.sub(r"\D", "", s)
    if not s:
        return None
    if len(s) >= 5:
        return s[:5]
    return s.zfill(5)

def fill_zip_from_county(df, county_zip_crosswalk_path):
    if county_zip_crosswalk_path is None:
        return df
    cw = pd.read_csv(county_zip_crosswalk_path, dtype=str)
    cw_cols = {c.lower(): c for c in cw.columns}
    if "county" not in cw_cols or "zip" not in cw_cols:
        print("County-zip crosswalk provided but doesn't contain 'county' and 'zip' columns. Skipping fallback.")
        return df
    cw = cw[[cw_cols["county"], cw_cols["zip"]]].rename(columns={cw_cols["county"]: "county", cw_cols["zip"]: "zip"})
    cw["zip"] = cw["zip"].apply(lambda z: normalize_zip(z))
    modal = cw.groupby("county")["zip"].agg(lambda s: pd.Series(s).mode().iat[0] if not s.mode().empty else None).reset_index()
    modal.columns = ["service_county_key", "modal_zip"]
    df["service_county_key"] = df["service_county"].astype(str).str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
    modal["service_county_key"] = modal["service_county_key"].astype(str).str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
    df = df.merge(modal, on="service_county_key", how="left")
    df["service_zip_filled"] = df["service_zip"].fillna(df["modal_zip"])
    df.drop(columns=["service_county_key", "modal_zip"], inplace=True)
    return df

def prepare_df(raw):
    colmap = find_best_cols(raw)
    clean = pd.DataFrame()
    for k, c in colmap.items():
        if c is not None:
            clean[k] = raw[c]
        else:
            clean[k] = pd.NA

    cs_col = None
    for pat in [r"customer.*sector", r"customer.*class", r"service.*type", r"customer.*type"]:
        regex = re.compile(pat, flags=re.I)
        for c in raw.columns:
            if regex.search(c):
                cs_col = c
                break
        if cs_col:
            break
    if cs_col:
        clean["customer_sector"] = raw[cs_col]
    else:
        clean["customer_sector"] = pd.NA

    clean["system_size_ac"] = pd.to_numeric(clean["system_size_ac"], errors="coerce")
    clean["app_approved_date"] = pd.to_datetime(clean["app_approved_date"], errors="coerce", infer_datetime_format=True)
    clean["technology_type"] = clean["technology_type"].astype(str).str.strip()
    clean["service_zip"] = clean["service_zip"].apply(lambda z: normalize_zip(z) if not pd.isna(z) else None)
    clean["service_county"] = clean["service_county"].astype(str).where(~clean["service_county"].isna(), None)

    return clean

def aggregate_capacity_by_zip(clean_df, year=2025, include_all_prior=False, include_missing_dates=False, county_zip_crosswalk_path=None):
    tmp = clean_df.copy()
    
    # --- Fill ZIPs from county crosswalk if provided ---
    if county_zip_crosswalk_path is not None:
        if "service_county" not in tmp.columns:
            tmp["service_county"] = None
        if "service_zip" not in tmp.columns:
            tmp["service_zip"] = None
        tmp = fill_zip_from_county(tmp, county_zip_crosswalk_path)
        tmp["service_zip"] = tmp["service_zip_filled"]
        tmp.drop(columns=["service_zip_filled"], inplace=True)

    # --- Filter photovoltaic systems ---
    mask_tech = tmp["technology_type"].fillna("").str.contains(r"photovoltaic", case=False, na=False)
    df_photovoltaic = tmp[mask_tech].copy()
    print(f"Rows with 'Photovoltaic' technology: {len(df_photovoltaic):,}")

    # --- Extract approval year ---
    df_photovoltaic["approved_year"] = df_photovoltaic["app_approved_date"].dt.year

    # --- Filter by year ---
    if include_all_prior:
        condition = (df_photovoltaic["approved_year"].notna() & (df_photovoltaic["approved_year"] <= year))
        if include_missing_dates:
            condition = condition | df_photovoltaic["approved_year"].isna()
        df_year = df_photovoltaic[condition].copy()
        print(f"Including all interconnections up to {year}: {len(df_year):,} rows selected (include_missing_dates={include_missing_dates})")
    else:
        condition = (df_photovoltaic["approved_year"] == year)
        if include_missing_dates:
            condition = condition | df_photovoltaic["approved_year"].isna()
        df_year = df_photovoltaic[condition].copy()
        print(f"Rows approved in {year}: {len(df_year):,} (include_missing_dates={include_missing_dates})")

    # --- Drop rows with missing ZIPs ---
    before_drop = len(df_year)
    df_year = df_year[df_year["service_zip"].notna() & (df_year["service_zip"].astype(str) != "None")]
    dropped = before_drop - len(df_year)
    if dropped > 0:
        print(f"Dropped {dropped:,} rows with missing service_zip after fallbacks.")

    # --- Aggregate total PV capacity ---
    agg_total = df_year.groupby("service_zip", as_index=False)["system_size_ac"].sum()
    agg_total = agg_total.rename(columns={"service_zip": "zip", "system_size_ac": "pv_capacity_ac"})
    agg_total["zip"] = agg_total["zip"].astype(str).str.zfill(5)

    # --- Aggregate residential PV capacity ---
    df_res = df_year[df_year["customer_sector"].str.contains("residential", case=False, na=False)].copy()
    agg_res = df_res.groupby("service_zip", as_index=False)["system_size_ac"].sum()
    agg_res = agg_res.rename(columns={"service_zip": "zip", "system_size_ac": "pv_capacity_residential_ac"})
    agg_res["zip"] = agg_res["zip"].astype(str).str.zfill(5)

    # --- Aggregate residential PV capacity under 10 kW ---
    df_res_under10 = df_res[df_res["system_size_ac"] < 10].copy()

    # Capacity under 10 kW
    agg_res_under10 = df_res_under10.groupby("service_zip", as_index=False)["system_size_ac"].sum()
    agg_res_under10 = agg_res_under10.rename(columns={"service_zip": "zip", "system_size_ac": "pv_capacity_residential_ac_under10"})
    agg_res_under10["zip"] = agg_res_under10["zip"].astype(str).str.zfill(5)

    # ✅ NEW: count of systems under 10 kW
    agg_res_under10_count = df_res_under10.groupby("service_zip", as_index=False).size()
    agg_res_under10_count = agg_res_under10_count.rename(columns={"service_zip": "zip", "size": "pv_count_residential_ac_under10"})
    agg_res_under10_count["zip"] = agg_res_under10_count["zip"].astype(str).str.zfill(5)

    # ✅ Count of *all* residential PV systems (regardless of size)
    agg_res_count = df_res.groupby("service_zip", as_index=False).size()
    agg_res_count = agg_res_count.rename(columns={"service_zip": "zip", "size": "pv_count_residential_ac"})
    agg_res_count["zip"] = agg_res_count["zip"].astype(str).str.zfill(5)



    # --- Merge all aggregates ---
    agg = agg_total.merge(agg_res, on="zip", how="left")
    agg = agg.merge(agg_res_count, on="zip", how="left")                  # ✅ add total residential count
    agg = agg.merge(agg_res_under10, on="zip", how="left")
    agg = agg.merge(agg_res_under10_count, on="zip", how="left")


    agg["pv_capacity_residential_ac"] = agg["pv_capacity_residential_ac"].fillna(0.0)
    agg["pv_count_residential_ac"] = agg["pv_count_residential_ac"].fillna(0).astype(int)

    agg["pv_capacity_residential_ac_under10"] = agg["pv_capacity_residential_ac_under10"].fillna(0.0)
    agg["pv_count_residential_ac_under10"] = agg["pv_count_residential_ac_under10"].fillna(0).astype(int)



    # --- Print min/max stats for all ---
    min_row = agg.loc[agg["pv_capacity_ac"].idxmin()]
    max_row = agg.loc[agg["pv_capacity_ac"].idxmax()]
    print("\n--- PV Capacity AC (kW) Stats by ZIP ---")
    print(f"Min: ZIP {min_row['zip']} — {min_row['pv_capacity_ac']:.2f} kW")
    print(f"Max: ZIP {max_row['zip']} — {max_row['pv_capacity_ac']:.2f} kW")

    min_row_res = agg.loc[agg["pv_capacity_residential_ac"].idxmin()]
    max_row_res = agg.loc[agg["pv_capacity_residential_ac"].idxmax()]
    print("\n--- Residential PV Capacity AC (kW) Stats by ZIP ---")
    print(f"Min: ZIP {min_row_res['zip']} — {min_row_res['pv_capacity_residential_ac']:.2f} kW")
    print(f"Max: ZIP {max_row_res['zip']} — {max_row_res['pv_capacity_residential_ac']:.2f} kW")

    min_row_under10 = agg.loc[agg["pv_capacity_residential_ac_under10"].idxmin()]
    max_row_under10 = agg.loc[agg["pv_capacity_residential_ac_under10"].idxmax()]
    print("\n--- Residential PV <10 kW AC (kW) Stats by ZIP ---")
    print(f"Min: ZIP {min_row_under10['zip']} — {min_row_under10['pv_capacity_residential_ac_under10']:.2f} kW")
    print(f"Max: ZIP {max_row_under10['zip']} — {max_row_under10['pv_capacity_residential_ac_under10']:.2f} kW")

    return agg, df_year



def plot_choropleth(agg_df, zip_shp_path, title="PV Capacity (AC) by ZIP - 2025", vmax_quantile=0.95):
    zips_gdf = gpd.read_file(zip_shp_path)
    zip_col = None
    for c in zips_gdf.columns:
        if re.search(r"zip|zcta|zip5|zcta5", c, flags=re.I):
            zip_col = c
            break
    if zip_col is None:
        raise KeyError("Could not find a ZIP column name in the shapefile. Columns: " + ", ".join(zips_gdf.columns.astype(str)))
    zips_gdf["zip5"] = zips_gdf[zip_col].astype(str).str.extract(r"(\d{5})")[0].str.zfill(5)
    merged = zips_gdf.merge(agg_df, left_on="zip5", right_on="zip", how="left")
    merged["pv_capacity_residential_ac_under10"] = merged["pv_capacity_residential_ac_under10"].fillna(0.0)

    vmax = merged["pv_capacity_residential_ac_under10"].quantile(vmax_quantile)
    vmax = max(vmax, merged["pv_capacity_residential_ac_under10"].max())

    fig, ax = plt.subplots(figsize=(10, 10))
    merged_ca = merged.cx[-125:-113, 32:43]

    vmax = 20000
    merged_ca.plot(column='pv_capacity_residential_ac_under10',
                   cmap='YlOrRd',
                   linewidth=0.3,
                   edgecolor='black',
                   legend=True,
                   legend_kwds={'label': "Total Solar PV Capacity (kW AC)"},
                   ax=ax,
                   vmax=vmax)

    ax.set_title(title, fontsize=14)
    ax.axis('off')
    plt.tight_layout()
    plt.show()


def main():
    raw = load_and_concat_csvs(CSV_FOLDER)
    print(f"Loaded combined CSV rows: {len(raw):,}")
    cleaned = prepare_df(raw)

    agg, used_rows = aggregate_capacity_by_zip(cleaned,
                                               year=2025,
                                               include_all_prior=True,
                                               include_missing_dates=False,
                                               county_zip_crosswalk_path=COUNTY_ZIP_CROSSWALK)

    print(f"\nAggregated {agg['pv_capacity_ac'].sum():,.0f} kW AC across {len(agg):,} ZIP codes (up to 2025).")

    # --- New folder for aggregated output ---
    AGG_OUTPUT_FOLDER = r'/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Aggregated_Data_Solar'
    os.makedirs(AGG_OUTPUT_FOLDER, exist_ok=True)

    # --- Save CSV there ---
    out_csv = os.path.join(AGG_OUTPUT_FOLDER, "pv_capacity_ac_by_zip_up_to_2025_agg.csv")
    agg.to_csv(out_csv, index=False)
    print(f"Saved aggregation to {out_csv}")


    plot_choropleth(agg, ZIP_SHP_PATH, title="PV Capacity (AC) by ZIP — Up to 2025")


if __name__ == "__main__":
    main()
