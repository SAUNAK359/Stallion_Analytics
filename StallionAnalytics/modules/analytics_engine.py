import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import warnings

warnings.filterwarnings("ignore")

class StallionAnalyticsEngine:
    """
    The 'Toolbelt' for the Stallion Planner.
    Performs heavy statistical lifting locally to reduce LLM load.
    """

    def detect_anomalies(self, df, value_col, contamination=0.05):
        """
        Uses Isolation Forest to find statistical outliers.
        Returns: A summary string of anomalies found.
        """
        try:
            if df.empty or value_col not in df.columns: return "No data for anomaly detection."
            
            # Prepare data
            data = df[[value_col]].dropna()
            if len(data) < 10: return "Not enough data points for reliable anomaly detection."

            # Model
            iso = IsolationForest(contamination=contamination, random_state=42)
            preds = iso.fit_predict(data)
            
            # Extract Anomalies (-1 means anomaly)
            anomalies = df.loc[data.index[preds == -1]]
            
            if anomalies.empty:
                return "No significant statistical anomalies detected."
            
            # Summarize
            summary = f"⚠️ Found {len(anomalies)} Anomalies:\n"
            # Get top 3 most extreme
            top_anomalies = anomalies.sort_values(by=value_col, ascending=False).head(3)
            for idx, row in top_anomalies.iterrows():
                # Try to find a date or label column for context
                label = row.keys()[0] # Heuristic: First column is usually the label (Date/Name)
                summary += f"- {row[label]}: {row[value_col]}\n"
                
            return summary
        except Exception as e:
            return f"Anomaly Detection Failed: {str(e)}"

    def generate_forecast(self, df, date_col, value_col, periods=6):
        """
        Uses Holt-Winters to predict future trends.
        Returns: A summary string of the forecast trend.
        """
        try:
            if df.empty or date_col not in df.columns: return "No data for forecasting."
            
            # Prep
            data = df.copy()
            data[date_col] = pd.to_datetime(data[date_col], errors='coerce')
            data = data.dropna(subset=[date_col]).sort_values(by=date_col)
            
            if len(data) < 12: return "Data too short for seasonal forecasting (need 12+ points)."

            # Resample (Monthly heuristic)
            ts = data.set_index(date_col)[value_col].resample('ME').sum().fillna(0)
            
            # Model
            model = ExponentialSmoothing(ts, trend='add', seasonal='add', seasonal_periods=12).fit()
            forecast = model.forecast(periods)
            
            # Analyze Trend
            start_val = ts.iloc[-1]
            end_val = forecast.iloc[-1]
            growth = ((end_val - start_val) / start_val) * 100
            
            direction = "Growth" if growth > 0 else "Decline"
            return f"🔮 Forecast ({periods} months): Projected {direction} of {growth:.1f}%. Expected value: {end_val:,.0f}."
            
        except Exception as e:
            return f"Forecasting Failed: {str(e)}"

    def check_correlations(self, df):
        """
        Calculates Pearson correlation matrix.
        Returns: Strong relationships between numerical columns.
        """
        try:
            # Select only numeric
            numeric_df = df.select_dtypes(include=[np.number])
            if numeric_df.shape[1] < 2: return "Not enough numeric columns for correlation."
            
            corr_matrix = numeric_df.corr()
            
            # Find strong pairs
            insights = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i):
                    col1 = corr_matrix.columns[i]
                    col2 = corr_matrix.columns[j]
                    score = corr_matrix.iloc[i, j]
                    
                    if abs(score) > 0.75: # Strong threshold
                        strength = "Positive" if score > 0 else "Negative"
                        insights.append(f"- Strong {strength} Correlation ({score:.2f}) between '{col1}' and '{col2}'")
            
            if not insights: return "No strong correlations (>0.75) detected."
            return "🔗 Key Correlations:\n" + "\n".join(insights[:5]) # Top 5
            
        except Exception as e:
            return f"Correlation Check Failed: {str(e)}"