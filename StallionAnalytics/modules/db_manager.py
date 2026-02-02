import duckdb
import pandas as pd
import streamlit as st
import re

class StallionDB:
    """
    The High-Performance Data Engine.
    Wraps DuckDB to handle large datasets and multiple tables efficiently.
    """
    
    def __init__(self):
        # In-memory database for the session
        self.conn = duckdb.connect(database=':memory:')
        self.table_names = []

    def ingest_data(self, uploaded_files):
        """
        Streams multiple files into DuckDB tables.
        Returns: (Error_String, Success_Message_String)
        """
        self.table_names = [] # Reset table list
        messages = []
        
        # Ensure input is a list (Streamlit returns a single object if only 1 file, unless accept_multiple_files=True is handled carefully)
        if not isinstance(uploaded_files, list):
            uploaded_files = [uploaded_files]

        try:
            for file in uploaded_files:
                # Sanitize table name (remove extension, spaces -> underscores, lowercase)
                clean_name = re.sub(r'\W+', '_', file.name.split('.')[0]).lower()
                
                # Save temp file for DuckDB to read
                file_path = f"temp_{clean_name}"
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())

                # Determine loader based on extension
                if file.name.endswith('.csv'):
                    query = f"CREATE OR REPLACE TABLE {clean_name} AS SELECT * FROM read_csv_auto('{file_path}', normalize_names=True)"
                elif file.name.endswith('.json'):
                    query = f"CREATE OR REPLACE TABLE {clean_name} AS SELECT * FROM read_json_auto('{file_path}')"
                elif file.name.endswith('.parquet'):
                    query = f"CREATE OR REPLACE TABLE {clean_name} AS SELECT * FROM read_parquet('{file_path}')"
                else:
                    return f"Unsupported format: {file.name}", None

                self.conn.execute(query)
                self.table_names.append(clean_name)
                messages.append(clean_name)

            return None, f"Successfully loaded tables: {', '.join(messages)}"

        except Exception as e:
            return f"Ingestion Error: {str(e)}", None

    def get_schema(self):
        """
        Returns schema for ALL loaded tables to help AI find Joins.
        """
        full_schema = ""
        try:
            if not self.table_names:
                return "No tables loaded."
                
            for table in self.table_names:
                df_schema = self.conn.execute(f"DESCRIBE {table}").df()
                full_schema += f"\nTABLE: {table}\nCOLUMNS:\n"
                for _, row in df_schema.iterrows():
                    full_schema += f"- {row['column_name']} ({row['column_type']})\n"
            return full_schema
        except:
            return "Error retrieving schema."

    def run_query(self, sql_query):
        """
        Executes an SQL query and returns the result as a Pandas DataFrame.
        """
        try:
            return self.conn.execute(sql_query).df(), None
        except Exception as e:
            return pd.DataFrame(), str(e)
            
    def get_sample(self, limit=5):
        """Returns sample of the first table loaded."""
        if self.table_names:
            return self.conn.execute(f"SELECT * FROM {self.table_names[0]} LIMIT {limit}").df()
        return pd.DataFrame()