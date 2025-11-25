from transform import get_dataframes
import pandas as pd
import os

output_dir = "data_exports"
os.makedirs(output_dir, exist_ok=True)

dfs = get_dataframes()

for name, df in dfs.items():
    df.to_csv(os.path.join(output_dir, f"{name}.csv"), index=False)
