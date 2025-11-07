import os
import gc
import pandas as pd
from sqlalchemy import create_engine

# -----------------------------
# Configuration
# -----------------------------
data_dir = "../data/"
files = {
    "business": "yelp_academic_dataset_business.json",
    "checkin":  "yelp_academic_dataset_checkin.json",
    "review":   "yelp_academic_dataset_review.json",
    "tip":      "yelp_academic_dataset_tip.json",
    "user":     "yelp_academic_dataset_user.json"
}

# Optional: columns to keep for memory efficiency
cols = {
    "business": ["business_id", "name", "city", "state", "stars", "review_count", "categories"],
    "checkin":  ["business_id", "date"],
    "review":   ["review_id", "user_id", "business_id", "stars", "date"],
    "tip":      ["user_id", "business_id", "text", "date"],
    "user":     ["user_id", "name", "review_count", "yelping_since", "fans"]
}

# -----------------------------
# SQLAlchemy engine
# -----------------------------
# Example for SQLite
# engine = create_engine('sqlite:///yelp.db')
# Example for MySQL
# engine = create_engine('mysql+pymysql://user:password@host:port/dbname')

# -----------------------------
# Function: Load JSON with optional chunking
# -----------------------------
def read_yelp_json(file_path, selected_cols=None, chunksize=None):
    """
    Reads a JSON Lines file and optionally filters columns.
    Supports chunked reading for very large files.
    """
    if chunksize:
        chunks = pd.read_json(file_path, lines=True, chunksize=chunksize, encoding='utf-8')
        df = pd.concat([chunk[selected_cols] for chunk in chunks], ignore_index=True) if selected_cols else pd.concat(chunks, ignore_index=True)
    else:
        df = pd.read_json(file_path, lines=True, encoding='utf-8')
        if selected_cols:
            df = df[selected_cols]
    return df.convert_dtypes(dtype_backend="pyarrow")

# -----------------------------
# Function: Load JSON to SQL in chunks
# -----------------------------
def load_json_to_sql(file_path, table_name, engine, selected_cols=None, chunksize=50_000, if_exists='replace'):
    """
    Reads a JSON Lines file in chunks and writes to SQL efficiently.
    """
    total_rows = 0
    for i, chunk in enumerate(pd.read_json(file_path, lines=True, chunksize=chunksize, encoding='utf-8')):
        if selected_cols:
            chunk = chunk[selected_cols]
        chunk.to_sql(
            table_name,
            con=engine,
            if_exists='append' if i > 0 else if_exists,
            index=False,
            method='multi',
            chunksize=chunksize
        )
        total_rows += len(chunk)
        gc.collect()
        print(f"Chunk {i+1}: Loaded {len(chunk):,} rows (Total: {total_rows:,}) into '{table_name}'.")

    print(f"Finished loading '{table_name}' with {total_rows:,} rows.")

# -----------------------------
# Load all Yelp datasets
# -----------------------------
for table_name, file_name in files.items():
    file_path = os.path.join(data_dir, file_name)
    if os.path.exists(file_path):
        load_json_to_sql(file_path, table_name, engine, selected_cols=cols.get(table_name), chunksize=50_000)
    else:
        print(f"File not found: {file_path}")
