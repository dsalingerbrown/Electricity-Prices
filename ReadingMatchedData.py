import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

# ---------------- USER CONFIG ----------------
MATCHED_CSV_PATH = r'/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/CA_national_matched.csv'
ZIP_SHP_PATH = r'/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/tl_2025_us_zcta520/tl_2025_us_zcta520.shp'
AGG_OUTPUT_FOLDER = r'/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Aggregated_Data_Matched'
os.makedirs(AGG_OUTPUT_FOLDER, exist_ok=True)
# --------------------------------------------

def normalize_zip(z):
    if pd.isna(z):
        return None
    s = str(int(z)) if isinstance(z, float) and z.is_integer() else str(z).strip()
    s = ''.join(filter(str.isdigit, s))
    if not s:
        return None
    return s[:5].zfill(5) if len(s) >= 5 else s.zfill(5)

def aggregate_capacity_by_zip(df):
    # Normalize ZIP codes
    df['zip'] = df['zip_code'].apply(normalize_zip)

    # Drop rows with missing ZIPs
    df = df[df['zip'].notna()]

    # Convert system size to numeric
    df['system_size_ac'] = pd.to_numeric(df['PV_system_size_DC'], errors='coerce')

    # Aggregate total capacity by ZIP
    agg_total = df.groupby('zip', as_index=False)['system_size_ac'].sum()
    agg_total = agg_total.rename(columns={'system_size_ac': 'pv_capacity_ac'})

    # Count systems by ZIP
    agg_count = df.groupby('zip', as_index=False).size()
    agg_count = agg_count.rename(columns={'size': 'pv_system_count'})

    # Merge capacity and count
    agg = agg_total.merge(agg_count, on='zip', how='left')

    print(f"Aggregated {agg['pv_capacity_ac'].sum():,.0f} kW AC across {len(agg):,} ZIP codes.")
    return agg

def plot_choropleth(agg_df, zip_shp_path, column='pv_capacity_ac', title="PV Capacity by ZIP"):
    zips_gdf = gpd.read_file(zip_shp_path)
    zip_col = next((c for c in zips_gdf.columns if 'zip' in c.lower() or 'zcta' in c.lower()), None)
    if zip_col is None:
        raise KeyError("Could not find ZIP column in shapefile.")
    zips_gdf['zip5'] = zips_gdf[zip_col].astype(str).str.extract(r'(\d{5})')[0].str.zfill(5)

    merged = zips_gdf.merge(agg_df, left_on='zip5', right_on='zip', how='left')
    merged[column] = merged[column].fillna(0.0)

    fig, ax = plt.subplots(figsize=(10, 10))
    merged_ca = merged.cx[-125:-113, 32:43]  # zoom to CA
    vmax = merged[column].quantile(0.95)
    vmax = max(vmax, merged[column].max())

    merged_ca.plot(column=column,
                   cmap='YlOrRd',
                   linewidth=0.3,
                   edgecolor='black',
                   legend=True,
                   legend_kwds={'label': column},
                   ax=ax,
                   vmax=vmax)
    ax.set_title(title, fontsize=14)
    ax.axis('off')
    plt.tight_layout()
    plt.show()

def main():
    use_cols = ['zip_code', 'PV_system_size_DC', 'third_party_owned']
    matched = pd.read_csv(MATCHED_CSV_PATH, usecols=use_cols, low_memory=False)

    agg = aggregate_capacity_by_zip(matched)

    # Save CSV
    out_csv = os.path.join(AGG_OUTPUT_FOLDER, "matched_pv_capacity_by_zip.csv")
    agg.to_csv(out_csv, index=False)
    print(f"Saved aggregation to {out_csv}")

    # Plot
    plot_choropleth(agg, ZIP_SHP_PATH, column='pv_capacity_ac', title="Matched PV Capacity by ZIP")

if __name__ == "__main__":
    main()
