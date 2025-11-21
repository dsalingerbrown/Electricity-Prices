import pandas as pd
import matplotlib.pyplot as plt
import json
import numpy as np

# --- TOGGLES ---
NORMALIZE_BY_DETACHED = True        # normalize by single-family detached homes
NORMALIZE_BY_HOUSEHOLDS = False     # normalize by total households instead (old method)
RESTRICT_TO_COASTAL = True          # restrict to coastal counties only

# === Step 1: Load datasets ===
ev_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/ev_share_long.csv'
pv_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Aggregated_Data_Solar/pv_capacity_ac_by_zip_up_to_2025_agg.csv'
dwellings_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Data/DwellingData/2023Dwellings.csv'
crosswalk_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Data/ZIP_COUNTY_062025.csv'  # <— update this path

# --- Load EV data (now using EV_PHEV_Total) ---
ev_df = pd.read_csv(ev_path)
ev_df['Zip Code'] = ev_df['Zip Code'].astype(str).str.zfill(5)

# Expect columns: BEVs, PHEVs, EV_PHEV_Total, EV_Share, EV_PHEV_Share
if 'EV_PHEV_Total' not in ev_df.columns:
    raise ValueError("❌ ERROR: ev_share_long.csv does not contain EV_PHEV_Total. Make sure the previous script was re-run.")

# --- Load PV data ---
pv_df = pd.read_csv(pv_path)
pv_df.rename(columns={'zip': 'Zip Code'}, inplace=True)
pv_df['Zip Code'] = pv_df['Zip Code'].astype(str).str.zfill(5)

# --- Load Detached Homes Data ---
dwellings_df = pd.read_csv(dwellings_path)
dwellings_df['Zip Code'] = dwellings_df['NAME'].str.extract(r'(\d{5})')
dwellings_df['Zip Code'] = dwellings_df['Zip Code'].astype(str).str.zfill(5)
dwellings_df['num_detached'] = pd.to_numeric(dwellings_df['B25024_002E'], errors='coerce')

# --- Load Household Data Only If Needed ---
if NORMALIZE_BY_HOUSEHOLDS:
    households_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Data/Households.json'
    with open(households_path, 'r') as f:
        data = json.load(f)
    headers = data[0]
    rows = data[1:]
    households_df = pd.DataFrame(rows, columns=headers)
    households_df.rename(columns={
        'zip code tabulation area': 'Zip Code',
        'B11001_001E': 'num_households'
    }, inplace=True)
    households_df['Zip Code'] = households_df['Zip Code'].astype(str).str.zfill(5)
    households_df['num_households'] = pd.to_numeric(households_df['num_households'], errors='coerce')

# --- Load ZIP-to-County Crosswalk (for coastal filtering) ---
if RESTRICT_TO_COASTAL:
    crosswalk = pd.read_csv(crosswalk_path, dtype={'ZIP': str})
    crosswalk['ZIP'] = crosswalk['ZIP'].str.zfill(5)

    # FIPS to County Name lookup (California coastal only)
    county_fips_to_name = {
        # '06015': "Del Norte County",
        # '06023': "Humboldt County",
        # '06045': "Mendocino County",
        # '06097': "Sonoma County",
        '06041': "Marin County",
        '06075': "San Francisco County",
        '06081': "San Mateo County",
        '06013': "Contra Costa County",
        '06001': "Alameda County",
        '06085': "Santa Clara County",
        # '06087': "Santa Cruz County",
        # '06053': "Monterey County",
        # '06079': "San Luis Obispo County",
        '06083': "Santa Barbara County",
        # '06111': "Ventura County",
        '06037': "Los Angeles County",
        '06059': "Orange County",
        '06073': "San Diego County"
    }

    # Match by county FIPS codes (the HUD crosswalk uses numeric county codes)
    coastal_fips = list(county_fips_to_name.keys())
    crosswalk['COUNTY'] = crosswalk['COUNTY'].astype(str).str.zfill(5)
    coastal_zips = crosswalk.loc[crosswalk['COUNTY'].isin(coastal_fips), 'ZIP'].unique().tolist()

    print(f"✅ Identified {len(coastal_zips)} coastal ZIP codes.")

# === Step 2: Filter EV data to 2024 ===
ev_2024 = ev_df[ev_df['Year'] == 2024].copy()

# === Step 3: Merge EV + Detached Data ===
merged = ev_2024.merge(dwellings_df[['Zip Code', 'num_detached']], on='Zip Code', how='inner')
merged = merged[merged['num_detached'] > 0].copy()

# --- Merge Household Data Only If Needed ---
if NORMALIZE_BY_HOUSEHOLDS:
    merged = merged.merge(households_df[['Zip Code', 'num_households']], on='Zip Code', how='inner')
    merged = merged[merged['num_households'] > 0].copy()

