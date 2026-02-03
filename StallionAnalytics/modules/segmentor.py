import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings
import json

# Suppress warnings for cleaner logs in production
warnings.filterwarnings("ignore")

class StallionSegmentor:
    """
    The Dynamic Segmentation Engine.
    
    Capabilities:
    1. Strategy Discovery: Uses AI to analyze data schema and recommend the best segmentation approach (RFM vs. Generic).
    2. Execution: Performs data preprocessing, feature engineering, and K-Means clustering.
    3. Summarization: Generates human-readable cluster profiles.
    """
    
    def __init__(self, ai_engine=None):
        """
        Args:
            ai_engine (StallionCopilot): Reference to the AI engine for strategy generation.
        """
        self.ai = ai_engine

    def suggest_strategy(self, df_head_markdown):
        """
        Asks the AI to map columns and propose a segmentation strategy.
        
        Args:
            df_head_markdown (str): First few rows of the dataframe in Markdown format.
            
        Returns:
            dict: JSON config containing 'strategy_type', 'id_col', 'date_col', 'amount_col', or 'feature_cols'.
        """
        if not self.ai:
            return None

        prompt = f"""
        You are a Data Science Architect. Analyze this data sample to determine the best Customer/Entity Segmentation Strategy.
        
        DATA SAMPLE:
        {df_head_markdown}
        
        TASK:
        1. Identify the 'Entity ID' (Customer ID, Product ID, User ID, etc.).
        2. Identify the best numerical features for clustering.
           - If Transaction Data (Date, Amount) is present -> Suggest 'RFM' (Recency, Frequency, Monetary).
           - If Behavioral Data (Duration, Clicks, logins) is present -> Suggest 'Generic' and list the columns.
           - If Product Data (Price, Stock) is present -> Suggest 'Generic'.
        
        OUTPUT JSON ONLY (No markdown):
        {{
            "strategy_type": "RFM" or "Generic",
            "id_col": "column_name_for_id",
            "date_col": "column_name_for_date (only if RFM)",
            "amount_col": "column_name_for_amount (only if RFM)",
            "feature_cols": ["col1", "col2"] (only if Generic)
        }}
        """
        try:
            response = self.ai._call_ai(prompt)
            # Use the Copilot's helper to sanitize JSON
            return self.ai._clean_json(response)
        except Exception as e:
            # Fallback/Log error
            print(f"Strategy Suggestion Failed: {e}")
            return None

    def execute_segmentation(self, df, strategy_config, n_clusters=4):
        """
        Executes the clustering strategy defined by the AI.
        
        Args:
            df (pd.DataFrame): The raw data query result.
            strategy_config (dict): The configuration returned by suggest_strategy.
            n_clusters (int): Number of clusters to generate.
            
        Returns:
            (pd.DataFrame, str): The labeled dataframe and a markdown summary of cluster stats.
        """
        try:
            if df.empty: return None, "No data to segment."
            
            features = pd.DataFrame()
            
            # --- PATH A: RFM SEGMENTATION ---
            if strategy_config.get("strategy_type") == "RFM":
                id_col = strategy_config.get("id_col")
                date_col = strategy_config.get("date_col")
                amt_col = strategy_config.get("amount_col")
                
                # Validation
                if not (id_col and date_col and amt_col):
                    return None, "RFM Strategy missing required columns in config."
                
                # Pre-processing
                data = df.copy()
                data[date_col] = pd.to_datetime(data[date_col], errors='coerce')
                data[amt_col] = pd.to_numeric(data[amt_col], errors='coerce')
                data = data.dropna(subset=[id_col, date_col, amt_col])
                
                # Snapshot date (1 day after max date)
                snapshot = data[date_col].max() + pd.Timedelta(days=1)
                
                # Aggregation
                features = data.groupby(id_col).agg({
                    date_col: lambda x: (snapshot - x.max()).days, # Recency
                    id_col: 'count',                                # Frequency
                    amt_col: 'sum'                                  # Monetary
                }).rename(columns={
                    date_col: 'Recency',
                    id_col: 'Frequency',
                    amt_col: 'Monetary'
                })
                
                # Clean outliers (negative recency/money)
                features = features[(features['Monetary'] > 0) & (features['Recency'] >= 0)]

            # --- PATH B: GENERIC CLUSTERING (Behavioral/Product) ---
            else:
                id_col = strategy_config.get("id_col")
                cols = strategy_config.get("feature_cols", [])
                
                if not cols: return None, "Generic Strategy missing feature columns."
                
                # Validate columns exist
                valid_cols = [c for c in cols if c in df.columns]
                if not valid_cols: return None, "Feature columns not found in data."
                
                # Aggregation (if ID exists and duplicates present)
                if id_col and id_col in df.columns:
                     # Check if we need to group by ID
                    if df.duplicated(subset=[id_col]).any():
                        # Defaulting to mean for behavioral metrics
                        features = df.groupby(id_col)[valid_cols].mean()
                    else:
                        features = df.set_index(id_col)[valid_cols]
                else:
                    # No ID, just cluster the rows directly
                    features = df[valid_cols]
                
                features = features.dropna()

            # --- CORE CLUSTERING LOGIC ---
            if len(features) < n_clusters:
                return None, f"Not enough data points ({len(features)}) for {n_clusters} clusters."

            # 1. Log Transform (Handle skewed distributions common in business data)
            # Using log1p to handle zeros safely
            features_log = np.log1p(features.select_dtypes(include=np.number))
            
            # 2. Scaling
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features_log)
            
            # 3. K-Means
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(features_scaled)
            
            # 4. Attach Clusters to Original Data
            features['Cluster'] = clusters
            
            # 5. Generate Summary Stats for AI Context
            # Group by Cluster and get mean of features
            summary_stats = features.groupby('Cluster').mean().round(2)
            summary_stats['Count'] = features['Cluster'].value_counts()
            
            # Sort by count or primary metric for better readability
            summary_stats = summary_stats.sort_values(by='Count', ascending=False)
            
            return features, summary_stats.to_markdown()

        except Exception as e:
            return None, f"Segmentation Execution Error: {str(e)}"