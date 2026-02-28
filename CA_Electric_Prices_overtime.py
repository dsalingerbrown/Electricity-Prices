import pandas as pd
import matplotlib.pyplot as plt

# 1. Load the data
# We use 'skiprows' to bypass the empty/title rows at the top. 
# Looking at your image, the "Utility" header seems to be around row 2 or 3 (0-indexed). 
# You may need to change 'skiprows=2' to 1 or 3 depending on the exact file structure.
file_path = '/Users/dannysalingerbrown/Desktop/Electricity_Prices_Project/Data/HistoricalElectricCostData  08 09 2024  v 02 21 2025 v3.xlsx' 
df = pd.read_excel(file_path, skiprows=2)

# 2. Clean the data
# Drop completely empty columns (like the empty column A on the far left)
df = df.dropna(axis=1, how='all')

# Drop rows that don't have utility data (this removes the "Notes:" row at the bottom)
df = df.dropna(subset=['Utility'])

# 3. Reshape for plotting
# Set the 'Utility' column as the index so it doesn't get plotted as a normal data point
df.set_index('Utility', inplace=True)

# Transpose (.T) the dataframe so that Years become the rows (X-axis) 
# and Utilities become the columns (the different lines we want to draw)
df_plot = df.T

# 4. Create the Plot
plt.figure(figsize=(12, 6))

# Plot each utility's data
for utility in df_plot.columns:
    plt.plot(df_plot.index, df_plot[utility], marker='o', linewidth=2, label=utility)

# Formatting the chart
plt.title('Bundled System Average Rate (¢/kWh, January 1)', fontsize=14, pad=15)
plt.xlabel('Year', fontsize=12)
plt.ylabel('Rate (¢/kWh)', fontsize=12)
plt.legend(title='Utility')
plt.grid(True, linestyle='--', alpha=0.7)

# Ensure all years display nicely on the x-axis without overlapping
plt.xticks(df_plot.index, rotation=45) 
plt.tight_layout()

# Display the plot
plt.show()