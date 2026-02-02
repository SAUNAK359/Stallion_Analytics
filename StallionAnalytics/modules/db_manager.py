import duckdb
import pandas as pd
import streamlit as st

class StallionDB:
    """
    The High-Performance Data Engine.
    Wraps DuckDB to handle large datasets efficiently.
    """
    
    def __init__(self):
        # In-memory database for the session
        # For persistence, we could change ':memory:' to 'stallion.db'
        self.conn = duckdb.connect(database=':memory:')

    def ingest_data(self, uploaded_file):
        """
        Streams file directly into a SQL table named 'source_data'.
        """
        try:
            # Create a temporary view directly from the file buffer is tricky in DuckDB 
            # without saving to disk first. For Streamlit, we save to a temp file.
            
            file_path = f"temp_{uploaded_file.name}"
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Determine loader based on extension
            if file_path.endswith('.csv'):
                # DuckDB's CSV sniffer is excellent (auto-detects delimiter/types)
                query = f"CREATE OR REPLACE TABLE source_data AS SELECT * FROM read_csv_auto('{file_path}', normalize_names=True)"
            elif file_path.endswith('.json'):
                query = f"CREATE OR REPLACE TABLE source_data AS SELECT * FROM read_json_auto('{file_path}')"
            elif file_path.endswith('.parquet'):
                query = f"CREATE OR REPLACE TABLE source_data AS SELECT * FROM read_parquet('{file_path}')"
            else:
                return "Unsupported file format for Big Data Engine."

            self.conn.execute(query)
            return None # No error

        except Exception as e:
            return f"Ingestion Error: {str(e)}"

    def get_schema(self):
        """
        Returns column names and types for the AI to understand.
        """
        try:
            # Fetch minimal schema info
            df_schema = self.conn.execute("DESCRIBE source_data").df()
            
            # Format nicely for the LLM
            schema_str = "TABLE: source_data\nCOLUMNS:\n"
            for _, row in df_schema.iterrows():
                schema_str += f"- {row['column_name']} ({row['column_type']})\n"
            
            return schema_str
        except:
            return "No data loaded."

    def run_query(self, sql_query):
        """
        Executes an SQL query and returns the result as a Pandas DataFrame.
        This is safe because the RESULT is usually small (aggregated), 
        even if the source is massive.
        """
        try:
            return self.conn.execute(sql_query).df(), None
        except Exception as e:
            return None, str(e)
            
    def get_sample(self, limit=5):
        return self.conn.execute(f"SELECT * FROM source_data LIMIT {limit}").df()