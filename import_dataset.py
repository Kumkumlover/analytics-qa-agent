import os
import kagglehub
import pandas as pd
import sqlite3
import glob

def download_and_import():
    print("Downloading dataset from Kaggle...")
    os.environ['KAGGLE_API_TOKEN'] = 'KGAT_5a79ac7fafe7cbb46c03a93226277bf6'
    
    path = kagglehub.dataset_download("wafaaelhusseini/e-commerce-transactions-clickstream")
    print(f"Dataset downloaded to: {path}")

    db_path = "analytics.db"
    conn = sqlite3.connect(db_path)
    
    csv_files = glob.glob(os.path.join(path, "*.csv"))
    if not csv_files:
        print("No CSV files found in the dataset.")
        return
        
    for csv_file in csv_files:
        table_name = os.path.basename(csv_file).replace('.csv', '')
        print(f"Importing {csv_file} into table '{table_name}'...")
        
        df = pd.read_csv(csv_file)
        df.columns = [c.strip().replace(' ', '_').lower() for c in df.columns]
        
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"Successfully imported {len(df)} rows into '{table_name}'.")

    conn.close()
    print(f"All data imported into {db_path} successfully.")

if __name__ == "__main__":
    download_and_import()
