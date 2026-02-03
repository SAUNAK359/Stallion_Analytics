import streamlit as st
import pandas as pd
import time
from modules.copilot import StallionCopilot
from modules.analytics_engine import StallionAnalyticsEngine
from modules.segmentor import StallionSegmentor

class StallionPlanner:
    """
    The 'Stallion Planner' Agent (v4.0 - Full Agentic Suite).
    
    ARCHITECTURE: RHRL Pipeline
    1. Recall: Audits the current dashboard state (Context Awareness).
    2. Hypothesis: Formulates a surgical research plan based on User Objective.
    3. Reasoning: Executes SQL & routes data to Deterministic Tools (Forecast/Anomaly/Segmentation).
    4. Layout: Synthesizes intelligence into a Board-Ready HTML Report.
    """
    
    def __init__(self, db_engine, ai_provider, api_key, model):
        self.db = db_engine
        self.ai = StallionCopilot(ai_provider, api_key, model, db_engine)
        self.analytics = StallionAnalyticsEngine()
        # Initialize Segmentor with AI reference for dynamic strategy
        self.segmentor = StallionSegmentor(self.ai)
    
    def generate_enterprise_report(self, dashboard_config, user_objective=None, context_signature=None):
        """
        Orchestrates the full Agentic Pipeline.
        Args:
            context_signature (dict): Metadata from the Workspace (Intent + AI Summary).
        """
        
        # ==============================================================================
        # PHASE 1: RECALL (Legacy Audit)
        # ==============================================================================
        # Captures the baseline state of the current dashboard (Context setting)
        context_log = "### 1. DASHBOARD AUDIT (Baseline Data)\n"
        
        # Audit KPIs
        if "kpi_cards" in dashboard_config:
            context_log += "\n[METRICS]\n"
            for kpi in dashboard_config["kpi_cards"]:
                try:
                    df, _ = self.db.run_query(kpi["sql_query"])
                    val = df.iloc[0,0] if not df.empty else "N/A"
                    context_log += f"- {kpi.get('label')}: {val}\n"
                except: pass

        # Audit Charts
        if "charts" in dashboard_config:
            context_log += "\n[TRENDS]\n"
            for chart in dashboard_config["charts"]:
                try:
                    df, _ = self.db.run_query(chart["sql_query"])
                    if not df.empty:
                        # Capture basic stats for context
                        stats = df.describe().to_markdown()
                        head = df.head(5).to_markdown()
                        context_log += f"\nCHART: {chart.get('title')}\nStats:\n{stats}\nSample:\n{head}\n"
                except: pass
        
        # --- ENHANCED CONTEXT INJECTION ---
        # If this is a loaded dashboard, inject the saved context
        saved_context_prompt = ""
        if context_signature:
            saved_context_prompt = f"""
            ### 🧠 SAVED WORKSPACE CONTEXT:
            - **Original User Intent:** "{context_signature.get('intent')}"
            - **AI Context Signature:** "{context_signature.get('automated_summary')}"
            
            *Instruction:* Use this context to guide your investigation. If the original intent was about 'Churn', focus your analysis on Churn.
            """

        # ==============================================================================
        # PHASE 2: HYPOTHESIS (Strategic Planning)
        # ==============================================================================
        # Formulate a specific plan based on the user's goal.
        schema = self.db.get_schema()
        
        plan_prompt = f"""
        You are a Chief Analytics Officer.
        USER OBJECTIVE: "{user_objective if user_objective else "General Performance Audit"}"
        {saved_context_prompt}

        DATABASE SCHEMA:
        {schema}
        
        TASK: Plan the investigation.
        For each logical step, write the specific SQL query (DuckDB) and select the Analytical Tool to apply.
        
        AVAILABLE TOOLS:
        - [ANOMALY]: Detect outliers in time-series or lists. Use for identifying risks.
        - [FORECAST]: Predict future trends. Use for forward-looking questions.
        - [SEGMENTATION]: Cluster entities (customers/products) to find groups. Use for "Who?" questions.
        - [CORRELATION]: Find relationships between metrics. Use for "Why?" questions.
        - [NONE]: Just fetch data for display.
        
        OUTPUT FORMAT (Per Line):
        SQL_QUERY | TOOL_NAME
        """
        
        # Get the plan from the Brain
        raw_plan = self.ai._call_ai(plan_prompt)
        
        # ==============================================================================
        # PHASE 3: REASONING (Execution & Tool Usage)
        # ==============================================================================
        deep_dive_log = f"\n### 2. DEEP DIVE INVESTIGATION\n"
        
        lines = raw_plan.strip().split("\n")
        for line in lines:
            if "|" in line:
                parts = line.split("|")
                # Clean SQL
                sql = parts[0].strip().replace("```sql", "").replace("```", "").replace(";", "")
                tool = parts[1].strip().upper()
                
                try:
                    # A. Run SQL (Data Extraction)
                    df, err = self.db.run_query(sql)
                    if not df.empty:
                        deep_dive_log += f"\n[Query]: {sql}\n"
                        deep_dive_log += f"Data Snapshot:\n{df.head(5).to_markdown()}\n"
                        
                        # B. Tool Routing (The "Muscle")
                        tool_insight = ""
                        
                        # --- 1. SEGMENTATION TOOL ---
                        if "SEGMENTATION" in tool:
                            # Step 1: Ask Segmentor to define strategy based on this data
                            strategy = self.segmentor.suggest_strategy(df.head(5).to_markdown())
                            if strategy:
                                # Step 2: Run Clustering
                                _, summary_md = self.segmentor.execute_segmentation(df, strategy)
                                tool_insight = f"👥 SEGMENTATION ANALYSIS:\n{summary_md}"
                            else:
                                tool_insight = "Segmentation failed to determine strategy."

                        # --- 2. ANOMALY TOOL ---
                        elif "ANOMALY" in tool and len(df.columns) >= 2:
                            # Heuristic: 2nd column is the metric
                            tool_insight = self.analytics.detect_anomalies(df, df.columns[1])
                            
                        # --- 3. FORECAST TOOL ---
                        elif "FORECAST" in tool and len(df.columns) >= 2:
                            # Heuristic: 1st column date, 2nd value
                            tool_insight = self.analytics.generate_forecast(df, df.columns[0], df.columns[1])
                            
                        # --- 4. CORRELATION TOOL ---
                        elif "CORRELATION" in tool:
                            tool_insight = self.analytics.check_correlations(df)
                        
                        # Log Result
                        if tool_insight:
                            deep_dive_log += f"🧰 TOOL RESULT ({tool}):\n{tool_insight}\n"
                            
                except Exception as e:
                    # Continue to next step in plan even if one fails
                    deep_dive_log += f"[Error executing plan step]: {str(e)}\n"

        # ==============================================================================
        # PHASE 4: LAYOUT (Report Generation)
        # ==============================================================================
        full_context = context_log + "\n" + deep_dive_log
        
        report_prompt = f"""
        You are 'Stallion Planner', an Elite Strategy Consultant (Persona: McKinsey/BCG Partner).
        
        MISSION:
        Generate a "Board Room Ready" Executive HTML Report.
        
        USER OBJECTIVE: {user_objective}
        
        ### INTELLIGENCE DOSSIER (Includes AI Tool Analysis):
        {full_context}
        
        ### DESIGN SYSTEM (CSS):
        - Background: #0e1117 (Deep Space Grey).
        - Text: #E0E0E0 (Off-white).
        - Font: 'Inter', sans-serif.
        - Cards: background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 20px; margin-bottom: 20px.
        - Accents: #00E5FF (Cyan) for positives, #FF4B4B (Red) for risks.
        
        ### REPORT STRUCTURE:
        1. **Title Header:** Report Name, Objective, Date.
        2. **Executive Summary:** Synthesize the "Tool Results" (Specific Anomalies, Forecasts, Correlations). Start with the answer.
        3. **Deep Dive Analysis:** Group findings by topic.
           - **Visuals:** You CANNOT generate images. You MUST use HTML/CSS to visualize numbers.
             - Use **CSS Progress Bars** for percentages.
             - Use **Colored Badges** for status.
             - Use **HTML Tables** for data snapshots.
        4. **Segmentation Special:** If 'SEGMENTATION ANALYSIS' is present, create a dedicated Card showing the Cluster Stats Table.
           - **Crucial:** Invent 2-word Business Personas for each cluster (e.g., 'Cluster 0' -> 'High-Value Loyalists').
        5. **Risk & Opportunity Radar:** Highlight Anomalies (Risks) & Forecasts (Opportunities).
        
        Output ONLY the raw HTML code. Do not use Markdown blocks.
        """
        
        raw_html = self.ai._call_ai(report_prompt)
        # Final cleanup
        return raw_html.replace("```html", "").replace("```", "").strip()