import geopandas as gpd
import pandas as pd

# -----------------------------
# 1. Load the ZCTA shapefile
# -----------------------------
shapefile_path = "/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/tl_2025_us_zcta520/tl_2025_us_zcta520.shp"

gdf = gpd.read_file(shapefile_path)

print("Columns in shapefile:", gdf.columns)

# Use the ZCTA5CE20 column
if 'ZCTA5CE20' in gdf.columns:
    gdf['ZCTA'] = gdf['ZCTA5CE20']
else:
    raise ValueError("Could not find ZCTA5CE20 column in shapefile.")

# Get sorted list of all ZCTAs
zcta_list = sorted(gdf['ZCTA'].unique())
print(f"\nNumber of ZCTAs in shapefile: {len(zcta_list)}")
print("Sample of ZCTAs:", zcta_list[:20])

# -----------------------------
# 2. Export ZCTAs to CSV
# -----------------------------
output_csv = "/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/all_zctas.csv"
pd.DataFrame({'ZCTA': zcta_list}).to_csv(output_csv, index=False)
print(f"\n✅ Saved all ZCTAs to CSV: {output_csv}")
