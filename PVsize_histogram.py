import pandas as pd
import matplotlib.pyplot as plt
import glob
import os

# === Step 1: Load and combine all CSVs ===
path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Interconnected_Project_Sites_2025-08-31 (2)'  # <-- update this path
# Get all CSV files but exclude aggregated CSVs
csv_files = [f for f in glob.glob(os.path.join(path, "*.csv"))
             if "pv_capacity_by_zip_up_to_2025_agg"  not in os.path.basename(f)]

dfs = []
for f in csv_files:
    df = pd.read_csv(f, low_memory=False)
    dfs.append(df)

combined = pd.concat(dfs, ignore_index=True)

# === Step 2: Keep only photovoltaic systems ===
combined = combined[combined["Technology Type"].str.contains("Photovoltaic", case=False, na=False)]

# === Step 3: Clean and convert system size column ===
combined["system_size_dc"] = pd.to_numeric(combined["System Size DC"], errors="coerce")

# Remove nulls and negative values (errors in data)
combined = combined[combined["system_size_dc"] > 0]

# === Step 4: Summary statistics ===
print("Total photovoltaic records:", len(combined))
summary = combined["system_size_dc"].describe(percentiles=[0.5, 0.9, 0.95, 0.99])
print("\nSummary statistics for system size (kW DC):")
print(summary)

# === Step 5: Plot histogram (focus on rooftop scale) ===
plt.figure(figsize=(8, 5))
plt.hist(combined[combined["system_size_dc"] < 100]["system_size_dc"], bins=100, color='skyblue', edgecolor='black')
plt.xlabel("System Size (kW DC)")
plt.ylabel("Count")
plt.title("Distribution of Rooftop Solar PV System Sizes (<100 kW)")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

# === Step 6: Optional – log scale histogram for full range ===
plt.figure(figsize=(8, 5))
plt.hist(combined["system_size_dc"], bins=200, color='orange', edgecolor='black', log=True)
plt.xlabel("System Size (kW DC)")
plt.ylabel("Log Count")
plt.title("Full Distribution of Solar PV System Sizes (log scale)")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()
