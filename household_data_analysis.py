import json

# === 1. Load the JSON file ===
with open("/Users/dannysalingerbrown/Downloads/acs5.json", "r") as f:
    data = json.load(f)

columns = data[0]
print("Columns:", columns)

# === 2. Skip the header row ===
rows = data[1:]

# === 3. Sum up the second column ===
total = sum(int(row[1]) for row in rows if row[1].isdigit())

print(f"Total of second column: {total:,}")
