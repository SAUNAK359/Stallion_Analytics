import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.linear_model import LinearRegression
import warnings

# Suppress statsmodels warnings for cleaner logs
warnings.filterwarnings("ignore")

class StallionForecaster:
    """
    The Agentic Forecasting Engine.
    Automatically detects data patterns (Trend/Seasonality) and selects the best model.
    """
    
    def __init__(self):
        pass

    def generate_forecast(self, df, x_col, y_col, periods=6, growth_factor=0.0):
        """
        df: Input DataFrame (must have date column)
        periods: Number of future periods to predict (months/days)
        growth_factor: User 'What-If' percentage (e.g., 0.10 for +10% growth)
        
        Returns: (forecast_df, model_info_string)
        """
        try:
            # 1. Data Preparation
            data = df.copy()
            # Attempt to convert to datetime
            data[x_col] = pd.to_datetime(data[x_col], errors='coerce')
            data = data.dropna(subset=[x_col])
            data = data.sort_values(by=x_col)
            
            if data.empty:
                return None, "Invalid Date Column"

            # Resample to ensure regular intervals
            # Heuristic: If > 60 points, assume Daily/Weekly, else Monthly
            # We aggregate by sum to handle duplicates
            if len(data) > 60:
                freq = 'D'
                cycle = 7 # Weekly seasonality
            else:
                # Use 'ME' for Month End in newer pandas, fallback to 'M'
                freq = 'M' 
                cycle = 12 # Yearly seasonality
            
            # Group and fill gaps
            ts_data = data.groupby(x_col)[y_col].sum()
            
            # Infer frequency if possible, else force our heuristic
            if not ts_data.index.freq:
                try:
                    ts_data = ts_data.asfreq(freq, method='ffill').fillna(0)
                except:
                    # Fallback for messy dates: Use index as 0,1,2...
                    pass
            
            # 2. Model Selection Logic (Agentic Decision)
            # Need at least 2 full cycles for seasonal models
            use_seasonality = len(ts_data) >= (cycle * 2)
            
            model_name = ""
            
            if use_seasonality:
                try:
                    # Holt-Winters (Trend + Seasonality)
                    model = ExponentialSmoothing(
                        ts_data, 
                        trend='add', 
                        seasonal='add', 
                        seasonal_periods=cycle
                    ).fit()
                    forecast_values = model.forecast(periods)
                    model_name = f"Holt-Winters (Seasonal period={cycle})"
                except:
                    # Fallback if HW fails
                    use_seasonality = False
            
            if not use_seasonality:
                # Simple Linear Trend (Robust fallback)
                # Convert dates to ordinal for regression
                X = np.arange(len(ts_data)).reshape(-1, 1)
                y = ts_data.values
                reg = LinearRegression().fit(X, y)
                
                future_X = np.arange(len(ts_data), len(ts_data) + periods).reshape(-1, 1)
                pred = reg.predict(future_X)
                
                # Create Date Index for future
                last_date = ts_data.index[-1]
                future_dates = pd.date_range(start=last_date, periods=periods+1, freq=freq)[1:]
                
                forecast_values = pd.Series(pred, index=future_dates)
                model_name = "Linear Trend (Not enough data for seasonality)"

            # 3. Apply User "What-If" Scenario (Growth Factor)
            # Apply cumulative growth or flat bump? 
            # Let's apply a ramp-up scalar multiplier
            if growth_factor != 0:
                # Ramp up the effect: Year 1 gets x%, Year 2 gets 2x%...
                # Actually, simpler: Apply flat growth to the trend line
                modifiers = np.linspace(1, 1 + growth_factor, periods)
                forecast_values = forecast_values * modifiers
                model_name += f" + {int(growth_factor*100)}% Growth Scenario"

            # 4. Format Output
            forecast_df = pd.DataFrame({
                x_col: forecast_values.index,
                y_col: forecast_values.values,
                "Type": "Forecast"
            })
            
            return forecast_df, model_name

        except Exception as e:
            return None, str(e)