import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. Define the rate structures
rates = {
    'S1_Volumetric': 0.45, 'S1_Peak': 0.57, 'S1_OffPeak': 0.42, 'S1_Fixed': 0.0,
    'S2_Volumetric': 0.39, 'S2_Peak': 0.51, 'S2_OffPeak': 0.36, 'S2_Fixed': 24.15,
    'S3_Volumetric': 0.20, 'S3_Peak': 0.32, 'S3_OffPeak': 0.17
}

peak_ratio = 0.20
offpeak_ratio = 0.80

# 2. Load Your Data
df = pd.read_csv('/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Data/2024_personal_income_tax_statistics_by_zip_code.csv')
zip_col = 'ZipCode' 
df[zip_col] = df[zip_col].astype(str)
df = df[df['Avg_AGI'] > 0].copy()

# 3. Filter for target zip codes and REMOVE DUPLICATES
target_zips = ['94025', '90011'] # Just keeping the mapped ones for these plots
df_filtered = df[df[zip_col].isin(target_zips)].copy()
df_filtered = df_filtered.drop_duplicates(subset=[zip_col])

profiles = []
for index, row in df_filtered.iterrows():
    if row[zip_col] == '94025':
        p1, p2 = row.copy(), row.copy()
        p1['Profile_Name'], p1['Baseline_Usage_kWh'], p1['Is_EV'] = 'Silicon Valley\n(Has EV)', 800, True
        p2['Profile_Name'], p2['Baseline_Usage_kWh'], p2['Is_EV'] = 'Silicon Valley\n(No EV)', 500, False
        profiles.extend([p1, p2])
    elif row[zip_col] == '90011':
        p4, p5 = row.copy(), row.copy()
        p4['Profile_Name'], p4['Baseline_Usage_kWh'], p4['Is_EV'] = 'South LA\n(Has EV)', 750, True
        p5['Profile_Name'], p5['Baseline_Usage_kWh'], p5['Is_EV'] = 'South LA\n(No EV)', 450, False
        profiles.extend([p4, p5])

df_profiles = pd.DataFrame(profiles)
df_profiles = df_profiles.sort_values(by=['Avg_AGI', 'Is_EV'])

# 4. CALIBRATED WOLAK IMPLEMENTATION
hours_in_month = 730
df_profiles['Hourly_Mean_kW'] = df_profiles['Baseline_Usage_kWh'] / hours_in_month
df_profiles['Hourly_Variance'] = np.where(
    df_profiles['Is_EV'], 
    (df_profiles['Hourly_Mean_kW'] * 1.5) + 0.8, 
    (df_profiles['Hourly_Mean_kW'] * 1.5)        
)
df_profiles['Wolak_EEHWTP_Score'] = 0.5 * (df_profiles['Hourly_Variance'] + (df_profiles['Hourly_Mean_kW']**2))

distribution_cost_multiplier = 65.0 
df_profiles['S3_Capacity_Fixed'] = df_profiles['Wolak_EEHWTP_Score'] * distribution_cost_multiplier
df_profiles['S3_Customer_Access_Fixed'] = np.where(df_profiles['Avg_AGI'] > 50000, 75.0, 25.0)
df_profiles['S3_Applied_Fixed'] = df_profiles['S3_Customer_Access_Fixed'] + df_profiles['S3_Capacity_Fixed']

# 5. Implement Elasticity
elasticity = -0.2
pct_change_price_S3 = (rates['S3_Volumetric'] - rates['S1_Volumetric']) / rates['S1_Volumetric']

df_profiles['Usage_S1'] = df_profiles['Baseline_Usage_kWh']
df_profiles['Usage_S3'] = df_profiles['Baseline_Usage_kWh'] * (1 + (elasticity * pct_change_price_S3))

df_profiles['S1_Peak_kWh'] = df_profiles['Usage_S1'] * peak_ratio
df_profiles['S1_OffPeak_kWh'] = df_profiles['Usage_S1'] * offpeak_ratio
df_profiles['S3_Peak_kWh'] = df_profiles['Usage_S3'] * peak_ratio
df_profiles['S3_OffPeak_kWh'] = df_profiles['Usage_S3'] * offpeak_ratio

# 6. Calculate Annual Bills
df_profiles['Annual_Bill_S1'] = (rates['S1_Fixed'] + (rates['S1_Peak'] * df_profiles['S1_Peak_kWh']) + (rates['S1_OffPeak'] * df_profiles['S1_OffPeak_kWh'])) * 12
df_profiles['Annual_Bill_S3'] = (df_profiles['S3_Applied_Fixed'] + (rates['S3_Peak'] * df_profiles['S3_Peak_kWh']) + (rates['S3_OffPeak'] * df_profiles['S3_OffPeak_kWh'])) * 12

# =====================================================================
# VISUALIZATION 1: TOTAL ANNUAL BILLS
# =====================================================================
labels = df_profiles['Profile_Name'].tolist()
x = np.arange(len(labels))
width = 0.35  

