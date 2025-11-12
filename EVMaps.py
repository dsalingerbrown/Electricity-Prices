import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import glob
import os
import re

# === Step 1: load and combine all yearly CSVs ===
path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/EVShareData(2019-2025)'  # folder containing 2019–2025 CSVs
files = sorted(glob.glob(os.path.join(path, "*.csv")))

dfs = []
for file in files:
    match = re.search(r'20\d{2}', os.path.basename(file))
    if match:
        year = int(match.group())
    else:
        print(f"⚠️ Could not find year in filename: {file}")
        continue

    df = pd.read_csv(file)

    zip_col = None
    for col in df.columns:
        if col.lower() == 'zip code':
            zip_col = col
            break
    if zip_col is None:
        print(f"⚠️ No ZIP column found in {file}")
        continue

    df.rename(columns={zip_col: 'Zip Code'}, inplace=True)
    df['Zip Code'] = df['Zip Code'].astype(str)
    
    df['Year'] = year
    dfs.append(df)

data = pd.concat(dfs, ignore_index=True)

# === DEBUG CHECK ===
print("Unique years in raw data:", sorted(data['Year'].unique()))

for year in [2024, 2025]:
    df = data[data['Year'] == year]
    print(f"\nYear {year}: {len(df)} rows")
    print("Sample ZIPs:", df['Zip Code'].head())
    print("Vehicles summary:", df['Vehicles'].describe())

# === Step 2: clean and standardize ===
data['Zip Code'] = data['Zip Code'].astype(str).str.replace(r'\D', '', regex=True).str[:5]
data = data[data['Zip Code'].str.len() == 5]

data['Fuel'] = data['Fuel'].str.strip()
data['Vehicles'] = pd.to_numeric(data['Vehicles'], errors='coerce').fillna(0)

# === Step 3: aggregate per ZIP and year ===
agg = data.groupby(['Year', 'Zip Code', 'Fuel'], as_index=False)['Vehicles'].sum()

# === Step 4: EV + PHEV classification ===
def is_ev(fuel):
    fuel = fuel.lower()
    return 'battery electric' in fuel

def is_phev(fuel):
    fuel = fuel.lower()
    return 'plug-in hybrid' in fuel or 'phev' in fuel

agg['is_ev'] = agg['Fuel'].apply(is_ev)
agg['is_phev'] = agg['Fuel'].apply(is_phev)

# Totals
zip_totals = agg.groupby(['Year', 'Zip Code'], as_index=False)['Vehicles'].sum().rename(columns={'Vehicles': 'Total'})

# BEVs only
zip_evs = agg.loc[agg['is_ev']].groupby(['Year', 'Zip Code'], as_index=False)['Vehicles'].sum().rename(columns={'Vehicles': 'BEVs'})

# PHEVs only
zip_phevs = agg.loc[agg['is_phev']].groupby(['Year', 'Zip Code'], as_index=False)['Vehicles'].sum().rename(columns={'Vehicles': 'PHEVs'})

# Merge all
ev_share = zip_totals.merge(zip_evs, on=['Year', 'Zip Code'], how='left') \
                     .merge(zip_phevs, on=['Year', 'Zip Code'], how='left')

ev_share[['BEVs','PHEVs']] = ev_share[['BEVs','PHEVs']].fillna(0)

# BEV-only share (existing metric)
ev_share['EV_Share'] = ev_share['BEVs'] / ev_share['Total']

# === NEW METRICS: BEV + PHEV ===
ev_share['EV_PHEV_Total'] = ev_share['BEVs'] + ev_share['PHEVs']
ev_share['EV_PHEV_Share'] = ev_share['EV_PHEV_Total'] / ev_share['Total']

# === Step 5: join with ZIP shapefile ===
zcta = gpd.read_file('/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/tl_2025_us_zcta520/tl_2025_us_zcta520.shp')
zcta = zcta.rename(columns={'ZCTA5CE20': 'Zip Code'})
zcta['Zip Code'] = zcta['Zip Code'].astype(str).str.zfill(5)

# California filter
zcta = zcta[(zcta['Zip Code'] >= '90000') & (zcta['Zip Code'] <= '96199')]

valid_zips = set(zcta['Zip Code'])
before_count = len(ev_share)
ev_share = ev_share[ev_share['Zip Code'].isin(valid_zips)]
after_count = len(ev_share)
print(f"Filtered ev_share: {before_count} -> {after_count}")

# Save updated long-form CSV
ev_share.to_csv('ev_share_long.csv', index=False)
print("✅ Updated ev_share_long.csv saved (now includes BEVs, PHEVs, EV_PHEV_Share)")

# Preview pivot table
pivot_ev = ev_share.pivot_table(index='Zip Code', columns='Year', values='EV_Share')
pivot_ev = pivot_ev.sort_values(by=pivot_ev.columns.max(), ascending=False)
pivot_ev.to_csv('ev_share_pivot_by_zip.csv')

# === Step 6: mapping ===
zcta = zcta.to_crs(epsg=3310)

vmin = 0
vmax = 0.22

# --- MAPS FOR BEV SHARE (existing) ---
for year in sorted(ev_share['Year'].unique()):
    df_year = ev_share[ev_share['Year'] == year]
    gdf = zcta.merge(df_year, on='Zip Code', how='left')

    filename = f"ev_share_{year}.png"
    if os.path.exists(filename):
        os.remove(filename)

    fig, ax = plt.subplots(figsize=(10,12))
    gdf.plot(column='EV_Share', cmap='YlGnBu', linewidth=0.5, edgecolor='grey',
             legend=True, vmin=vmin, vmax=vmax,
             missing_kwds={'color': 'lightgrey', 'label': 'No data'},
             ax=ax)
    ax.set_title(f"EV Share by ZIP Code in California ({year})", fontsize=16)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close()

# --- NEW MAPS: BEV + PHEV SHARE ---
for year in sorted(ev_share['Year'].unique()):
    df_year = ev_share[ev_share['Year'] == year]
    gdf = zcta.merge(df_year, on='Zip Code', how='left')

    filename = f"ev_phev_share_{year}.png"
    if os.path.exists(filename):
        os.remove(filename)

    fig, ax = plt.subplots(figsize=(10,12))
    gdf.plot(column='EV_PHEV_Share', cmap='YlGnBu', linewidth=0.5, edgecolor='grey',
             legend=True, vmin=vmin, vmax=vmax,
             missing_kwds={'color': 'lightgrey', 'label': 'No data'},
             ax=ax)
    ax.set_title(f"EV + PHEV Share by ZIP Code in California ({year})", fontsize=16)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close()

print("✅ All BEV and EV+PHEV maps created.")
