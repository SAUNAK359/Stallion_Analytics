import openai
import google.generativeai as genai
import json
import streamlit as st

class StallionCopilot:
    def __init__(self, provider, api_key, model, df):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.df = df 

    def process_query(self, user_query, current_config, data_metadata):
        system_prompt = f"""You are the Co-Pilot for Stallion Analytics. You have full control over the Dashboard Configuration.

CURRENT DASHBOARD JSON:
{json.dumps(current_config)}

DATA METADATA:
{data_metadata}

USER COMMAND:
"{user_query}"

INSTRUCTIONS:
1. If the user wants to CHANGE the visual layout (e.g., "Change chart to line", "Add a KPI for Profit", "Remove the second chart"),
   return a JSON object with "response_type": "update_dashboard" and "content": {{THE COMPLETE UPDATED DASHBOARD JSON}}.
   
2. If the user asks a specific question about the data (e.g., "Why is sales down?", "Summarize the dataset"),
   return a JSON object with "response_type": "text_answer" and "content": "Your analytical answer here".
   
3. OUTPUT MUST BE STRICT JSON ONLY. No Markdown."""
        
        response_text = self._call_ai(system_prompt)
        
        try:
            return self._clean_json(response_text)
        except:
            return {"response_type": "text_answer", "content": response_text}

    def _call_ai(self, prompt):
        if self.provider == "Google Gemini":
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model if self.model else "gemini-2.5-pro")
            return model.generate_content(prompt).text
        else:
            client = openai.OpenAI(api_key=self.api_key)
            resp = client.chat.completions.create(
                model=self.model if self.model else "gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}]
            )
            return resp.choices[0].message.content

    def _clean_json(self, text):
        clean = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            try:
                start = clean.find("{")
                end = clean.rfind("}") + 1
                if start != -1 and end != -1:
                    return json.loads(clean[start:end])
                return clean
            except Exception:
                 return clean
