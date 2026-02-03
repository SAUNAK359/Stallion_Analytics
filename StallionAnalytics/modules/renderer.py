import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from modules.forecaster import StallionForecaster
# Import Copilot for the 'Deep Insights' feature
from modules.copilot import StallionCopilot

class StallionRenderer:
    """
    The Big Data Visualizer with Interactive Cross-Filtering, Forecasting & Deep Insights.
    """
    
    def __init__(self, db_engine):
        self.db = db_engine 
        self.layout_style = dict(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#fafafa'),
            margin=dict(t=30, l=10, r=10, b=10),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
        )
        
        if "active_filters" not in st.session_state:
            st.session_state["active_filters"] = {}

    def render(self, config):
        st.subheader(config.get("dashboard_title", "Analytics Dashboard"))
        
        # ACTIVE FILTERS UI
        if st.session_state["active_filters"]:
            filters_text = "  |  ".join([f"**{k}** = '{v}'" for k, v in st.session_state["active_filters"].items()])
            with st.container(border=True):
                col1, col2 = st.columns([0.85, 0.15])
                col1.markdown(f"🔍 **Active Filters:** {filters_text}")
                if col2.button("✖ Clear", use_container_width=True):
                    st.session_state["active_filters"] = {}
                    st.rerun()
        
        # 1. KPIs
        if "kpi_cards" in config:
            self._render_sql_kpis(config["kpi_cards"])
        st.markdown("---")
        # 2. Charts
        if "charts" in config:
            self._render_sql_charts(config["charts"])

    def _inject_filters(self, sql):
        if not st.session_state["active_filters"]: return sql
        clauses = []
        for col, val in st.session_state["active_filters"].items():
            if isinstance(val, str): clauses.append(f"{col} = '{val}'")
            else: clauses.append(f"{col} = {val}")
        filter_sql = " AND ".join(clauses)
        return f"SELECT * FROM ({sql}) WHERE {filter_sql}"

    def _render_sql_kpis(self, kpis):
        cols = st.columns(len(kpis))
        for idx, kpi in enumerate(kpis):
            with cols[idx]:
                filtered_sql = self._inject_filters(kpi.get("sql_query"))
                df, _ = self.db.run_query(filtered_sql)
                val = "N/A"
                if not df.empty: val = self._format_metric(df.iloc[0, 0], kpi.get("format"))
                st.markdown(f"""
                <div class="css-1r6slb0">
                    <h4 style='margin:0; color:#94a3b8; font-size:14px;'>{kpi.get('label')}</h4>
                    <h2 style='margin:0; color:#fff; font-size:28px;'>{val}</h2>
                </div>
                """, unsafe_allow_html=True)

    def _render_sql_charts(self, charts):
        for i in range(0, len(charts), 2):
            c1, c2 = st.columns(2)
            with c1: self._draw_chart(charts[i], key=f"chart_{i}")
            if i + 1 < len(charts):
                with c2: self._draw_chart(charts[i+1], key=f"chart_{i+1}")

    def _draw_chart(self, chart_config, key):
        title = chart_config.get("title", "Untitled Chart")
        base_sql = chart_config.get("sql_query")
        c_type = chart_config.get("type", "bar")
        description = chart_config.get("description")
        
        # 1. Execution
        filtered_sql = self._inject_filters(base_sql)
        df, error = self.db.run_query(filtered_sql)
        
        if error:
            st.error(f"Query Failed for '{title}': {error}")
            return
        if df.empty:
            st.info(f"No data for '{title}'")
            return

        # 2. Axes
        x_col = chart_config.get("x_column", df.columns[0])
        y_col = chart_config.get("y_column", df.columns[1] if len(df.columns) > 1 else df.columns[0])
        color_col = chart_config.get("color_column", None)

        # 3. FORECAST WIDGET
        is_time_series = False
        try:
            pd.to_datetime(df[x_col])
            is_time_series = True
        except:
            is_time_series = False

        forecast_df = None
        growth = 0.0
        
        if is_time_series and c_type in ["line", "area", "bar"]:
            with st.expander(f"🔮 Forecast Lab: {title}", expanded=False):
                c1, c2, c3 = st.columns([0.2, 0.4, 0.4])
                enable_forecast = c1.checkbox("Active", key=f"fc_en_{key}")
                periods = c2.slider("Horizon", 1, 24, 6, key=f"fc_per_{key}")
                growth = c3.slider("Growth %", -50, 50, 0, key=f"fc_gro_{key}") / 100.0
                
                if enable_forecast:
                    forecaster = StallionForecaster()
                    with st.spinner("Modeling..."):
                        forecast_df, info = forecaster.generate_forecast(df, x_col, y_col, periods, growth)
                        st.caption(f"**Model:** {info}")

        try:
            # 4. Plotly Chart
            if c_type == "bar": fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=title, template="plotly_dark")
            elif c_type == "line": fig = px.line(df, x=x_col, y=y_col, color=color_col, title=title, template="plotly_dark")
            elif c_type == "pie": fig = px.pie(df, names=x_col, values=y_col, title=title, template="plotly_dark")
            elif c_type == "scatter": fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=title, template="plotly_dark")
            elif c_type == "area": fig = px.area(df, x=x_col, y=y_col, color=color_col, title=title, template="plotly_dark")
            else: fig = px.bar(df, x=x_col, y=y_col, title=title, template="plotly_dark")

            if forecast_df is not None:
                fig.add_trace(go.Scatter(x=forecast_df[x_col], y=forecast_df[y_col], mode='lines', name=f'Forecast ({int(growth*100)}%)', line=dict(color='#00E5FF', width=3, dash='dot')))

            fig.update_layout(self.layout_style)
            selection = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key=key)
            
            # 5. DEEP INSIGHTS (Interactive Agent)
            with st.expander(f"🧠 Deep Insights: {title}"):
                if st.button("⚡ Analyze this Chart", key=f"anl_{key}"):
                    if st.session_state.get("api_key"):
                        copilot = StallionCopilot(
                            st.session_state.get("ai_provider"), 
                            st.session_state.get("api_key"), 
                            st.session_state.get("ai_model"),
                            self.db
                        )
                        with st.spinner("Agent is analyzing data patterns..."):
                            insight = copilot.generate_chart_insight(df, title)
                            st.markdown(insight)
                    else:
                        st.error("Please configure AI Settings in Sidebar.")
                else:
                    if description: st.info(f"Context: {description}")
                    else: st.caption("Click Analyze for AI-driven observations.")

            # 6. Click Handler
            if selection and selection["selection"]["points"]:
                point = selection["selection"]["points"][0]
                if "x" in point:
                    st.session_state["active_filters"][x_col] = point["x"]
                    st.rerun()

        except Exception as e:
            st.warning(f"Plotting Error in '{title}': {str(e)}")

    def _format_metric(self, val, fmt):
        try:
            if val is None: return "0"
            val = float(val)
            if fmt == "currency": return f"${val:,.2f}"
            elif fmt == "percent": return f"{val:.1f}%"
            else: 
                if val.is_integer(): return f"{int(val):,}"
                return f"{val:,.2f}"
        except: return str(val)