s1_bills = df_profiles['Annual_Bill_S1'].values
s3_bills = df_profiles['Annual_Bill_S3'].values

fig1, ax1 = plt.subplots(figsize=(11, 6.5))
rects1 = ax1.bar(x - width/2, s1_bills, width, label='Scenario 1: Volumetric Rate (Status Quo)', color='#7f8c8d')
rects2 = ax1.bar(x + width/2, s3_bills, width, label='Scenario 3: Wolak Capacity + IGFC', color='#2980b9')

ax1.set_ylabel('Total Annual Electricity Bill ($)', fontsize=12, fontweight='bold')
ax1.set_title('Resolving the EV Cross-Subsidy:\nAnnual Bill Impacts by Household Profile', fontsize=14, fontweight='bold', pad=15)
ax1.set_xticks(x)
ax1.set_xticklabels(labels, fontsize=11)
ax1.legend(fontsize=11, loc='upper left')
ax1.grid(axis='y', linestyle='--', alpha=0.7)

max_bill = max(max(s1_bills), max(s3_bills))
ax1.set_ylim(0, max_bill * 1.25) 

def autolabel(ax, rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'${height:,.0f}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

autolabel(ax1, rects1)
autolabel(ax1, rects2)

fig1.tight_layout()
fig1.savefig('EV_Cross_Subsidy_Total_Bills.png', dpi=300)

# =====================================================================
# VISUALIZATION 2: RATE MECHANICS (VOLUMETRIC VS FIXED)
# =====================================================================
fig2, (ax_vol, ax_fix) = plt.subplots(1, 2, figsize=(14, 6))

# --- PANEL 1: Volumetric Rates ---
scenarios = ['Scenario 1\n(Status Quo)', 'Scenario 2\n(Current CPUC)', 'Scenario 3\n(Optimized)']
peak_rates = [rates['S1_Peak'], rates['S2_Peak'], rates['S3_Peak']]
offpeak_rates = [rates['S1_OffPeak'], rates['S2_OffPeak'], rates['S3_OffPeak']]

x_scen = np.arange(len(scenarios))

rects_peak = ax_vol.bar(x_scen - width/2, peak_rates, width, label='Peak Rate', color='#e74c3c')
rects_off = ax_vol.bar(x_scen + width/2, offpeak_rates, width, label='Off-Peak Rate', color='#3498db')

ax_vol.set_ylabel('Price per kWh ($)', fontsize=12, fontweight='bold')
ax_vol.set_title('Volumetric Energy Rates', fontsize=14, fontweight='bold', pad=15)
ax_vol.set_xticks(x_scen)
ax_vol.set_xticklabels(scenarios, fontsize=11)
ax_vol.legend(fontsize=11)
ax_vol.grid(axis='y', linestyle='--', alpha=0.7)
ax_vol.set_ylim(0, max(peak_rates) * 1.25)

for rect in rects_peak + rects_off:
    height = rect.get_height()
    ax_vol.annotate(f'${height:.2f}',
                xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points",
                ha='center', va='bottom', fontsize=10, fontweight='bold')

# --- PANEL 2: Fixed Monthly Charges ---
s1_fixed = [rates['S1_Fixed']] * 4
s2_fixed = [rates['S2_Fixed']] * 4
s3_fixed = df_profiles['S3_Applied_Fixed'].tolist()

width2 = 0.25
rects_s1 = ax_fix.bar(x - width2, s1_fixed, width2, label='Scenario 1', color='#95a5a6')
rects_s2 = ax_fix.bar(x, s2_fixed, width2, label='Scenario 2', color='#7f8c8d')
rects_s3 = ax_fix.bar(x + width2, s3_fixed, width2, label='Scenario 3', color='#f39c12')

ax_fix.set_ylabel('Monthly Fixed Charge ($)', fontsize=12, fontweight='bold')
ax_fix.set_title('Fixed Distribution Charges by Profile', fontsize=14, fontweight='bold', pad=15)
ax_fix.set_xticks(x)
ax_fix.set_xticklabels(labels, fontsize=11)
ax_fix.legend(fontsize=11, loc='upper left')
ax_fix.grid(axis='y', linestyle='--', alpha=0.7)
ax_fix.set_ylim(0, max(s3_fixed) * 1.25)

for rects in [rects_s1, rects_s2, rects_s3]:
    for rect in rects:
        height = rect.get_height()
        if height > 0:  
            ax_fix.annotate(f'${height:.0f}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=10, fontweight='bold')

fig2.suptitle('Rebalancing the Grid: Shifting from Volumetric Rate to Better Fixed Charge', fontsize=16, fontweight='bold', y=1.05)
fig2.tight_layout()
fig2.savefig('Rate_Mechanics_Comparison.png', dpi=300, bbox_inches='tight')

# Display both figures
plt.show()