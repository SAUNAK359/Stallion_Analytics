import streamlit as st
import streamlit.components.v1 as components 
import plotly.express as px
from modules.state_manager import init_session_state, set_page
from streamlit_extras.metric_cards import style_metric_cards
from modules.db_manager import StallionDB
from modules.llm_engine import DashboardBrain
from modules.renderer import StallionRenderer
from modules.copilot import StallionCopilot
from modules.reporter import StallionReporter
from modules.planner import StallionPlanner 
from modules.segmentor import StallionSegmentor
from modules.workspace import StallionWorkspace # <--- NEW IMPORT

# 1. Page Config
st.set_page_config(page_title="Stallion Analytics", page_icon="🐎", layout="wide", initial_sidebar_state="expanded")

# 2. Load CSS (Standard)
def load_css():
    try:
        with open("assets/style.css") as f: st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except: pass

# 3. Sidebar (Updated Navigation)
def render_sidebar():
    with st.sidebar:
        st.title("🐎 Stallion")
        st.caption("Enterprise Edition v5.5")
        st.markdown("---")
        if st.button("🏠 Home", use_container_width=True): set_page("Home")
        if st.button("📊 Dashboard", use_container_width=True): set_page("Dashboard")
        if st.button("📂 Your Work", use_container_width=True): set_page("Workspace") # <--- NEW
        if st.button("📑 Planner (Agent)", use_container_width=True): set_page("Planner")
        if st.button("👥 Segmentation", use_container_width=True): set_page("Segmentation")
        st.markdown("---")
        with st.expander("⚙️ AI Settings", expanded=False):
            provider = st.selectbox("AI Provider", ["Google Gemini", "OpenAI"])
            st.session_state["ai_provider"] = provider
            api_key = st.text_input("API Key", type="password")
            if api_key: st.session_state["api_key"] = api_key
            st.session_state["ai_model"] = "gemini-2.5-pro" if provider == "Google Gemini" else "gpt-3.5-turbo"

