import streamlit as st
from modules.state_manager import init_session_state, set_page
from streamlit_extras.metric_cards import style_metric_cards
from modules.data_loader import StallionLoader
from modules.llm_engine import DashboardBrain
from modules.renderer import StallionRenderer
from modules.copilot import StallionCopilot
from modules.reporter import StallionReporter
from modules.reporter import StallionReporter
st.set_page_config(
    page_title="Stallion Analytics",
    page_icon="🐎",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_css():
    try:
        with open("assets/style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

def render_sidebar():
    with st.sidebar:
        st.title("🐎 Stallion")
        st.markdown("---")
        if st.button("🏠 Home", use_container_width=True):
            set_page("Home")
        if st.button("📊 Dashboard", use_container_width=True):
            set_page("Dashboard")
        if st.button("🧠 Analytics (Co-Pilot)", use_container_width=True):
            set_page("Analytics")
        st.markdown("---")
        with st.expander("🔐 API Settings", expanded=False):
            provider = st.selectbox("AI Provider", ["Google Gemini", "OpenAI"])
            st.session_state["ai_provider"] = provider
            label = f"{provider} API Key"
            key = st.text_input(label, type="password", key="api_key_input")
            if key:
                st.session_state["api_key"] = key
                st.success("Key Saved")
        st.caption("Stallion AI v1.0.0")

def page_home():
    st.title("Welcome to Stallion Analytics")
    st.markdown("### Agentic Interactive Dashboard Engine")
    uploaded_file = st.file_uploader(
        "Upload your Data Source (CSV, JSON, Excel)", 
        type=["csv", "xlsx", "xls", "json"],
        help="Supported formats: CSV, Excel, JSON. Handles messy dates & encoding automatically."
    )
    if uploaded_file:
        if st.button("Initialize Stallion Engine", type="primary"):
            with st.spinner("Ingesting Data... Sanitizing Schema... Detecting Date Objects..."):
                df, error = StallionLoader.load_file(uploaded_file)
                if error:
                    st.error(error)
                else:
                    st.session_state["raw_data"] = df
                    st.session_state["processed_data"] = df
                    meta = StallionLoader.get_metadata(df)
                    st.session_state["data_metadata"] = meta 
                    st.success(f"Data Successfully Ingested! Shape: {df.shape}")
                    with st.expander("Inspect Raw Data (Sanitized)"):
                        st.dataframe(df.head(10), use_container_width=True)
                    st.info("System Ready. Proceed to Dashboard or Analytics.")
                    c1, c2 = st.columns(2)
                    if c1.button("Go to Dashboard"):
                        set_page("Dashboard")
                    if c2.button("Ask Co-Pilot"):
                        set_page("Analytics")
    st.markdown("---")
    st.subheader("System Status")
    c1, c2, c3 = st.columns(3)
    c1.metric("Engine Status", "Online", "Ready")
    c2.metric("Active Agents", "3", "Idle")
    if st.session_state["raw_data"] is not None:
        c3.metric("Data Loaded", "Yes", f"{len(st.session_state['raw_data'])} rows")
    else:
        c3.metric("Data Loaded", "No", "Waiting")
    style_metric_cards(background_color="#141928", border_left_color="#00E5FF")

def page_dashboard():
    st.header("Dashboard")
    if st.session_state["raw_data"] is None:
        st.info("No Data Loaded. Please go to Home and upload a dataset.")
        if st.button("Go to Home"):
            set_page("Home")
        return
    if not st.session_state.get("dashboard_config"):
        st.subheader("🤖 AI Architecting Session")
        st.write("The AI is analyzing your data schema to design the optimal dashboard layout.")
        col1, col2 = st.columns([3, 1])
        with col1:
            intent = st.text_input("What is the goal of this dashboard?", "Overview of performance and key trends")
        if st.button("Generate Dashboard Layout", type="primary"):
            api_key = st.session_state.get("api_key")
            provider = st.session_state.get("ai_provider", "Google Gemini")
            model = st.session_state.get("ai_model")
            brain = DashboardBrain(provider=provider, api_key=api_key, model=model)
            with st.spinner(f"Contacting {provider}... Designing Layout..."):
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
    config = st.session_state["dashboard_config"]
    df = st.session_state["processed_data"]
    renderer = StallionRenderer(df)
    c1, c2 = st.columns([0.8, 0.2])
    with c1:
        st.caption(f"Generated via {st.session_state.get('ai_provider', 'Mock')}")
    with c2:
        if st.button("Regenerate Layout", use_container_width=True):
            st.session_state["dashboard_config"] = {}
            st.rerun()
    renderer.render(config)

    st.markdown("---")
    st.subheader("📝 Intelligent Reporting")
    if "report_narrative" not in st.session_state:
        st.session_state["report_narrative"] = None
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Generate Executive Brief", type="primary", use_container_width=True):
            from modules.copilot import StallionCopilot
            copilot = StallionCopilot(
                provider=st.session_state.get("ai_provider"),
                api_key=st.session_state.get("api_key"),
                model=st.session_state.get("ai_model"),
                df=df
            )
            reporter = StallionReporter(None)
            sys_prompt, user_msg = reporter.generate_narrative(df, config)
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
                kpi_values = {}
                if "kpi_cards" in config:
                    for kpi in config["kpi_cards"]:
                        col = kpi.get("column")
                        op = kpi.get("operation", "count")
                        if col in df.columns:
                            if op == "sum": val = df[col].sum()
                            elif op == "avg": val = df[col].mean()
                            elif op == "count": val = len(df)
                            else: val = 0
                            if kpi.get("format") == "currency": val = f"${val:,.2f}"
                            else: val = f"{val:,.2f}"
                            kpi_values[kpi.get("label")] = val
                html_link = StallionReporter.create_html_report(
                    st.session_state["report_narrative"], 
                    kpi_values,
                    config
                )
                st.markdown(html_link, unsafe_allow_html=True)


def page_analytics():
    st.header("🧠 Co-Pilot Interface")
    if st.session_state["raw_data"] is None:
        st.warning("Please upload data in Home first.")
        return
    if "api_key" not in st.session_state:
        st.warning("Please configure AI Settings in the Sidebar.")
        return
    if not st.session_state.get("dashboard_config"):
        st.info("No active dashboard found. Please generate one in the 'Dashboard' tab first.")
        return
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    if prompt := st.chat_input("Ask me to analyze data or modify the dashboard..."):
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                copilot = StallionCopilot(
                    provider=st.session_state["ai_provider"],
                    api_key=st.session_state["api_key"],
                    model=st.session_state["ai_model"],
                    df=st.session_state["processed_data"]
                )
                result = copilot.process_query(
                    prompt, 
                    st.session_state["dashboard_config"],
                    st.session_state["data_metadata"]
                )
                if result.get("response_type") == "update_dashboard":
                    new_config = result["content"]
                    st.session_state["dashboard_config"] = new_config
                    response_msg = "✅ Dashboard updated based on your request. Check the Dashboard tab."
                    st.markdown(response_msg)
                    st.session_state["chat_history"].append({"role": "assistant", "content": response_msg})
                    with st.expander("View Configuration Changes"):
                        st.json(new_config)
                else:
                    answer = result.get("content", "I couldn't process that.")
                    st.markdown(answer)
                    st.session_state["chat_history"].append({"role": "assistant", "content": answer})

if __name__ == "__main__":
    init_session_state()
    load_css()
    render_sidebar()
    if st.session_state["page"] == "Home":
        page_home()
    elif st.session_state["page"] == "Dashboard":
        page_dashboard()
    elif st.session_state["page"] == "Analytics":
        page_analytics()
