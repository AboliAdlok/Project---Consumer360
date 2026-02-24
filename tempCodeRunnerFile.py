import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
import seaborn as sns
from lifetimes import BetaGeoFitter
from lifetimes import GammaGammaFitter
from lifetimes.utils import summary_data_from_transaction_data
from mlxtend.frequent_patterns import apriori, association_rules

# Load dataset
df = pd.read_csv("online_retail_raw.csv", encoding='latin1')

# Convert to datetime
df['invoicedate'] = pd.to_datetime(df['invoicedate'])

# Cleaning steps
df = df[df['customerid'].notna()]
df = df[df['quantity'] > 0]
df = df[df['unitprice'] > 0]

# Create Revenue column (if not already present)
df['revenue'] = df['quantity'] * df['unitprice']

# Create snapshot date
snapshot_date = df['invoicedate'].max() + dt.timedelta(days=1)

# Create RFM table
rfm = df.groupby('customerid').agg({
    'invoicedate': lambda x: (snapshot_date - x.max()).days,
    'invoiceno': 'nunique',
    'revenue': 'sum'
})

# Rename columns
rfm.columns = ['Recency', 'Frequency', 'Monetary']

# Reset index
rfm = rfm.reset_index()

# Display result
print(rfm.head())
print(rfm.describe())

#create RFM score
rfm['R_score'] = pd.qcut(rfm['Recency'], 5, labels=[5,4,3,2,1])
rfm['F_score'] = pd.qcut(rfm['Frequency'].rank(method='first'), 5, labels=[1,2,3,4,5])
rfm['M_score'] = pd.qcut(rfm['Monetary'], 5, labels=[1,2,3,4,5])

rfm['RFM_Score'] = rfm['R_score'].astype(str) + \
                   rfm['F_score'].astype(str) + \
                  rfm['M_score'].astype(str)

print(rfm.head())

# Segment customers based on RFM score
def segment_customer(row):
    r = int(row['R_score'])
    f = int(row['F_score'])
    m = int(row['M_score'])

    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    elif r >= 3 and f >= 3:
        return "Loyal Customers"
    elif r <= 2 and f <= 2:
        return "Churn Risk"
    elif r == 5:
        return "New Customers"
    else:
        return "Regular"

rfm['Segment'] = rfm.apply(segment_customer, axis=1)

# SEGMENT VALIDATION 
print(rfm.groupby('Segment')['Recency'].mean())
print(rfm.groupby('Segment')['Frequency'].mean())
print(rfm.groupby('Segment')['Monetary'].mean())

# Display segments
print(rfm[['customerid', 'RFM_Score', 'Segment']].head())

# Count of customers in each segment
print(rfm['Segment'].value_counts())

# Total revenue by segment
segment_revenue = rfm.groupby('Segment')['Monetary'].sum()
print(segment_revenue)

# Plotting the distribution of segments
# rfm['Segment'].value_counts().plot(kind='bar')
# plt.show()
# Count customers in each segment
segment_counts = rfm['Segment'].value_counts()

# Create bar chart
plt.figure(figsize=(8,5))
plt.bar(segment_counts.index, segment_counts.values)

# Add title and labels
plt.title("Customer Segment Distribution")
plt.xlabel("Segment")
plt.ylabel("Number of Customers")

# Rotate x labels for clarity
plt.xticks(rotation=10)

# Show plot
plt.show()

# ---- Cohort Analysis ----
df['InvoiceMonth'] = df['invoicedate'].dt.to_period('M')

cohort = df.groupby('customerid')['InvoiceMonth'].min()
df['CohortMonth'] = df['customerid'].map(cohort)

# Create Cohort Index (Month Difference)
df['CohortIndex'] = (
    (df['InvoiceMonth'].dt.year - df['CohortMonth'].dt.year) * 12 +
    (df['InvoiceMonth'].dt.month - df['CohortMonth'].dt.month) + 1
)

# Create retention table
cohort_data = df.groupby(['CohortMonth', 'CohortIndex'])['customerid'].nunique().reset_index()

cohort_pivot = cohort_data.pivot_table(
    index='CohortMonth',
    columns='CohortIndex',
    values='customerid'
)

# Calculate retention %
cohort_size = cohort_pivot.iloc[:, 0]
retention = cohort_pivot.divide(cohort_size, axis=0)

