import pandas as pd
import numpy as np
import datetime as dt

# Load CSV file
df = pd.read_csv("online_retail_raw.csv")

# Show first 5 rows
print(df.head())