
import pandas as pd
from sqlalchemy import create_engine

# Load CSV data
df = pd.read_csv('data/sales_data.csv')

# Data Cleaning
df.dropna(inplace=True)
df['order_id'] = df['order_id'].astype(int)
df['quantity'] = df['quantity'].astype(int)
df['price'] = df['price'].astype(float)

# Database connection
engine = create_engine('postgresql://postgres:postgresql@localhost:5432/retail_db')

# Load into PostgreSQL
df.to_sql('sales', engine, if_exists='append', index=False)

print("ETL process completed successfully.")
