import pandas as pd

# === Step 1: Load both datasets ===
ev_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/ev_share_long.csv'
income_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/CA_income_population.csv'

ev_df = pd.read_csv(ev_path)
income_df = pd.read_csv(income_path)

# === Step 2: Standardize ZIP code column names and formats ===
ev_df['Zip Code'] = ev_df['Zip Code'].astype(str).str.zfill(5)
income_df['ZipCode'] = income_df['ZipCode'].astype(str).str.zfill(5)

# === Step 3: Merge on ZIP code ===
merged = pd.merge(ev_df, income_df, left_on='Zip Code', right_on='ZipCode', how='inner')

print(f"Merged dataset shape: {merged.shape}")
print(merged.head())

# === Step 4: Compute EVs per capita income ===
# Scale by 1e6 to make numbers more interpretable (EVs per $1M income per capita)
merged['EVs_per_income_scaled'] = merged['EVs'] / merged['CAAGI_per_capita'] * 1e6

# === Step 5: Save output ===
merged.to_csv('/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/evs_income_normalized.csv', index=False)
print("✅ Saved merged data with EVs per income to 'evs_income_normalized.csv'")

# === Step 6: Optional summary ===
summary = merged.groupby('Year')['EVs_per_income_scaled'].describe()
print("\nSummary statistics by year:")
print(summary)

# Optional pivot table for inspection
pivot = merged.pivot_table(
    index='Zip Code',
    columns='Year',
    values='EVs_per_income_scaled'
)
pivot.to_csv('/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/evs_per_income_pivot.csv')
print("✅ Saved pivot table to 'evs_per_income_pivot.csv'")

import geopandas as gpd
import matplotlib.pyplot as plt

# === Step 7: Load California ZCTA shapefile ===
# Replace this with the actual path to your shapefile
shapefile_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/tl_2025_us_zcta520/tl_2025_us_zcta520.shp'
zcta_gdf = gpd.read_file(shapefile_path)

# Standardize ZIP code formatting
zcta_gdf['ZCTA5CE20'] = zcta_gdf['ZCTA5CE20'].astype(str).str.zfill(5)

# === Step 8: Choose a year to visualize ===
# You can change the year here to 2021, 2022, etc.
year_to_plot = 2025
map_df = merged[merged['Year'] == year_to_plot].copy()

# === Step 9: Merge shapefile with EV/income data ===
geo_merged = zcta_gdf.merge(map_df, left_on='ZCTA5CE20', right_on='Zip Code', how='inner')

print(f"Geo merged shapefile has {len(geo_merged)} ZCTAs for year {year_to_plot}")

# === Step 10: Plot choropleth ===
fig, ax = plt.subplots(1, 1, figsize=(10, 10))
geo_merged.plot(
    column='EVs_per_income_scaled',
    cmap='YlGnBu',         # Blue-green gradient (darker = higher)
    linewidth=0,
    legend=True,
    scheme='quantiles',    # Uses quantiles to spread the data evenly across color bins
    k=6,                   # 6 color bins
    ax=ax
)

ax.set_title(f'EVs/Income per Capita (Scaled) by ZIP Code – {year_to_plot}', fontsize=14)
ax.axis('off')

plt.show()
