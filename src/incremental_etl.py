import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging

# Load DB credentials
load_dotenv()
db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
print("DB URL:", db_url)
try:
    engine = create_engine(db_url)
    print("Database engine created successfully!")
    # Test connection immediately
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("Successfully connected to the database!")
except Exception as e:
    print(f"Error connecting to database: {e}")
    logging.error(f"Database connection error: {e}")
    # Exit or raise the exception if connection is critical
    exit(1)


# Create logs directory safely
project_root = os.path.dirname(os.path.dirname(__file__))  # one level up from /src
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'etl.log')

# Setup logging
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(message)s')

data_folder = 'data/daily'
processed_folder = 'data/processed'

# Get existing order_ids
def get_existing_ids():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT order_id FROM sales"))
        rows = result.fetchall()
        print(f"results: {rows}")
        return set(row[0] for row in rows)
existing_ids = get_existing_ids()
print(f"Existing IDs in database: {existing_ids}")

# Ensure folders exist
os.makedirs(data_folder, exist_ok=True)
os.makedirs(processed_folder, exist_ok=True)


# Process each CSV file
for filename in os.listdir(data_folder):
    if filename.endswith('.csv'):
        filepath = os.path.join(data_folder, filename)
        print(f"file path: {filepath}")
        try:
            df = pd.read_csv(filepath)
            print(f"Shape before dropna: {df.shape}")
            df.dropna(inplace=True)
            print(f"Shape after dropna: {df.shape}")
            df['order_id'] = df['order_id'].astype(int)

            new_rows = df[~df['order_id'].isin(existing_ids)]

            inserted = 0
            skipped = len(df) - len(new_rows)
            errors = 0

            if not new_rows.empty:
                try:
                    new_rows.to_sql('sales', con=engine, if_exists='append', index=False)
                    inserted = len(new_rows)
                    existing_ids.update(new_rows['order_id'].tolist())
                except Exception as e:
                    errors = len(new_rows)
                    logging.error(f"Error inserting data from {filename}: {e}")

            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO audit_log (file_name, records_inserted, records_skipped, errors_encountered)
                    VALUES (:file, :ins, :skip, :err)
                """), {
                    'file': filename,
                    'ins': inserted,
                    'skip': skipped,
                    'err': errors
                })

            logging.info(f"{filename}: Inserted={inserted}, Skipped={skipped}, Errors={errors}")

            os.rename(filepath, os.path.join(processed_folder, filename))

        except Exception as e:
            logging.error(f"Failed to process {filename}: {e}")
