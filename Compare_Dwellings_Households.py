import pandas as pd
import json

# --- Paths ---
dwellings_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/DwellingData/2023Dwellings.csv'
households_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Households.json'

# === Load Dwellings ===
dwellings_df = pd.read_csv(dwellings_path)
dwellings_df['Zip Code'] = dwellings_df['NAME'].str.extract(r'(\d{5})')
dwellings_df['Zip Code'] = dwellings_df['Zip Code'].astype(str).str.zfill(5)

# Single-family detached total units (occupied + vacant)
dwellings_df['detached_total'] = pd.to_numeric(dwellings_df['B25024_002E'], errors='coerce')
# Vacant detached units
dwellings_df['detached_vacant'] = pd.to_numeric(dwellings_df['B25024_010E'], errors='coerce')
# Occupied detached units
dwellings_df['detached_occupied'] = dwellings_df['detached_total'] - dwellings_df['detached_vacant']

# === Load Households JSON ===
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

# === Merge for Quick Check ===
check = dwellings_df.merge(households_df[['Zip Code', 'num_households']], on='Zip Code', how='inner')

# Compare households vs occupied detached units
check['difference_households_vs_occupied_detached'] = check['num_households'] - check['detached_occupied']

# --- Summary ---
print("\nSummary Statistics (Households vs Occupied Detached Units):")
print(check[['detached_total', 'detached_occupied', 'num_households', 'difference_households_vs_occupied_detached']].describe())

# --- Problematic ZIPs ---
problem_cases = check[check['num_households'] < check['detached_occupied']]
print(f"\nNumber of ZIPs where households < occupied detached units: {len(problem_cases)}")
if len(problem_cases) > 0:
    print("\nExamples (first few problematic ZIPs):")
    print(problem_cases[['Zip Code', 'detached_total', 'detached_occupied', 'num_households', 'difference_households_vs_occupied_detached']].head())
else:
    print("\n✅ All ZIPs have households >= occupied detached units (expected).")
