import streamlit as st

def init_session_state():
    defaults = {
        "page": "Home",
        "raw_data": None,
        "processed_data": None,
        "data_metadata": "",
        "dashboard_config": {},
        "chat_history": [],
        "notifications": [],
        "api_key": None,
        "ai_provider": "Google Gemini", 
        "ai_model": "gemini-2.5-pro"
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if st.session_state["ai_model"] in ["gemini-1.5-flash", "gemini-1.5-pro"]:
        st.session_state["ai_model"] = "gemini-2.5-pro"

def set_page(page_name):
    st.session_state["page"] = page_name
