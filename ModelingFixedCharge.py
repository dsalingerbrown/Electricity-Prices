import pandas as pd
import numpy as np

# 1. Define the rate structures (TOU integrated)
rates = {
    'S1_Volumetric': 0.45, 'S1_Peak': 0.57, 'S1_OffPeak': 0.42, 'S1_Fixed': 0.0,
    'S2_Volumetric': 0.39, 'S2_Peak': 0.51, 'S2_OffPeak': 0.36, 'S2_Fixed': 24.15,
    'S3_Volumetric': 0.20, 'S3_Peak': 0.32, 'S3_OffPeak': 0.17, 'S3_Fixed': 100.0,    
    'S3_Fixed_EV': 130.0                         
}

# Consumption behavior: 20% Peak, 80% Off-Peak
peak_ratio = 0.20
offpeak_ratio = 0.80

# 2. Load Your Data
df = pd.read_csv('/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Data/2024_personal_income_tax_statistics_by_zip_code.csv')

# Ensure Zip Codes are treated as strings
zip_col = 'ZipCode' 
df[zip_col] = df[zip_col].astype(str)

# Clean data
df = df[df['Avg_AGI'] > 0].copy()

# 3. Filter for target zip codes and generate specific Household Profiles
target_zips = ['94025', '93640', '90011']
df_filtered = df[df[zip_col].isin(target_zips)].copy()

profiles = []
for index, row in df_filtered.iterrows():
    if row[zip_col] == '94025':
        # Profile 1: 94025 Neighbor WITH an EV
        p1 = row.copy()
        p1['Profile_Name'] = 'Wealthy Area - HAS EV (Menlo Park)'
        p1['Baseline_Usage_kWh'] = 800
        p1['Is_EV'] = True
        profiles.append(p1)
        
        # Profile 2: 94025 Neighbor WITHOUT an EV
        p2 = row.copy()
        p2['Profile_Name'] = 'Wealthy Area - NO EV (Menlo Park)'
        p2['Baseline_Usage_kWh'] = 500
        p2['Is_EV'] = False
        profiles.append(p2)
        
    elif row[zip_col] == '93640':
        # Profile 3: 93640 Rural customer
        p = row.copy()
        p['Profile_Name'] = 'Poorer, Low EV Area (Rural Central Valley)'
        p['Baseline_Usage_kWh'] = 500
        p['Is_EV'] = False
        profiles.append(p)
        
    elif row[zip_col] == '90011':
        # Profile 4: 90011 Urban customer
        p = row.copy()
        p['Profile_Name'] = 'Working Class, Dense Urban (South LA)'
        p['Baseline_Usage_kWh'] = 450
        p['Is_EV'] = False
        profiles.append(p)

# Convert profiles list back into a DataFrame
df_profiles = pd.DataFrame(profiles)

# 4. Implement Elasticity
elasticity = -0.2

pct_change_price_S2 = (rates['S2_Volumetric'] - rates['S1_Volumetric']) / rates['S1_Volumetric']
pct_change_price_S3 = (rates['S3_Volumetric'] - rates['S1_Volumetric']) / rates['S1_Volumetric']

df_profiles['Usage_S1'] = df_profiles['Baseline_Usage_kWh']
df_profiles['Usage_S2'] = df_profiles['Baseline_Usage_kWh'] * (1 + (elasticity * pct_change_price_S2))
df_profiles['Usage_S3'] = df_profiles['Baseline_Usage_kWh'] * (1 + (elasticity * pct_change_price_S3))

# Calculate Peak vs Off-Peak kWh based on behavior
df_profiles['S1_Peak_kWh'] = df_profiles['Usage_S1'] * peak_ratio
df_profiles['S1_OffPeak_kWh'] = df_profiles['Usage_S1'] * offpeak_ratio

df_profiles['S2_Peak_kWh'] = df_profiles['Usage_S2'] * peak_ratio
df_profiles['S2_OffPeak_kWh'] = df_profiles['Usage_S2'] * offpeak_ratio

df_profiles['S3_Peak_kWh'] = df_profiles['Usage_S3'] * peak_ratio
df_profiles['S3_OffPeak_kWh'] = df_profiles['Usage_S3'] * offpeak_ratio

# 5. Calculate Annual Bills using TOU Rates
df_profiles['Annual_Bill_S1'] = (rates['S1_Fixed'] + (rates['S1_Peak'] * df_profiles['S1_Peak_kWh']) + (rates['S1_OffPeak'] * df_profiles['S1_OffPeak_kWh'])) * 12
df_profiles['Annual_Bill_S2'] = (rates['S2_Fixed'] + (rates['S2_Peak'] * df_profiles['S2_Peak_kWh']) + (rates['S2_OffPeak'] * df_profiles['S2_OffPeak_kWh'])) * 12

# Apply the appropriate fixed charge for Scenario 3 (EV vs Standard)
df_profiles['S3_Fixed_Applied'] = np.where(df_profiles['Is_EV'], rates['S3_Fixed_EV'], rates['S3_Fixed'])
df_profiles['Annual_Bill_S3'] = (df_profiles['S3_Fixed_Applied'] + (rates['S3_Peak'] * df_profiles['S3_Peak_kWh']) + (rates['S3_OffPeak'] * df_profiles['S3_OffPeak_kWh'])) * 12

# 6. Calculate Energy Burden
df_profiles['Burden_S1_pct'] = (df_profiles['Annual_Bill_S1'] / df_profiles['Avg_AGI']) * 100
df_profiles['Burden_S2_pct'] = (df_profiles['Annual_Bill_S2'] / df_profiles['Avg_AGI']) * 100
df_profiles['Burden_S3_pct'] = (df_profiles['Annual_Bill_S3'] / df_profiles['Avg_AGI']) * 100

# 7. Output the Results cleanly to the console
print("\n=== Scenario Comparison for Household Profiles ===")
for index, row in df_profiles.iterrows():
    print(f"\nProfile: {row['Profile_Name']} (Zip: {row[zip_col]})")
    print(f"Average Gross Income: ${row['Avg_AGI']:,.2f}")
    print(f"Assumed Baseline Usage: {row['Baseline_Usage_kWh']:.0f} kWh/month")
    
    if row['Is_EV']:
        print(f"Scenario 3 Charge Type: EV Level 2 Fixed Charge (${rates['S3_Fixed_EV']})")
    else:
        print(f"Scenario 3 Charge Type: Standard Fixed Charge (${rates['S3_Fixed']})")
    
    print(f"\n  Scenario 1 (Status Quo - Volumetric):")
    print(f"    - Usage w/ Elasticity: {row['Usage_S1']:.0f} kWh/month")
    print(f"    - Annual Bill: ${row['Annual_Bill_S1']:,.2f}")
    
    print(f"\n  Scenario 2 (Current CPUC):")
    print(f"    - Usage w/ Elasticity: {row['Usage_S2']:.0f} kWh/month")
    print(f"    - Annual Bill: ${row['Annual_Bill_S2']:,.2f}")
    
    print(f"\n  Scenario 3 (Optimized Fixed Charge):")
    print(f"    - Usage w/ Elasticity: {row['Usage_S3']:.0f} kWh/month")
    print(f"    - Annual Bill: ${row['Annual_Bill_S3']:,.2f}")
    print("-" * 55)