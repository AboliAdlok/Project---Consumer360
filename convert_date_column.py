import pandas as pd
import numpy as np
import datetime as dt

# Load CSV file
df = pd.read_csv("online_retail_raw.csv")

# Convert InvoiceDate column to datetime
df['invoicedate'] = pd.to_datetime(df['invoicedate'])

# Check structure
print(df.info())
print(df.head())
print(df.columns)