# === Step 4: Merge PV Data ===
merged = merged.merge(
    pv_df[['Zip Code', 'pv_capacity_residential_ac', 'pv_count_residential_ac']],
    on='Zip Code',
    how='inner'
)

# --- Apply Coastal Filter if Enabled ---
if RESTRICT_TO_COASTAL:
    before = len(merged)
    merged = merged[merged['Zip Code'].isin(coastal_zips)].copy()
    after = len(merged)
    print(f"🌊 Restricted to coastal ZIPs: {after:,} retained (from {before:,})")

# === Step 4b: Filter ZIPs with top 75% detached homes ===
threshold = merged['num_detached'].quantile(0.25)
print(f"\n25th percentile detached dwellings threshold: {threshold:,.0f}")
filtered = merged[merged['num_detached'] >= threshold].copy()
print(f"Number of ZIPs retained: {len(filtered)} (out of {len(merged)})")

# === Step 4c: Create EV + PHEV plotting variable ===
if NORMALIZE_BY_DETACHED:
    filtered['evs_plot'] = filtered['EV_PHEV_Total'] / filtered['num_detached']
    filtered['pv_plot'] = filtered['pv_capacity_residential_ac'] / filtered['num_detached']
    filtered['pv_count_plot'] = filtered['pv_count_residential_ac'] / filtered['num_detached']
    ev_label = 'EVs + PHEVs per Detached Home'
    pv_label = 'Residential PV Capacity (kW AC) per Detached Home'
    title_suffix = ' (Normalized by Detached Homes)'

elif NORMALIZE_BY_HOUSEHOLDS:
    filtered['evs_plot'] = filtered['EV_PHEV_Total'] / filtered['num_households']
    filtered['pv_plot'] = filtered['pv_capacity_residential_ac'] / filtered['num_households']
    filtered['pv_count_plot'] = filtered['pv_count_residential_ac'] / filtered['num_households']
    ev_label = 'EVs + PHEVs per Household'
    pv_label = 'Residential PV Capacity (kW AC) per Household'
    title_suffix = ' (Normalized by Households)'

else:
    filtered['evs_plot'] = filtered['EV_PHEV_Total']
    filtered['pv_plot'] = filtered['pv_capacity_residential_ac']
    filtered['pv_count_plot'] = filtered['pv_count_residential_ac']
    ev_label = 'EVs + PHEVs'
    pv_label = 'Residential PV Capacity (kW AC)'
    title_suffix = ''

print("\nPreview of filtered dataset:")
print(filtered[['Zip Code', 'EV_PHEV_Total', 'num_detached', 'evs_plot',
                'pv_capacity_residential_ac', 'pv_count_residential_ac', 'pv_plot']].head())

USE_LOG = False
if USE_LOG:
    filtered['evs_plot'] = np.log(filtered['evs_plot'])
    filtered['pv_plot'] = np.log(filtered['pv_plot'])
    filtered['pv_count_plot'] = np.log(filtered['pv_count_plot'])
    ev_label = 'ln(' + ev_label + ')'
    pv_label = 'ln(' + pv_label + ')'
    title_suffix += ' — Log-Transformed'
    print("\n✅ Using natural log.")

# === Top 20 PV ZIPs ===
top20pv = filtered[['Zip Code', 'pv_plot', 'pv_capacity_residential_ac',
                    'pv_count_residential_ac', 'num_detached', 'evs_plot']].copy()
top20pv = top20pv.sort_values(by='pv_plot', ascending=False).head(20)
print("\nTop 20 ZIP Codes by PV" + title_suffix + ":")
print(top20pv.to_string(index=False))

# === Correlation ===
corr = filtered[['evs_plot', 'pv_plot', 'pv_count_plot']].corr()
print("\nUnweighted correlation matrix:")
print(corr)

# === Scatter plots ===
plt.figure(figsize=(8,6))
plt.scatter(filtered['evs_plot'], filtered['pv_plot'], alpha=0.6, edgecolor='black')
plt.xlabel(ev_label)
plt.ylabel(pv_label)
plt.title('EV + PHEV Adoption vs Solar PV Deployment by ZIP' + title_suffix)
plt.grid(True)
plt.tight_layout()
plt.show()

plt.figure(figsize=(8,6))
plt.scatter(filtered['evs_plot'], filtered['pv_count_plot'], alpha=0.6, edgecolor='black')
plt.xlabel(ev_label)
plt.ylabel(pv_label)
plt.title('EV + PHEV Adoption vs PV Installation Count by ZIP' + title_suffix)
plt.grid(True)
plt.tight_layout()
plt.show()
