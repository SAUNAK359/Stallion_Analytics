import streamlit as st
from modules.state_manager import init_session_state, set_page
from streamlit_extras.metric_cards import style_metric_cards
from modules.db_manager import StallionDB
from modules.llm_engine import DashboardBrain
from modules.renderer import StallionRenderer
from modules.copilot import StallionCopilot
from modules.reporter import StallionReporter

# 1. Page Config
st.set_page_config(
    page_title="Stallion Analytics",
    page_icon="🐎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Load CSS
def load_css():
    try:
        with open("assets/style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

# 3. Sidebar
def render_sidebar():
    with st.sidebar:
        st.title("🐎 Stallion")
        st.caption("Enterprise Edition v3.0")
        st.markdown("---")
        
        # Navigation
        if st.button("🏠 Home", use_container_width=True): set_page("Home")
        if st.button("📊 Dashboard", use_container_width=True): set_page("Dashboard")
        # Note: 'Analytics' page is removed because it's now a floating widget
        
        st.markdown("---")
        
        # API Settings
        with st.expander("⚙️ AI Settings", expanded=False):
            provider = st.selectbox("AI Provider", ["Google Gemini", "OpenAI"])
            st.session_state["ai_provider"] = provider
            
            key_name = "Gemini Key" if provider == "Google Gemini" else "OpenAI Key"
            api_key = st.text_input(key_name, type="password")
            
            if api_key: st.session_state["api_key"] = api_key
            
            # Set Model Defaults
            st.session_state["ai_model"] = "gemini-2.5-pro" if provider == "Google Gemini" else "gpt-3.5-turbo"
            
        st.caption("Stallion AI v3.0.0")

# --- FLOATING CO-PILOT WIDGET ---
def render_copilot():
    """
    Renders the floating chat bubble on every page with Toast notifications.
    """
    # Only show if data is loaded
    if not st.session_state.get("db_engine"):
        return

    # Floating Popover (CSS makes it float bottom-right)
    with st.popover("💬", use_container_width=False):
        st.subheader("Stallion Co-Pilot")
        
        # 1. CONTEXT SELECTOR
        # Scan dashboard config to find charts
        config = st.session_state.get("dashboard_config", {})
        context_options = ["Global (All Data)"]
        
        if "charts" in config:
            for chart in config["charts"]:
                context_options.append(f"Chart: {chart.get('title', 'Untitled')}")
        if "kpi_cards" in config:
            for kpi in config["kpi_cards"]:
                context_options.append(f"KPI: {kpi.get('label', 'Metric')}")
                
        selected_context = st.selectbox("🎯 Focus Context:", context_options, index=0)

        # 2. CHAT HISTORY
        chat_container = st.container(height=300)
        with chat_container:
            for msg in st.session_state["chat_history"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # 3. INPUT
        if prompt := st.chat_input("Ask or Change..."):
            # Append User Msg
            st.session_state["chat_history"].append({"role": "user", "content": prompt})
            
            # Show spinner inside the chat window
            with chat_container:
                with st.chat_message("user"): st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Analyzing..."):
                        copilot = StallionCopilot(
                            provider=st.session_state["ai_provider"],
                            api_key=st.session_state.get("api_key"),
                            model=st.session_state["ai_model"],
                            db_engine=st.session_state["db_engine"]
                        )
                        
                        # Process with Context
                        result = copilot.process_query(
                            prompt, 
                            st.session_state.get("dashboard_config", {}),
                            st.session_state.get("data_metadata", ""),
                            focused_context=selected_context
                        )
                        
                        # Handle Response
                        if result.get("response_type") == "update_dashboard":
                            st.session_state["dashboard_config"] = result["content"]
                            msg_text = "✅ Dashboard updated based on your command."
                            # Toast Notification for Visibility
                            st.toast("✅ Dashboard Layout Updated!", icon="📊")
                            st.rerun() # Refresh main page to show changes!
                        else:
                            msg_text = result.get("content", "I couldn't generate a response.")
                            st.toast("✅ Analysis Complete", icon="🧠")
                        
                        st.markdown(msg_text)
                        
                        # 4. SMART SUGGESTIONS
                        if "suggestions" in result:
                            st.caption("Suggested next steps:")
                            cols = st.columns(len(result["suggestions"]))
                            for i, sugg in enumerate(result["suggestions"]):
                                cols[i].button(sugg, key=f"sugg_{len(st.session_state['chat_history'])}_{i}")

            # Save Assistant Msg
            st.session_state["chat_history"].append({"role": "assistant", "content": msg_text})
            # We rely on the rerun inside the 'update_dashboard' block for visual updates.
            # If it was just text, we might want to rerun to clear the input box.
            if result.get("response_type") != "update_dashboard":
                 st.rerun()

# 4. Page: Home (Ingestion)
def page_home():
    st.title("Welcome to Stallion Analytics")
    st.markdown("### Enterprise Big Data Engine")
    
    # UPDATED: Accept Multiple Files
    uploaded_files = st.file_uploader(
        "Upload Data (CSV, JSON, Parquet)", 
        type=["csv", "json", "parquet"],
        accept_multiple_files=True, # <--- NEW: Enable multi-file upload
        help="Upload multiple files (e.g. Sales.csv + Customers.csv) for auto-blending."
    )
    
    if uploaded_files:
        if st.button("Initialize Engine", type="primary"):
            with st.spinner("Streaming data into DuckDB..."):
                # Initialize DB
                db = StallionDB()
                # Pass list of files to DB
                error, msg = db.ingest_data(uploaded_files)
                
                if error:
                    st.error(error)
                else:
                    # Success State
                    st.session_state["db_engine"] = db
                    st.session_state["data_metadata"] = db.get_schema()
                    st.session_state["raw_data"] = "DuckDB-Managed" 
                    
                    st.success(f"Success! {msg}")
                    
                    # Preview Data
                    with st.expander("Inspect Sample Rows (First Table)"):
                        st.dataframe(db.get_sample(), use_container_width=True)
                    
                    # Quick Nav
                    if st.button("Go to Dashboard"): set_page("Dashboard")

    # Status Metrics
    st.markdown("---")
    c1, c2 = st.columns(2)
    c1.metric("Engine Status", "Online (DuckDB)", "Ready")
    status = "Loaded" if st.session_state.get("db_engine") else "Waiting"
    c2.metric("Data Status", status, "0ms Latency")
    style_metric_cards(background_color="#141928", border_left_color="#00E5FF")

# 5. Page: Dashboard (Renderer)
def page_dashboard():
    st.header("Dashboard")
    
    # Check for DB Engine
    if not st.session_state.get("db_engine"):
        st.info("No Data Loaded. Please go to Home and upload a dataset.")
        if st.button("Go to Home"): set_page("Home")
        return

    # A. AI Architecting (If no layout exists)
    if not st.session_state.get("dashboard_config"):
        st.subheader("🤖 AI Architecting Session")
        
        # 1. INITIALIZE BRAIN
        brain = DashboardBrain(
            provider=st.session_state.get("ai_provider"),
            api_key=st.session_state.get("api_key"),
            model=st.session_state.get("ai_model")
        )

        # 2. GENERATE SUGGESTIONS (Lazy Load)
        if "intent_suggestions" not in st.session_state:
            with st.spinner("🧠 AI is analyzing schema to find business insights..."):
                suggestions = brain.suggest_intents(st.session_state["data_metadata"])
                st.session_state["intent_suggestions"] = suggestions
        
        # 3. DISPLAY SUGGESTIONS
        st.markdown("##### 💡 Suggested Analyses based on your data:")
        
        # Use columns to create a "Pill" layout
        suggestions = st.session_state.get("intent_suggestions", [])
        cols = st.columns(4) 
        selected_intent = None
        
        for i, suggestion in enumerate(suggestions):
            col = cols[i % 4]
            if col.button(suggestion, use_container_width=True):
                selected_intent = suggestion
        
        st.markdown("---")
        st.write("Or define your own goal:")
        
        # 4. INPUT & GENERATION
        default_val = selected_intent if selected_intent else "Overview of performance trends"
        intent = st.text_input("Dashboard Goal", value=default_val)
        
        if selected_intent or st.button("Generate Layout", type="primary"):
            with st.spinner(f"Architecting Dashboard for: '{intent}'..."):
                config = brain.generate_dashboard_layout(
                    st.session_state["data_metadata"], 
                    intent
                )
                if "error" in config:
                    st.error(config["error"])
                else: 
                    st.session_state["dashboard_config"] = config
                    st.rerun()
        return

    # B. Render Dashboard
    config = st.session_state["dashboard_config"]
    db_engine = st.session_state["db_engine"]
    
    # Initialize SQL Renderer
    renderer = StallionRenderer(db_engine)
    
    # Toolbar
    c1, c2 = st.columns([0.8, 0.2])
    with c1: 
        # Show active filters indicator
        if st.session_state.get("active_filters"):
            st.caption("⚠️ Filtered View Active")
        else:
            st.caption("Live SQL Query Mode")
            
    with c2: 
        if st.button("Reset Layout", use_container_width=True):
            st.session_state["dashboard_config"] = {}
            # Clear suggestions so they regenerate if data changed (optional)
            # st.session_state.pop("intent_suggestions", None) 
            st.rerun()
            
    renderer.render(config)

    # C. Reporting Section
    st.markdown("---")
    st.subheader("📝 Intelligent Reporting")
    if "report_narrative" not in st.session_state:
        st.session_state["report_narrative"] = None
        
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Generate Executive Brief", type="primary", use_container_width=True):
            
            # Initialize CoPilot to generate text
            copilot = StallionCopilot(
                provider=st.session_state.get("ai_provider"),
                api_key=st.session_state.get("api_key"),
                model=st.session_state.get("ai_model"),
                db_engine=db_engine
            )
            
            # Prepare Prompt
            reporter = StallionReporter(None)
            sys_prompt, user_msg = reporter.generate_narrative(db_engine.get_sample(), config)
            
            with st.spinner("AI is analyzing trends and writing the report..."):
                full_prompt = f"{sys_prompt}\n\n{user_msg}"
                narrative = copilot._call_ai(full_prompt)
                st.session_state["report_narrative"] = narrative
                st.rerun()
                
    with col2:
        if st.session_state["report_narrative"]:
            with st.container(border=True):
                st.markdown("### 📋 Executive Summary")
                st.markdown(st.session_state["report_narrative"])
                
                # Calculate KPI values for Report HTML
                kpi_values = {}
                if "kpi_cards" in config:
                    for kpi in config["kpi_cards"]:
                        sql = kpi.get("sql_query")
                        # Note: Reporting uses base SQL, not filtered SQL
                        df_res, _ = db_engine.run_query(sql)
                        if not df_res.empty:
                            val = df_res.iloc[0, 0]
                            if kpi.get("format") == "currency": val = f"${float(val):,.2f}"
                            else: val = f"{float(val):,.2f}"
                            kpi_values[kpi.get("label")] = val

                html_link = StallionReporter.create_html_report(
                    st.session_state["report_narrative"], 
                    kpi_values,
                    config
                )
                st.markdown(html_link, unsafe_allow_html=True)


# MAIN EXECUTION
if __name__ == "__main__":
    init_session_state()
    load_css()
    render_sidebar()
    
    # Render Main Page Content
    if st.session_state["page"] == "Home":
        page_home()
        
    elif st.session_state["page"] == "Dashboard":
        page_dashboard()
        
    # ALWAYS RENDER THE FLOATING WIDGET LAST
    render_copilot()