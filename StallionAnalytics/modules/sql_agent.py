import google.generativeai as genai
import openai

class SQLAgent:
    def __init__(self, provider, api_key, model):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        
        if provider == "Google Gemini":
            genai.configure(api_key=api_key)

    def generate_sql_for_chart(self, chart_intent, schema_metadata):
        """
        Translates a chart requirement into a SQL query.
        """
        system_prompt = f"""
        You are a SQL Expert for DuckDB. 
        Your task is to write a single valid SQL query to fetch data for a visualization.
        
        DATABASE SCHEMA:
        {schema_metadata}
        
        TABLE NAME: source_data
        
        USER INTENT: "{chart_intent}"
        
        RULES:
        1. Return ONLY the raw SQL query. No markdown, no explanation.
        2. Use compatible DuckDB syntax.
        3. If aggregating (e.g., "sales by region"), make sure to GROUP BY.
        4. LIMIT results to 100 rows to prevent UI crashing.
        """
        
        # Call AI (Reusing the generic call logic from before)
        response = self._call_ai(system_prompt)
        
        # Clean response
        sql = response.replace("```sql", "").replace("```", "").strip()
        return sql

    def _call_ai(self, prompt):
        # ... (Same call logic as Copilot/DashboardBrain) ...
        # For brevity, assuming you copy the _call_ai method here
        # or inherit from a BaseAgent class.
        if self.provider == "Google Gemini":
             model = genai.GenerativeModel(self.model)
             return model.generate_content(prompt).text
        else:
             # OpenAI logic
             pass