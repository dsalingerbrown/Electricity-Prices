import pandas as pd
import numpy as np

# -----------------------------
# 1. Load data
# -----------------------------
# Path to EV share long CSV (your long-form CSV from previous script)
ev_csv_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/ev_share_long.csv'

# Path to updated income/population CSV with CAAGI_per_capita
income_csv_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/CA_income_population.csv'

# Load CSVs
ev_df = pd.read_csv(ev_csv_path, dtype={'Zip Code': str})
income_df = pd.read_csv(income_csv_path, dtype={'ZipCode': str})

# -----------------------------
# 2. Merge EV data with per-capita income
# -----------------------------
# Ensure consistent column names
income_df = income_df.rename(columns={'ZipCode': 'Zip Code'})

# Merge on Zip Code
merged_df = pd.merge(ev_df, income_df[['Zip Code', 'CAAGI_per_capita']], on='Zip Code', how='inner')

print(f"Merged dataset has {len(merged_df)} rows")

# -----------------------------
# 3. Option A: normalize EV share by per-capita income
# -----------------------------
# This gives EVs per unit income (you can multiply by 1000 or other factor for readability)
merged_df['EV_per_income'] = merged_df['EV_Share'] / merged_df['CAAGI_per_capita'] * 1e6

# Optional: handle infinite or missing values
merged_df['EV_per_income'].replace([np.inf, -np.inf], np.nan, inplace=True)
merged_df = merged_df.dropna(subset=['EV_per_income'])

# -----------------------------
# 4. Option D: percentile rank per year
# -----------------------------
# Compute percentile rank of EV_Share within each year
merged_df['EV_Share_percentile'] = merged_df.groupby('Year')['EV_Share'].rank(pct=True)

# -----------------------------
# 5. Pivot tables (optional)
# -----------------------------
# Pivot Option A: EV per income
pivot_a = merged_df.pivot_table(
    index='Zip Code',
    columns='Year',
    values='EV_per_income'
)
pivot_a.to_csv('EV_per_income_pivot.csv')
print("✅ Saved pivot table for EV per income")

# Pivot Option D: EV percentile
pivot_d = merged_df.pivot_table(
    index='Zip Code',
    columns='Year',
    values='EV_Share_percentile'
)
pivot_d.to_csv('EV_percentile_pivot.csv')
print("✅ Saved pivot table for EV share percentile")

# -----------------------------
# 6. Quick summary statistics
# -----------------------------
for year in sorted(merged_df['Year'].unique()):
    df_year = merged_df[merged_df['Year'] == year]
    print(f"\nYear {year}:")
    print(f"EV per income - min: {df_year['EV_per_income'].min():.6f}, max: {df_year['EV_per_income'].max():.6f}")
    print(f"EV percentile - min: {df_year['EV_Share_percentile'].min():.2f}, max: {df_year['EV_Share_percentile'].max():.2f}")
