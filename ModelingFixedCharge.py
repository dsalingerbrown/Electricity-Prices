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
target_zips = ['94025', '93640', '90011']
df_filtered = df[df[zip_col].isin(target_zips)].copy()
df_filtered = df_filtered.drop_duplicates(subset=[zip_col])

profiles = []
for index, row in df_filtered.iterrows():
    if row[zip_col] == '94025':
        p1, p2 = row.copy(), row.copy()
        p1['Profile_Name'], p1['Baseline_Usage_kWh'], p1['Is_EV'] = 'Silicon Valley (Has EV)', 800, True
        p2['Profile_Name'], p2['Baseline_Usage_kWh'], p2['Is_EV'] = 'Silicon Valley (No EV)', 500, False
        profiles.extend([p1, p2])
    elif row[zip_col] == '93640':
        p = row.copy()
        p['Profile_Name'], p['Baseline_Usage_kWh'], p['Is_EV'] = 'Rural CV (No EV)', 500, False
        profiles.append(p)
    elif row[zip_col] == '90011':
        p4, p5 = row.copy(), row.copy()
        p4['Profile_Name'], p4['Baseline_Usage_kWh'], p4['Is_EV'] = 'South LA (Has EV)', 750, True
        p5['Profile_Name'], p5['Baseline_Usage_kWh'], p5['Is_EV'] = 'South LA (No EV)', 450, False
        profiles.extend([p4, p5])

df_profiles = pd.DataFrame(profiles)

# 4. CALIBRATED WOLAK IMPLEMENTATION (Revenue Neutral)
hours_in_month = 730
df_profiles['Hourly_Mean_kW'] = df_profiles['Baseline_Usage_kWh'] / hours_in_month

# Adjusted Variance proxy to accurately reflect a Level 2 charger impact with 40% Coincidence Factor
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
pct_change_price_S2 = (rates['S2_Volumetric'] - rates['S1_Volumetric']) / rates['S1_Volumetric']
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
# 9. VISUALIZATION FOR PRESENTATION DECK
# =====================================================================

# Filter to just the EV vs Non-EV comparative zip codes
plot_df = df_profiles[df_profiles[zip_col].isin(['90011', '94025'])].copy()

# Sort the data so the bars appear in a logical order (South LA first, then Menlo Park)
plot_df = plot_df.sort_values(by=['Avg_AGI', 'Is_EV'])

# Extract values for the plot
labels = plot_df['Profile_Name'].tolist()
# Add line breaks to labels for cleaner formatting on the X-axis
labels = [label.replace(' (', '\n(') for label in labels] 

s1_bills = plot_df['Annual_Bill_S1'].values
s3_bills = plot_df['Annual_Bill_S3'].values

x = np.arange(len(labels))  # label locations
width = 0.35  # width of the bars

# Create the plot
fig, ax = plt.subplots(figsize=(11, 6.5))

rects1 = ax.bar(x - width/2, s1_bills, width, label='Scenario 1: Volumetric Rate (Status Quo)', color='#7f8c8d')
rects2 = ax.bar(x + width/2, s3_bills, width, label='Scenario 3: Better Fixed Charge Mechanism', color='#2980b9')

# Formatting
ax.set_ylabel('Total Annual Electricity Bill ($)', fontsize=12, fontweight='bold')
ax.set_title('Resolving the EV Cross-Subsidy:\nAnnual Bill Impacts by Household Profile', fontsize=14, fontweight='bold', pad=15)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=11)
ax.legend(fontsize=11, loc='upper left')
ax.grid(axis='y', linestyle='--', alpha=0.7)

# --- THE FIX: Add 25% headroom to the top of the chart so the legend doesn't overlap ---
max_bill = max(max(s1_bills), max(s3_bills))
ax.set_ylim(0, max_bill * 1.25) 

# Add numeric labels to the top of the bars
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'${height:,.0f}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

autolabel(rects1)
autolabel(rects2)

plt.tight_layout()

# Save the plot as a high-res PNG for your slide deck
plt.savefig('EV_Cross_Subsidy_Chart.png', dpi=300)
plt.show()