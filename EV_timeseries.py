import pandas as pd
import matplotlib.pyplot as plt

# ---------------- USER CONFIG ----------------
CSV_FILE = r'/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/DMV Count Expanded Years No Counties.csv'
START_YEAR = 1995  # earliest model year to show
# --------------------------------------------

# --- Step 1: Load CSV ---
df = pd.read_csv(CSV_FILE)

# --- Step 2: Clean columns ---
# Ensure Model Year is numeric (some may be <1992 etc.)
def parse_model_year(x):
    try:
        x = str(x).strip()
        if x.startswith('<'):
            return int(x[1:]) - 1  # e.g., '<1992' -> 1991
        return int(x)
    except:
        return None

df['Model_Year'] = df['Model Year'].apply(parse_model_year)
df['Vehicles'] = pd.to_numeric(df['Vehicles'], errors='coerce').fillna(0)

# --- Step 3: Filter to EVs and PHEVs ---
def is_ev(fuel):
    fuel = str(fuel).lower()
    return 'battery electric' in fuel

def is_phev(fuel):
    fuel = str(fuel).lower()
    return 'plug-in hybrid' in fuel or 'phev' in fuel

df = df[df['Fuel'].apply(lambda f: is_ev(f) or is_phev(f))]

# --- NEW: Only use Year 2023 to avoid duplicates ---
df = df[df['Year'] == 2023]

# --- DEBUG: check totals ---
total_all_vehicles = df['Vehicles'].sum()
print(f"Total EV + PHEVs in filtered dataset: {total_all_vehicles:,}")

# Optional: see cumulative table
print("\nCumulative EV + PHEVs by Model Year:")
agg_debug = df.groupby('Model_Year')['Vehicles'].sum().sort_index().cumsum().reset_index(name='Cumulative_Vehicles')
print(agg_debug)


# --- Step 4: Aggregate by model year ---
agg = df.groupby('Model_Year')['Vehicles'].sum().reset_index()

# --- Step 5: Sort by model year and calculate cumulative sum ---
agg = agg.sort_values('Model_Year')
agg['Cumulative_Vehicles'] = agg['Vehicles'].cumsum()

# --- Step 6: Filter for years >= START_YEAR ---
agg = agg[agg['Model_Year'] >= START_YEAR]

import matplotlib.ticker as mtick

# --- Step 7: Plot cumulative EV + PHEVs (scaled y-axis in thousands) ---
plt.figure(figsize=(10, 6))
plt.plot(
    agg['Model_Year'],
    agg['Cumulative_Vehicles'],
    marker='o',
    linewidth=2
)
plt.title('Cumulative EV + PHEV Registrations in California by Year')
plt.xlabel('Year', fontsize=14)
plt.ylabel('Cumulative Vehicles (Thousands)', fontsize=14)
plt.grid(True, alpha=0.3)
plt.xlim(agg['Model_Year'].min(), agg['Model_Year'].max())

# Scale y-axis to thousands
plt.gca().yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f'{int(x/1000):,}'))

plt.tight_layout()
plt.show()

# --- Optional: save processed cumulative data ---
agg.to_csv('ev_phev_cumulative_by_model_year.csv', index=False)
print("✅ Cumulative EV + PHEV data saved to ev_phev_cumulative_by_model_year.csv")
