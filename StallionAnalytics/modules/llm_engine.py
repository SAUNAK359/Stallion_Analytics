import openai
import google.generativeai as genai
import json

class DashboardBrain:
    def __init__(self, provider="OpenAI", api_key=None, model=None):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        if provider == "Google Gemini" and api_key:
            genai.configure(api_key=api_key)

    def generate_dashboard_layout(self, data_metadata, user_intent="General Overview"):
        system_prompt = """You are a Senior Data Visualization Architect for 'Stallion Analytics'.
Your goal is to design a high-end, executive-level dashboard based on dataset metadata.

OUTPUT FORMAT:
Return ONLY a raw JSON object. Do not wrap in markdown blocks (no ```json).

JSON STRUCTURE:
{
    "dashboard_title": "string",
    "kpi_cards": [
        {"id": "kpi_1", "label": "string", "column": "string", "operation": "sum/avg/count/min/max", "format": "currency/number/percent"}
    ],
    "charts": [
        {
            "id": "chart_1",
            "type": "bar/line/area/pie/scatter",
            "title": "string",
            "x_column": "string", 
            "y_column": "string", 
            "color_column": "string (optional)",
            "description": "Short insight about why this chart matters."
        }
    ]
}

RULES:
1. Max 8 KPI cards. Max 8 Charts unless user defines the number of KPI/Charts.
2. Use the provided Metadata to choose correct columns.
3. Reason about what visualizations best suit the user intent.
4. Ensure the JSON is valid and parsable."""
        
        user_message = f"""DATASET METADATA:
{data_metadata}

USER INTENT:
{user_intent}

Generate the Stallion Dashboard JSON configuration now."""

        try:
            if self.provider == "OpenAI":
                return self._call_openai(system_prompt, user_message)
            elif self.provider == "Google Gemini":
                return self._call_gemini(system_prompt, user_message)
            return self.mock_generation()
        except Exception as e:
            return {"error": f"AI Generation Failed: {str(e)}"}

    def _call_openai(self, sys_prompt, user_msg):
        if not self.api_key:
             return {"error": "OpenAI API Key is missing."}
        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model if self.model else "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.2
            )
            return self._clean_json(response.choices[0].message.content)
        except Exception as e:
            return {"error": f"OpenAI API Error: {str(e)}"}

    def _call_gemini(self, sys_prompt, user_msg):
        if not self.api_key:
             return {"error": "Google Gemini API Key is missing."}
        try:
            model_name = self.model if self.model else "gemini-2.5-pro"
            model = genai.GenerativeModel(model_name)
            full_prompt = f"{sys_prompt}\n\nUSER REQUEST:\n{user_msg}"
            response = model.generate_content(full_prompt)
            return self._clean_json(response.text)
        except Exception as e:
            return {"error": f"Gemini API Error: {str(e)}"}

    def _clean_json(self, text):
        clean_text = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            try:
                start = clean_text.find("{")
                end = clean_text.rfind("}") + 1
                if start != -1 and end != -1:
                    return json.loads(clean_text[start:end])
                return {"error": "Invalid JSON format returned by AI."}
            except json.JSONDecodeError:
                 return {"error": "Invalid JSON format returned by AI."}

    @staticmethod
    def mock_generation():
        return {
            "dashboard_title": "Mock Dashboard (No API Key)",
            "kpi_cards": [
                {"id": "k1", "label": "Total Rows", "column": "index", "operation": "count", "format": "number"}
            ],
            "charts": []
        }