# --- CO-PILOT (Standard) ---
def render_copilot():
    if not st.session_state.get("db_engine"): return
    with st.popover("💬", use_container_width=False):
        st.subheader("Stallion Co-Pilot")
        # ... (Same Co-Pilot logic as previous version) ...
        # (Included in full file, abbreviated here for brevity)
        config = st.session_state.get("dashboard_config", {})
        context_options = ["Global (All Data)"]
        if "charts" in config:
            for chart in config["charts"]:
                context_options.append(f"Chart: {chart.get('title', 'Untitled')}")
                
        selected_context = st.selectbox("🎯 Focus Context:", context_options, index=0)

        chat_container = st.container(height=300)
        with chat_container:
            for msg in st.session_state["chat_history"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        if prompt := st.chat_input("Ask or Change..."):
            st.session_state["chat_history"].append({"role": "user", "content": prompt})
            
            with chat_container:
                with st.chat_message("user"): st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        copilot = StallionCopilot(
                            st.session_state["ai_provider"],
                            st.session_state.get("api_key"),
                            st.session_state["ai_model"],
                            st.session_state["db_engine"]
                        )
                        result = copilot.process_query(
                            prompt, 
                            st.session_state.get("dashboard_config", {}),
                            st.session_state.get("data_metadata", ""),
                            selected_context
                        )
                        
                        msg_text = result.get("content", "Error")
                        if result.get("response_type") == "update_dashboard":
                            st.session_state["dashboard_config"] = result["content"]
                            st.toast("✅ Dashboard Updated!", icon="📊")
                            st.rerun()
                        elif result.get("response_type") == "update_executive_summary":
                            st.session_state["enterprise_report"] = result["content"]
                            msg_text = "✅ Planner Report Updated. Check Planner Tab."
                            st.toast("✅ Report Generated!", icon="📑")
                        
                        st.markdown(msg_text)
                        
                        if "suggestions" in result:
                            st.caption("Suggested next steps:")
                            cols = st.columns(len(result["suggestions"]))
                            for i, sugg in enumerate(result["suggestions"]):
                                cols[i].button(sugg, key=f"sugg_{len(st.session_state['chat_history'])}_{i}")

            st.session_state["chat_history"].append({"role": "assistant", "content": msg_text})
            if result.get("response_type") != "update_dashboard":
                 st.rerun()

# 4. Page: Home (Standard)
def page_home():
    st.title("Welcome to Stallion Analytics")
    uploaded_files = st.file_uploader("Upload Data", type=["csv", "json", "parquet"], accept_multiple_files=True)
    if uploaded_files and st.button("Initialize Engine", type="primary"):
        db = StallionDB()
        error, msg = db.ingest_data(uploaded_files)
        if not error:
            st.session_state["db_engine"] = db
            st.session_state["data_metadata"] = db.get_schema()
            st.success(msg)
            if st.button("Go to Dashboard"): set_page("Dashboard")

# 5. Page: Dashboard (Updated with SAVE Button)
def page_dashboard():
    st.header("Dashboard")
    if not st.session_state.get("db_engine"):
        st.info("No Data Loaded.")
        return

    # SAVE BUTTON IN HEADER
    c1, c2 = st.columns([0.85, 0.15])
    with c2:
        if st.button("💾 Save Work", use_container_width=True):
            st.session_state["show_save_dialog"] = True

    # Save Dialog (Modal Simulation)
    if st.session_state.get("show_save_dialog"):
        with st.container(border=True):
            st.markdown("#### Save Dashboard to Workspace")
            save_name = st.text_input("Dashboard Name")
            save_desc = st.text_area("Analysis Context (Intent)")
            if st.button("Confirm Save", type="primary"):
                ws = StallionWorkspace()
                # Initialize Copilot just for generating the signature
                copilot = None
                if st.session_state.get("api_key"):
                    copilot = StallionCopilot(st.session_state["ai_provider"], st.session_state["api_key"], st.session_state["ai_model"], None)
                
                ws.save_work(save_name, save_desc, st.session_state.get("dashboard_config"), copilot)
                st.success("Saved to Workspace!")
                st.session_state["show_save_dialog"] = False
                st.rerun()

    # ... (Rest of Dashboard Logic: Brain, Renderer) ...
    # (Same as previous version)
    renderer = StallionRenderer(st.session_state["db_engine"])
    renderer.render(st.session_state.get("dashboard_config", {}))

# 6. Page: Workspace (NEW)
def page_workspace():
    st.header("📂 Your Work")
    ws = StallionWorkspace()
    saved_items = ws.list_work()
    
    if not saved_items:
        st.info("No saved dashboards found. Go to Dashboard and click 'Save Work'.")
        return

    for item in saved_items:
        with st.container(border=True):
            c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
            with c1:
                st.subheader(item['name'])
                st.caption(f"Created: {item['created_at']}")
                st.markdown(f"**Intent:** {item['description']}")
                if item.get('context_signature'):
                    st.info(f"🧠 **AI Context:** {item['context_signature'].get('automated_summary')}")
            
            with c2:
                if st.button("📂 Load", key=f"load_{item['id']}", use_container_width=True):
                    st.session_state["dashboard_config"] = item['config']
                    # Inject Context for Planner
                    st.session_state["loaded_context"] = item.get("context_signature")
                    st.toast("Dashboard Loaded! Go to Dashboard tab.", icon="✅")
                
                if st.button("📑 Send to Planner", key=f"plan_{item['id']}", use_container_width=True):
                    st.session_state["dashboard_config"] = item['config']
                    st.session_state["loaded_context"] = item.get("context_signature")
                    set_page("Planner") # Auto-navigate
                    st.rerun()

            with c3:
                if st.button("🗑️ Delete", key=f"del_{item['id']}", type="primary", use_container_width=True):
                    ws.delete_work(item['id'])
                    st.rerun()

# 7. Page: Planner (Updated for Context)
def page_planner():
    st.header("📑 Stallion Planner: Strategic Reporting")
    if not st.session_state.get("db_engine"):
        st.warning("⚠️ No Data.")
        return

    # Check for Loaded Context
    loaded_ctx = st.session_state.get("loaded_context")
    if loaded_ctx:
        st.info(f"🧠 Planner is context-aware: Investigating '{loaded_ctx.get('intent')}'")

    with st.container(border=True):
        st.subheader("🎯 Define Your Objective")
        # Pre-fill objective if context exists
        default_obj = loaded_ctx.get('intent') if loaded_ctx else ""
        user_objective = st.text_area("Goal:", value=default_obj, placeholder="Analyze Q3...")
        
        if st.button("🚀 Generate Report", type="primary"):
            planner = StallionPlanner(
                st.session_state["db_engine"], st.session_state["ai_provider"], 
                st.session_state["api_key"], st.session_state["ai_model"]
            )
            # ... (Progress Bar Logic) ...
            progress_text = "Initializing Agent..."
            my_bar = st.progress(0, text=progress_text)
            
            try:
                # 1. Recall
                my_bar.progress(25, text="Step 1/4: Auditing Dashboard (Recall)...")
                
                # 2. Hypothesis
                my_bar.progress(50, text="Step 2/4: Formulating Hypotheses & SQL...")
                
                # 3. Reasoning
                my_bar.progress(75, text="Step 3/4: Running Analytics Tools (Anomaly/Forecast)...")
                
                config = st.session_state.get("dashboard_config", {})
                # Pass the loaded_ctx to the generate function
                report_html = planner.generate_enterprise_report(config, user_objective, loaded_ctx) 
                
                 # 4. Layout
                my_bar.progress(100, text="Step 4/4: Rendering Presentation (Layout)...")
                
                st.session_state["enterprise_report"] = report_html
                st.rerun()
             
            except Exception as e:
                st.error(f"Planner Failed: {str(e)}")

    if "enterprise_report" in st.session_state:
        components.html(st.session_state["enterprise_report"], height=800, scrolling=True)

# 8. Page: Segmentation (Standard)
def page_segmentation():
    st.header("👥 Agentic Segmentation Lab")
    
    if not st.session_state.get("db_engine"):
        st.warning("⚠️ No Data Loaded.")
        return

    st.markdown("Identify hidden customer groups using **RFM Analysis** and **Unsupervised Learning (K-Means)**.")
    
    if st.button("🚀 Run Auto-Segmentation", type="primary"):
        if not st.session_state.get("api_key"):
            st.error("Configure AI Settings first (for naming clusters).")
            return
            
        segmentor = StallionSegmentor()
        db = st.session_state["db_engine"]
        # Get Sample for Clustering (DuckDB)
        df = db.get_sample(limit=50000) 
        
        with st.spinner("Calculating RFM & Clustering..."):
            rfm_df, summary = segmentor.perform_rfm_analysis(df)
            
            if rfm_df is not None:
                st.session_state["rfm_result"] = rfm_df
                
                # AI Naming
                copilot = StallionCopilot(
                    st.session_state["ai_provider"], 
                    st.session_state["api_key"], 
                    st.session_state["ai_model"], 
                    db
                )
                prompt = f"""
                Analyze these Customer Segments (RFM Stats):
                {summary}
                
                Task: Name each cluster (0-3) with a short Business Persona & Emoji.
                Example: {{ "0": "🏆 Champions", "1": "💤 Sleepers" }}
                Return JSON only.
                """
                try:
                    names = copilot._clean_json(copilot._call_ai(prompt))
                    st.session_state["segment_names"] = names
                    st.rerun()
                except:
                    st.error("AI Naming Failed. Showing raw clusters.")
            else:
                st.error(summary)

    if "rfm_result" in st.session_state:
        rfm = st.session_state["rfm_result"]
        names = st.session_state.get("segment_names", {})
        
        # Map Names
        rfm['Segment'] = rfm['Cluster'].astype(str).map(lambda x: names.get(x, f"Cluster {x}"))
        
        st.subheader("Cluster Visualization")
        
        # 3D Chart
        fig = px.scatter_3d(
            rfm, x='Recency', y='Frequency', z='Monetary',
            color='Segment', opacity=0.7,
            title="Customer Segments (3D View)",
            template="plotly_dark"
        )
        fig.update_layout(height=600, margin=dict(l=0, r=0, b=0, t=30))
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("View Segment Data"):
            st.dataframe(rfm, use_container_width=True)

# MAIN EXECUTION
if __name__ == "__main__":
    init_session_state()
    load_css()
    render_sidebar()
    
    page = st.session_state["page"]
    if page == "Home": page_home()
    elif page == "Dashboard": page_dashboard()
    elif page == "Workspace": page_workspace()
    elif page == "Planner": page_planner()
    elif page == "Segmentation": page_segmentation()
        
    render_copilot()