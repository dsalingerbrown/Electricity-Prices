import pandas as pd
import glob
import os

# ---------------- USER CONFIG ----------------
national_path = "/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/TTS_LBNL_public_file_29-Sep-2025_all.csv"
CA_FOLDER = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Interconnected_Project_Sites_2025-08-31 (2)'
matched_out_csv = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/CA_national_matched.csv'
chunk_size = 100_000  # adjust based on available RAM
# --------------------------------------------

# === Step 1: Load and combine CA data (all CSVs) ===
ca_paths = glob.glob(os.path.join(CA_FOLDER, "*.csv"))
ca_cols = ['Service Zip', 'App Approved Date', 'System Size DC']
ca_dfs = []

for path in ca_paths:
    df = pd.read_csv(path, usecols=ca_cols, low_memory=False)
    df.rename(columns={'Service Zip': 'zip_code',
                       'App Approved Date': 'installation_date',
                       'System Size DC': 'system_size_dc'}, inplace=True)
    
    # Convert types
    df['zip_code'] = df['zip_code'].astype(str).str.zfill(5)
    df['system_size_dc'] = pd.to_numeric(df['system_size_dc'], errors='coerce').astype('float32')
    df['installation_date'] = pd.to_datetime(df['installation_date'], errors='coerce', infer_datetime_format=True)
    
    ca_dfs.append(df)

ca_combined = pd.concat(ca_dfs, ignore_index=True)
print(f"Combined CA dataset: {len(ca_combined):,} rows")

# Optional: aggregate CA by zip + installation_date + system_size
# (If exact duplicate system IDs exist, this prevents memory blow-up)
ca_combined['zip_date_size'] = (
    ca_combined['zip_code'] + '_' +
    ca_combined['installation_date'].dt.strftime('%Y-%m-%d') + '_' +
    ca_combined['system_size_dc'].astype(str)
)
ca_combined_set = set(ca_combined['zip_date_size'])

# === Step 2: Process national dataset in chunks ===
national_cols = ['zip_code', 'installation_date', 'PV_system_size_DC', 'third_party_owned']
matched_rows = 0
first_chunk = True

for chunk in pd.read_csv(national_path, usecols=national_cols, chunksize=chunk_size, low_memory=False):
    # Convert types
    chunk['zip_code'] = chunk['zip_code'].astype(str).str.zfill(5)
    chunk['PV_system_size_DC'] = pd.to_numeric(chunk['PV_system_size_DC'], errors='coerce').astype('float32')
    chunk['installation_date'] = pd.to_datetime(chunk['installation_date'], errors='coerce', infer_datetime_format=True)
    
    # Create the same 'zip_date_size' key for matching
    chunk['zip_date_size'] = (
        chunk['zip_code'] + '_' +
        chunk['installation_date'].dt.strftime('%Y-%m-%d') + '_' +
        chunk['PV_system_size_DC'].astype(str)
    )
    
    # Keep only rows that exist in CA dataset
    matched_chunk = chunk[chunk['zip_date_size'].isin(ca_combined_set)].copy()
    matched_rows += len(matched_chunk)
    
    # Drop helper column before saving
    matched_chunk.drop(columns=['zip_date_size'], inplace=True)
    
    # Save incrementally
    if first_chunk:
        matched_chunk.to_csv(matched_out_csv, index=False)
        first_chunk = False
    else:
        matched_chunk.to_csv(matched_out_csv, mode='a', header=False, index=False)
    
    print(f"Processed chunk, matched {len(matched_chunk):,} rows so far. Total matched: {matched_rows:,}")

print(f"\n✅ Finished! Total matched rows: {matched_rows:,}")
print(f"Saved matched CSV to {matched_out_csv}")
