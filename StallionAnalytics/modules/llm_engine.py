import openai
import google.generativeai as genai
import json

class DashboardBrain:
    """
    The SQL-Aware Intelligence Layer.
    Generates Dashboard Layouts AND the specific SQL queries to populate them.
    """
    
    def __init__(self, provider="OpenAI", api_key=None, model=None):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        if provider == "Google Gemini" and api_key:
            genai.configure(api_key=api_key)

    def suggest_intents(self, schema_metadata):
        """
        Analyzes the schema and suggests 7 high-value dashboard ideas.
        Returns: List of strings.
        """
        system_prompt = """
        You are a Senior Business Analyst. 
        Analyze the provided Database Schema and generate 7 distinct, high-value dashboard ideas.
        
        RULES:
        1. Focus on "Business Value" (e.g., "Customer Churn Analysis", "Inventory Turnover", "Seasonal Sales Trends").
        2. Avoid generic titles like "Data Overview". Go for specific insights like "Cohort Analysis" or "Pareto Distribution".
        3. Return ONLY a JSON list of strings. No markdown.
        
        Example Output:
        ["Sales Performance by Region", "Customer Acquisition Cost Analysis", "Quarterly Revenue Trends", ...]
        """
        
        user_message = f"""
        DATABASE SCHEMA:
        {schema_metadata}
        
        Generate 7 dashboard suggestions now.
        """

        try:
            if self.provider == "Google Gemini":
                response = self._call_gemini(system_prompt, user_message)
            else:
                response = self._call_openai(system_prompt, user_message)
            
            # Ensure it's a list
            if isinstance(response, list):
                return response
            else:
                return ["Overview of Key Metrics", "Trends Over Time", "Category Breakdown"] # Fallback
                
        except Exception as e:
            return [f"Error generating suggestions: {str(e)}"]

    def generate_dashboard_layout(self, schema_metadata, user_intent="General Overview"):
        """
        Input: Database Schema (String)
        Output: JSON Config with embedded SQL queries.
        """
        system_prompt = """
        You are a Principal Data Architect and SQL Expert for DuckDB.
        Your goal is to design a dashboard and write OPTIMIZED SQL queries for each visual.
        
        CONTEXT:
        - Table Name: source_data
        - Database: DuckDB (Supports standard SQL)
        
        OUTPUT FORMAT (Strict JSON):
        {
            "dashboard_title": "string",
            "kpi_cards": [
                {
                    "id": "kpi_1",
                    "label": "Total Revenue",
                    "sql_query": "SELECT SUM(sales) FROM source_data", 
                    "format": "currency" 
                }
            ],
            "charts": [
                {
                    "id": "chart_1",
                    "type": "bar/line/pie",
                    "title": "Sales by Region",
                    "sql_query": "SELECT region, SUM(sales) as total_sales FROM source_data GROUP BY region ORDER BY total_sales DESC LIMIT 20",
                    "x_column": "region",
                    "y_column": "total_sales",
                    "description": "Top performing regions."
                }
            ]
        }
        
        RULES:
        1. "sql_query": MUST be a valid, executable SQL query.
        2. Aggregations: Always GROUP BY when using SUM/AVG/COUNT in charts.
        3. Limits: Always add 'LIMIT 100' to chart queries to prevent browser crashes.
        4. KPI Queries: Must return exactly ONE row and ONE column (a single value).
        """
        
        user_message = f"""
        DATABASE SCHEMA:
        {schema_metadata}
        
        USER INTENT:
        {user_intent}
        
        Design the dashboard and write the SQL now.
        """

        try:
            if self.provider == "Google Gemini":
                return self._call_gemini(system_prompt, user_message)
            else:
                return self._call_openai(system_prompt, user_message)
        except Exception as e:
            return {"error": f"AI Generation Failed: {str(e)}"}

    def _call_gemini(self, sys, user):
        model = genai.GenerativeModel(self.model if self.model else "gemini-2.5-pro")
        resp = model.generate_content(f"{sys}\n\nUSER: {user}")
        return self._clean_json(resp.text)

    def _call_openai(self, sys, user):
        client = openai.OpenAI(api_key=self.api_key)
        resp = client.chat.completions.create(
            model=self.model if self.model else "gpt-3.5-turbo",
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}]
        )
        return self._clean_json(resp.choices[0].message.content)

    def _clean_json(self, text):
        clean = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean)
        except:
            return {"error": "Invalid JSON returned."}