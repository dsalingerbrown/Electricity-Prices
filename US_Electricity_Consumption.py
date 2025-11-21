import pandas as pd
import matplotlib.pyplot as plt

# Load CSV properly
df = pd.read_csv(
    "/Users/dannysalingerbrown/Downloads/retail-major-sectors.csv",
    skiprows=5,    # skip metadata
)

# Rename columns
df = df.rename(columns={
    df.columns[0]: "year",
    df.columns[5]: "direct_use"
})

# Convert year to integer
df["year"] = df["year"].astype(int)

# Compute total electricity consumption
df["total_consumption"] = (
    df["industrial"]
    + df["commercial"]
    + df["residential"]
    + df["transportation"]
    + df["direct_use"]
)

# Convert total_consumption to terawatt-hours
df["total_consumption_TWh"] = df["total_consumption"] * 1000

# Plot the line graph
plt.figure(figsize=(12, 6))
plt.plot(df["year"], df["total_consumption_TWh"], linewidth=2, color="red")

plt.title("Annual U.S. Electricity Consumption (1950–2022)", fontsize=16)
plt.xlabel("Year", fontsize=14)
plt.ylabel("Terawatt Hours", fontsize=14)

plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
