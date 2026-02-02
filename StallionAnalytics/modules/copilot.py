import google.generativeai as genai
import openai
import json
import streamlit as st

class StallionCopilot:
    """
    The SQL-Aware Active Agent with Context & Suggestions.
    """
    
    def __init__(self, provider, api_key, model, db_engine):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.db = db_engine

    def process_query(self, user_query, current_config, schema_metadata, focused_context=None):
        """
        focused_context: ID/Title of the specific chart/KPI the user wants to modify.
        """
        
        # 1. Handle Context Filtering
        context_str = "Global Dashboard (The user is asking about the entire dataset or layout)"
        
        # Check if user selected a specific Chart/KPI
        if focused_context and "Global" not in focused_context:
            context_str = f"FOCUS AREA: The user is explicitly pointing at this component: '{focused_context}'."

        system_prompt = f"""
        You are the SQL Co-Pilot for Stallion Analytics.
        
        DATABASE SCHEMA:
        {schema_metadata}
        
        CURRENT DASHBOARD JSON:
        {json.dumps(current_config)}
        
        CONTEXT: {context_str}
        
        USER COMMAND: "{user_query}"
        
        INSTRUCTIONS:
        1. Decide if this is a Dashboard Update (Visual/SQL change) or a Text Answer (Analysis).
        2. IF Update: Return "response_type": "update_dashboard" and the FULL updated JSON in "content".
        3. IF Answer: Return "response_type": "text_answer" and the analytical text in "content".
        4. ALWAYS provide 2 short, clickable "suggestions" for next steps.
        
        OUTPUT FORMAT (Strict JSON):
        {{
            "response_type": "update_dashboard" | "text_answer",
            "content": "string or json_object",
            "suggestions": ["Action 1", "Action 2"]
        }}
        """
        
        try:
            response_text = self._call_ai(system_prompt)
            return self._clean_json(response_text)
        except Exception as e:
            # Fallback if AI fails or returns bad JSON
            return {
                "response_type": "text_answer", 
                "content": f"I analyzed the data but encountered an error parsing the response. Raw output: {str(e)}",
                "suggestions": ["Try simpler query", "Check Data"]
            }

    def _call_ai(self, prompt):
        if self.provider == "Google Gemini":
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            return model.generate_content(prompt).text
        else:
            client = openai.OpenAI(api_key=self.api_key)
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": prompt}]
            )
            return resp.choices[0].message.content

    def _clean_json(self, text):
        # Remove markdown fences and whitespace
        clean = text.replace("```json", "").replace("```", "").strip()
        # Sometimes AI adds extra text outside JSON, try to find the first { and last }
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end != -1:
            clean = clean[start:end]
        return json.loads(clean)