import json
import os
import datetime
from modules.copilot import StallionCopilot

WORKSPACE_FILE = "stallion_workspace.json"

class StallionWorkspace:
    """
    The Persistence Engine for Stallion Analytics.
    Manages 'Context-Injected' Saves.
    """
    
    def __init__(self):
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(WORKSPACE_FILE):
            with open(WORKSPACE_FILE, 'w') as f:
                json.dump({}, f)

    def save_work(self, name, description, dashboard_config, ai_engine=None):
        """
        Saves the dashboard with an AI-generated Context Signature.
        """
        # 1. Generate Context Signature (if AI is available)
        context_signature = {
            "intent": description, # User defined
            "automated_summary": "No AI summary available."
        }
        
        if ai_engine and dashboard_config:
            try:
                # Extract chart titles for context
                titles = [c.get('title') for c in dashboard_config.get('charts', [])]
                kpis = [k.get('label') for k in dashboard_config.get('kpi_cards', [])]
                
                prompt = f"""
                Generate a 'Context Signature' for this dashboard configuration.
                Charts: {titles}
                KPIs: {kpis}
                User Description: "{description}"
                
                Task: Summarize the ANALYTICAL INTENT in 1 sentence. (e.g. "Investigating Q3 regional sales dip.")
                """
                context_signature["automated_summary"] = ai_engine._call_ai(prompt).strip()
            except:
                pass

        # 2. Construct Record
        record = {
            "id": name.lower().replace(" ", "_"),
            "name": name,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "description": description,
            "context_signature": context_signature,
            "config": dashboard_config
        }
        
        # 3. Write to Disk
        with open(WORKSPACE_FILE, 'r') as f:
            data = json.load(f)
        
        data[record["id"]] = record
        
        with open(WORKSPACE_FILE, 'w') as f:
            json.dump(data, f, indent=4)
            
        return True

    def list_work(self):
        """Returns a list of saved dashboards."""
        with open(WORKSPACE_FILE, 'r') as f:
            data = json.load(f)
        return list(data.values())

    def load_work(self, work_id):
        """Returns the specific dashboard record."""
        with open(WORKSPACE_FILE, 'r') as f:
            data = json.load(f)
        return data.get(work_id)

    def delete_work(self, work_id):
        with open(WORKSPACE_FILE, 'r') as f:
            data = json.load(f)
        
        if work_id in data:
            del data[work_id]
            with open(WORKSPACE_FILE, 'w') as f:
                json.dump(data, f)
            return True
        return False