print(retention)

# Plot retention heatmap
plt.figure(figsize=(12,8))
sns.heatmap(retention, annot=False, cmap='Blues')
plt.title("Customer Retention Cohort Analysis")
plt.show()

# CLV MODEL
summary = summary_data_from_transaction_data(
    df,
    customer_id_col='customerid',
    datetime_col='invoicedate',
    monetary_value_col='revenue',
    observation_period_end=df['invoicedate'].max()
)

print(summary.head())

# Remove customers with zero frequency
#Filter Required Customers
summary = summary[summary['frequency'] > 0]

# Fit BG/NBD Model
bgf = BetaGeoFitter(penalizer_coef=0.01)
bgf.fit(summary['frequency'], summary['recency'], summary['T'])

# Predict Purchases (Next 30 Days)
summary['predicted_purchases_30days'] = bgf.predict(
    30,
    summary['frequency'],
    summary['recency'],
    summary['T']
)

# Fit Gamma-Gamma Model for Monetary Value
ggf = GammaGammaFitter(penalizer_coef=0.01)
ggf.fit(summary['frequency'], summary['monetary_value'])

# Calculate 12-Month CLV
summary['CLV_12months'] = ggf.customer_lifetime_value(
    bgf,
    summary['frequency'],
    summary['recency'],
    summary['T'],
    summary['monetary_value'],
    time=12,
    discount_rate=0.01
)

print(summary[['predicted_purchases_30days', 'CLV_12months']].head())

# Visualize CLV Distribution
import matplotlib.pyplot as plt

# Remove extreme outliers for better visualization (optional but recommended)
import seaborn as sns

clv_data = summary['CLV_12months']
clv_data = clv_data[clv_data < clv_data.quantile(0.99)]

plt.figure(figsize=(10,6))
sns.histplot(clv_data, bins=50, kde=True)
plt.title("Customer Lifetime Value Distribution (12 Months)")
plt.xlabel("CLV")
plt.ylabel("Number of Customers")
plt.show()

# Market Basket Analysis (Association Rules)
# Clean Data (Important Before Basket)
# Remove missing customer IDs
df = df[df['customerid'].notna()]

# Remove cancelled invoices (InvoiceNo starting with 'C')
df = df[~df['invoiceno'].astype(str).str.startswith('C')]

# Keep only positive quantity
df = df[df['quantity'] > 0]

# Create Basket Matrix (Proper Version)
# Create basket (Invoice × Product)
basket = (df
          .groupby(['invoiceno', 'stockcode'])['quantity']
          .sum()
          .unstack()
          .fillna(0))

# Convert to binary (1 if purchased, else 0)
basket = basket > 0

# Reduce Product Size (Very Important)
top_products = df['stockcode'].value_counts().head(100).index
basket = basket[top_products]

# Run Apriori Algorithm
frequent_items = apriori(
    basket,
    min_support=0.02,   # Adjust if too few/many rules
    use_colnames=True,
    max_len=2
)

# Generate Association Rules (Proper Version)
rules = association_rules(
    frequent_items,
    metric="lift",      # Lift is better than confidence alone
    min_threshold=1     # Lift > 1 means useful rule
)

# Clean & Sort Rules (Professional Output)
rules = rules.sort_values(by=['lift', 'confidence'], ascending=False)

# Select important columns
rules = rules[['antecedents', 'consequents',
               'support', 'confidence', 'lift']]

# print(rules.head(10))

# Convert frozensets to strings for better readability
rules['antecedents'] = rules['antecedents'].apply(lambda x: list(x)[0])
rules['consequents'] = rules['consequents'].apply(lambda x: list(x)[0])

print(rules.head(10))

# Map stock codes to product names for better interpretation
product_lookup = df[['stockcode', 'description']].drop_duplicates()

rules = rules.merge(product_lookup, left_on='antecedents', right_on='stockcode')
rules = rules.rename(columns={'description': 'Antecedent_Name'}).drop('stockcode', axis=1)

rules = rules.merge(product_lookup, left_on='consequents', right_on='stockcode')
rules = rules.rename(columns={'description': 'Consequent_Name'}).drop('stockcode', axis=1)

print(rules[['Antecedent_Name','Consequent_Name','support','confidence','lift']].head())