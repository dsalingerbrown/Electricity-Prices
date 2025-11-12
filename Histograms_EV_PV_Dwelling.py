import pandas as pd
import matplotlib.pyplot as plt

# === Load Merged Dataset (same merge stage as before) ===
# If you already have `merged` from your other script, you can instead:
# from your_script_name import merged

ev_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/ev_share_long.csv'
pv_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Aggregated_Data_Solar/pv_capacity_ac_by_zip_up_to_2025_agg.csv'
dwellings_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/DwellingData/2023Dwellings.csv'

# Load EV data
ev_df = pd.read_csv(ev_path)
ev_df['Zip Code'] = ev_df['Zip Code'].astype(str).str.zfill(5)
ev_2024 = ev_df[ev_df['Year'] == 2024].copy()

# Load PV data
pv_df = pd.read_csv(pv_path)
pv_df.rename(columns={'zip': 'Zip Code'}, inplace=True)
pv_df['Zip Code'] = pv_df['Zip Code'].astype(str).str.zfill(5)

# Load dwellings
dwellings_df = pd.read_csv(dwellings_path)
dwellings_df['Zip Code'] = dwellings_df['NAME'].str.extract(r'(\d{5})')
dwellings_df['Zip Code'] = dwellings_df['Zip Code'].astype(str).str.zfill(5)
dwellings_df['num_detached'] = pd.to_numeric(dwellings_df['B25024_002E'], errors='coerce')

# Merge
merged = ev_2024.merge(dwellings_df[['Zip Code', 'num_detached']], on='Zip Code', how='inner')
merged = merged[merged['num_detached'] > 0].copy()
merged = merged.merge(pv_df[['Zip Code', 'pv_count_residential_ac']], on='Zip Code', how='inner')

# === HISTOGRAM 1: Single-family detached dwellings ===
plt.figure(figsize=(8,5))
plt.hist(merged['num_detached'], bins=50)
plt.xlabel('Number of Single-Family Detached Dwellings per ZIP')
plt.ylabel('Frequency')
plt.title('Distribution of Single-Family Detached Housing (by ZIP)')
plt.tight_layout()
plt.show()

# === HISTOGRAM 2: PV installation count (residential) ===
plt.figure(figsize=(8,5))
plt.hist(merged['pv_count_residential_ac'], bins=50)
plt.xlabel('Residential PV Install Count per ZIP')
plt.ylabel('Frequency')
plt.title('Distribution of Residential PV Installations (by ZIP)')
plt.tight_layout()
plt.show()

# === HISTOGRAM 3: EV count ===
plt.figure(figsize=(8,5))
plt.hist(merged['EVs'], bins=50)
plt.xlabel('Number of EVs per ZIP')
plt.ylabel('Frequency')
plt.title('Distribution of EV Adoption (by ZIP)')
plt.tight_layout()
plt.show()

# === Summary Counts ===
num_zips = len(merged)
print(f"Total ZIPs in dataset: {num_zips}")

print("\nNon-missing values per variable:")
print(merged[['num_detached', 'pv_count_residential_ac', 'EVs']].count())

print("\nZIPs with ≥1 PV system:", (merged['pv_count_residential_ac'] > 0).sum())
print("ZIPs with ≥1 EV registered:", (merged['EVs'] > 0).sum())


print(merged)