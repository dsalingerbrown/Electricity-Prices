import pandas as pd
import glob
import os

# === Folder with your raw PV CSVs ===
path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Interconnected_Project_Sites_2025-08-31 (2)'  # <- update this path

# Load all CSVs, excluding aggregated CSVs
csv_files = [f for f in glob.glob(os.path.join(path, "*.csv"))
             if "pv_capacity_by_zip_up_to_2025_agg" not in os.path.basename(f)]

dfs = []
for f in csv_files:
    df = pd.read_csv(f, low_memory=False)
    dfs.append(df)

combined = pd.concat(dfs, ignore_index=True)

# Keep only Photovoltaic systems
combined = combined[combined["Technology Type"].str.contains("Photovoltaic", case=False, na=False)]

# Convert system size to numeric, ignore errors
combined["system_size_dc"] = pd.to_numeric(combined["System Size DC"], errors="coerce")

# Remove missing or invalid values (negative or zero)
combined = combined[combined["system_size_dc"] > 0]

# === Sort by system size, largest first ===
sorted_df = combined.sort_values(by="system_size_dc", ascending=False)

# Select the top 20 largest interconnections
top50 = sorted_df[["System Size DC", "Service Zip", "Service County", "App Approved Date", "Customer Sector"]].head(50)

# Print to console (optional)
print(top50)

output_folder = '/Users/dannysalingerbrown/Desktop/VehicleFuelTypeData'

# === Export to CSV ===
out_csv = os.path.join(output_folder, "top50_largest_pv_systems.csv")
top50.to_csv(out_csv, index=False)
print(f"Saved top 50 largest interconnections to {out_csv}")

# # === Optional: Export to Excel ===
# out_excel = os.path.join(path, "top50_largest_pv_systems.xlsx")
# top50.to_excel(out_excel, index=False)
# print(f"Saved top 50 largest interconnections to {out_excel}")
