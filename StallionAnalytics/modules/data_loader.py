import pandas as pd
import io
import warnings

class StallionLoader:
    @staticmethod
    def load_file(uploaded_file):
        if uploaded_file is None:
            return None, "No file provided."
        file_name = uploaded_file.name
        try:
            if file_name.endswith('.csv'):
                return StallionLoader._load_csv(uploaded_file)
            elif file_name.endswith(('.xlsx', '.xls')):
                return StallionLoader._load_excel(uploaded_file)
            elif file_name.endswith('.json'):
                return StallionLoader._load_json(uploaded_file)
            return None, "Unsupported file format. Please use CSV, Excel, or JSON."
        except Exception as e:
            return None, f"Critical Load Error: {str(e)}"

    @staticmethod
    def _load_csv(file_buffer):
        encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        for encoding in encodings:
            try:
                file_buffer.seek(0)
                df = pd.read_csv(file_buffer, encoding=encoding)
                return StallionLoader._sanitize(df), None
            except UnicodeDecodeError:
                continue
            except pd.errors.ParserError:
                file_buffer.seek(0)
                try:
                    df = pd.read_csv(file_buffer, encoding=encoding, on_bad_lines='skip')
                    return StallionLoader._sanitize(df), f"Warning: Some malformed rows were skipped using {encoding}."
                except Exception:
                    continue
        return None, "Failed to decode CSV. File might be binary or corrupted."

    @staticmethod
    def _load_excel(file_buffer):
        try:
            df = pd.read_excel(file_buffer)
            return StallionLoader._sanitize(df), None
        except Exception as e:
            return None, f"Excel Error: {str(e)}"

    @staticmethod
    def _load_json(file_buffer):
        try:
            df = pd.read_json(file_buffer)
            return StallionLoader._sanitize(df), None
        except ValueError:
            return None, "Invalid JSON format. Structure must be compatible with DataFrame."

    @staticmethod
    def _sanitize(df):
        df.columns = df.columns.astype(str).str.strip().str.lower().str.replace(r'[^\w\s]', '', regex=True).str.replace(' ', '_')
        df = df.dropna(how='all', axis=0)
        df = df.dropna(how='all', axis=1)
        for col in df.select_dtypes(include=['object']):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    temp_col = pd.to_datetime(df[col], errors='coerce')
                valid_ratio = temp_col.notna().mean()
                if valid_ratio > 0.8:
                    df[col] = temp_col
            except Exception:
                pass
        return df

    @staticmethod
    def get_metadata(df):
        buffer = io.StringIO()
        df.info(buf=buffer)
        info_str = buffer.getvalue()
        sample = df.head(3).to_markdown(index=False)
        return f"DATASET SHAPE: {df.shape}\nCOLUMNS: {list(df.columns)}\nTYPES:\n{info_str}\n\nSAMPLE DATA:\n{sample}"
