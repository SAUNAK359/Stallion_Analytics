import google.generativeai as genai
import openai
import json
import streamlit as st
import pandas as pd

class StallionCopilot:
    """
    The SQL-Aware Active Agent with 'Reasoning Loop'.
    Capabilities:
    1. Direct Dashboard Updates (Visuals).
    2. Data Querying for Text Answers (Reasoning).
    3. Context-Aware Summarization.
    """
    
    def __init__(self, provider, api_key, model, db_engine):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.db = db_engine

    def process_query(self, user_query, current_config, schema_metadata, focused_context=None):
        """
        Executes a 2-step Reasoning Loop:
        Step 1: Investigator (Should I run SQL?)
        Step 2: Responder (Answer using the SQL data or update dashboard)
        """
        
        # --- STEP 1: THE INVESTIGATOR ---
        # Ask AI if it needs data to answer.
        investigator_prompt = f"""
        You are a Data Investigator.
        User Query: "{user_query}"
        Schema: {schema_metadata}
        Context: {focused_context}
        
        Task: 
        - If the user asks for a visualization/chart update, return "ACTION: UPDATE_DASHBOARD".
        - If the user asks for a summary or report, return "ACTION: SUMMARIZE".
        - If the user asks a factual question about the data (e.g., "Which stock is most volatile?", "Why is sales down?"), write the SQL query to fetch the answer.
        
        Output ONLY one of:
        - "ACTION: UPDATE_DASHBOARD"
        - "ACTION: SUMMARIZE"
        - The SQL Query itself (DuckDB format)
        """
        
        pre_response = self._call_ai(investigator_prompt).strip()
        
        # --- STEP 2: EXECUTION ---
        data_context = ""
        action_type = "text_answer" # Default
        
        # CASE A: AI wants to run SQL to get facts
        if "SELECT" in pre_response.upper() and "ACTION" not in pre_response:
            try:
                clean_sql = pre_response.replace("```sql", "").replace("```", "").strip()
                df_result, err = self.db.run_query(clean_sql)
                
                if not df_result.empty:
                    # Limit context to top 10 rows to save tokens
                    csv_preview = df_result.head(10).to_markdown(index=False)
                    data_context = f"\n[INTERNAL DATA INVESTIGATION]\nSQL Executed: {clean_sql}\nResult Preview:\n{csv_preview}\n"
                else:
                    data_context = "\n[INTERNAL DATA INVESTIGATION]\nQuery returned no results."
            except Exception as e:
                data_context = f"\n[INTERNAL DATA INVESTIGATION]\nError executing SQL: {str(e)}"
        
        # CASE B: Dashboard Update Request
        elif "UPDATE_DASHBOARD" in pre_response:
            action_type = "update_dashboard"
            
        # CASE C: Summary Request
        elif "SUMMARIZE" in pre_response:
            action_type = "summarize"

        # --- STEP 3: THE RESPONDER ---
        system_prompt = f"""
        You are the Stallion Co-Pilot (Enterprise Edition).
        
        DATABASE SCHEMA:
        {schema_metadata}
        
        CURRENT DASHBOARD JSON:
        {json.dumps(current_config)}
        
        USER FOCUS: {focused_context}
        
        {data_context}  <-- CRITICAL: USE THIS REAL DATA TO ANSWER!
        
        USER COMMAND: "{user_query}"
        
        INSTRUCTIONS:
        1. IF action is 'update_dashboard': Return JSON with "response_type": "update_dashboard" and full config.
        2. IF action is 'summarize': Return JSON with "response_type": "update_executive_summary" and a rich HTML summary string in "content".
        3. IF action is 'text_answer': Provide a HIGHLY ANALYTICAL answer based on the DATA INSIGHTS provided above. 
           - Do not just state numbers; explain *why* (e.g., "Tesla is most volatile (5.4%), likely due to the recent earnings call...").
           - Be professional and conclusive.
        
        OUTPUT FORMAT (Strict JSON):
        {{
            "response_type": "update_dashboard" | "text_answer" | "update_executive_summary",
            "content": "string_or_json",
            "suggestions": ["Next Step 1", "Next Step 2"]
        }}
        """
        
        try:
            final_response = self._call_ai(system_prompt)
            return self._clean_json(final_response)
        except Exception as e:
            return {
                "response_type": "text_answer",
                "content": f"Reasoning Error: {str(e)}. (I tried to think but failed.)",
                "suggestions": ["Try simpler query"]
            }

    def generate_chart_insight(self, df, title):
        """
        Specialized method for the 'Analyze this Chart' button.
        """
        stats = df.describe().to_markdown()
        prompt = f"""
        Analyze this chart data for "{title}".
        Stats:
        {stats}
        
        Provide 3 bullet points:
        1. Observation (What is happening?)
        2. Insight (Why is it significant?)
        3. Recommendation (What to do?)
        """
        return self._call_ai(prompt)

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
        clean = text.replace("```json", "").replace("```", "").strip()
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end != -1:
            clean = clean[start:end]
        return json.loads(clean)