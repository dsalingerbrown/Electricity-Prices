
import pandas as pd

# === Step 1: Load both datasets ===

# Replace with your actual file paths
tax_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/2024_personal_income_tax_statistics_by_zip_code.csv'
pop_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/DECENNIALDHC2020.P1_2025-10-31T145824/DECENNIALDHC2020.P1-Data.csv'

# Load CSVs
tax_df = pd.read_csv(tax_path)
pop_df = pd.read_csv(pop_path)

# Quick look
print("Tax data columns:", tax_df.columns)
print("Population data columns:", pop_df.columns)



# === Step 2: Filter and aggregate tax data to 2020 ===
tax_df_2020 = tax_df[tax_df['TaxYear'] == 2020].copy()
tax_df_2020['ZipCode'] = tax_df_2020['ZipCode'].astype(str).str.zfill(5)
tax_df_2020 = tax_df_2020[['ZipCode', 'CAAGI']]

# For population data:
# Extract the numeric ZIP from the NAME column (e.g., 'ZCTA5_95014' → '95014')
pop_df['ZipCode'] = pop_df['NAME'].str.extract(r'ZCTA5 (\d{5})')
pop_df['ZipCode'] = pop_df['ZipCode'].astype(str)

# Keep only relevant columns
pop_df = pop_df[['ZipCode', 'P1_001N']]
pop_df = pop_df.rename(columns={'P1_001N': 'Population'})


# === Step 3: Merge datasets ===

merged_df = pd.merge(
    tax_df_2020,
    pop_df,
    on='ZipCode',
    how='inner'  # keep only ZIPs that appear in both datasets
)

# Check results
print(f"Merged dataset has {len(merged_df)} ZIP codes")
print(merged_df.head())

#Save to CSV
merged_df.to_csv('CA_income_population.csv', index=False)



# --- FIX: ensure numeric types for calculation ---
merged_df['CAAGI'] = pd.to_numeric(merged_df['CAAGI'].astype(str).str.replace(',', ''), errors='coerce')
merged_df['Population'] = pd.to_numeric(merged_df['Population'].astype(str).str.replace(',', ''), errors='coerce')

# Drop rows with missing or invalid values
merged_df = merged_df.dropna(subset=['CAAGI', 'Population'])

merged_df = merged_df[merged_df['CAAGI'] >= 0]

# === Step 4: Compute per-capita income ===
merged_df['CAAGI_per_capita'] = merged_df['CAAGI'] / merged_df['Population']

import numpy as np

# Check if any per-capita values are infinite
print("Any infinite per-capita values?", np.isinf(merged_df['CAAGI_per_capita']).any())

# Optionally see which ZIPs
print(merged_df[np.isinf(merged_df['CAAGI_per_capita'])])


merged_df = merged_df[np.isfinite(merged_df['CAAGI_per_capita'])]

# Save updated CSV with per-capita income
merged_df.to_csv('CA_income_population.csv', index=False)
print("✅ Updated CSV now includes CAAGI_per_capita")



# # === Step 5: Plot histogram ===
# import matplotlib.pyplot as plt

# # Clip per-capita income to the 99th percentile
# upper = merged_df['CAAGI_per_capita'].quantile(0.99)
# hist_data = merged_df[merged_df['CAAGI_per_capita'] <= upper]

# plt.figure(figsize=(10,6))
# plt.hist(hist_data['CAAGI_per_capita'], bins=50, color='skyblue', edgecolor='black')
# plt.title('Distribution of Per-Capita Income by ZIP Code in California (2020)', fontsize=14)
# plt.xlabel('Per-Capita Income ($)', fontsize=12)
# plt.ylabel('Number of ZIP Codes', fontsize=12)
# plt.grid(axis='y', alpha=0.75)
# plt.tight_layout()
# plt.show()


# === Step 6: Map per-capita income by ZIP ===
import geopandas as gpd
import matplotlib.pyplot as plt

# Clip the top 1% for color scaling
upper = merged_df['CAAGI_per_capita'].quantile(0.99)
map_df = merged_df[merged_df['CAAGI_per_capita'] <= upper]

# Load ZCTA shapefile (replace with your actual path)
shapefile_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/tl_2025_us_zcta520/tl_2025_us_zcta520.shp'
zcta_gdf = gpd.read_file(shapefile_path)

# Make sure the ZCTA column matches your ZIP codes
zcta_gdf['ZipCode'] = zcta_gdf['ZCTA5CE20'].astype(str).str.zfill(5)  # adjust column name if different

# Merge shapefile with your data
map_gdf = zcta_gdf.merge(map_df, on='ZipCode', how='left')

# Plot choropleth
fig, ax = plt.subplots(1, 1, figsize=(10, 12))
map_gdf.plot(
    column='CAAGI_per_capita',
    cmap='YlGnBu',            # yellow → green → blue, darker = higher
    linewidth=0.1,
    ax=ax,
    edgecolor='gray',
    legend=True,
    vmin=0,
    vmax=upper
)
ax.set_title('Per-Capita Income by ZIP Code in California (2020)', fontsize=14)
ax.axis('off')
plt.tight_layout()
plt.show()

