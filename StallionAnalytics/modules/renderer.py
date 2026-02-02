import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

class StallionRenderer:
    """
    The Big Data Visualizer with Interactive Cross-Filtering.
    Executes SQL queries on demand -> Renders Plotly Charts.
    """
    
    def __init__(self, db_engine):
        self.db = db_engine # Reference to StallionDB instance
        # Common Plotly Layout for "Stallion Theme"
        self.layout_style = dict(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#fafafa'),
            margin=dict(t=30, l=10, r=10, b=10),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
        )
        
        # Initialize filter state if missing
        if "active_filters" not in st.session_state:
            st.session_state["active_filters"] = {}

    def render(self, config):
        """Main rendering loop."""
        st.subheader(config.get("dashboard_title", "Analytics Dashboard"))
        
        # DISPLAY ACTIVE FILTERS (Cross-Filtering UI)
        if st.session_state["active_filters"]:
            # Format display string
            filters_text = "  |  ".join([f"**{k}** = '{v}'" for k, v in st.session_state["active_filters"].items()])
            
            # Info box with Clear button
            with st.container(border=True):
                col1, col2 = st.columns([0.85, 0.15])
                col1.markdown(f"🔍 **Active Filters:** {filters_text}")
                if col2.button("✖ Clear", use_container_width=True):
                    st.session_state["active_filters"] = {}
                    st.rerun()
        
        # 1. Render KPI Row
        if "kpi_cards" in config:
            self._render_sql_kpis(config["kpi_cards"])
            
        st.markdown("---")
        
        # 2. Render Charts Grid
        if "charts" in config:
            self._render_sql_charts(config["charts"])

    def _inject_filters(self, sql):
        """
        Dynamically appends WHERE clauses to the SQL based on active filters.
        Wraps the original query in a CTE/Subquery to ensure safety.
        """
        if not st.session_state["active_filters"]:
            return sql
            
        # Construct WHERE clause
        clauses = []
        for col, val in st.session_state["active_filters"].items():
            if isinstance(val, str):
                clauses.append(f"{col} = '{val}'")
            else:
                clauses.append(f"{col} = {val}")
        
        filter_sql = " AND ".join(clauses)
        
        # Wrap the original query to filter the RESULT set.
        # This is the safest way to handle GROUP BY / ORDER BY in the original SQL.
        # "SELECT * FROM ( <original_query> ) WHERE <filters>"
        return f"SELECT * FROM ({sql}) WHERE {filter_sql}"

    def _render_sql_kpis(self, kpis):
        """Calculates and renders metric cards using SQL (Filtered)."""
        cols = st.columns(len(kpis))
        
        for idx, kpi in enumerate(kpis):
            with cols[idx]:
                base_sql = kpi.get("sql_query")
                # INJECT FILTERS
                filtered_sql = self._inject_filters(base_sql)
                
                label = kpi.get("label", "Metric")
                
                df, error = self.db.run_query(filtered_sql)
                
                if error:
                    value = "Err"
                    # st.error(f"SQL Error: {error}") # Optional: hide error text in UI for KPIs
                elif df.empty:
                    value = "N/A"
                else:
                    raw_val = df.iloc[0, 0]
                    value = self._format_metric(raw_val, kpi.get("format"))

                st.markdown(f"""
                <div class="css-1r6slb0">
                    <h4 style='margin:0; color:#94a3b8; font-size:14px;'>{label}</h4>
                    <h2 style='margin:0; color:#fff; font-size:28px;'>{value}</h2>
                </div>
                """, unsafe_allow_html=True)

    def _render_sql_charts(self, charts):
        """Layouts charts in a 2-column grid."""
        for i in range(0, len(charts), 2):
            c1, c2 = st.columns(2)
            
            # Chart 1
            with c1:
                self._draw_chart(charts[i], key=f"chart_{i}")
            
            # Chart 2 (if exists)
            if i + 1 < len(charts):
                with c2:
                    self._draw_chart(charts[i+1], key=f"chart_{i+1}")

    def _draw_chart(self, chart_config, key):
        """Executes SQL and draws a single Plotly chart with Click Events."""
        title = chart_config.get("title", "Untitled Chart")
        base_sql = chart_config.get("sql_query")
        c_type = chart_config.get("type", "bar")
        description = chart_config.get("description")
        
        # 1. INJECT FILTERS & EXECUTE SQL
        filtered_sql = self._inject_filters(base_sql)
        df, error = self.db.run_query(filtered_sql)
        
        if error:
            st.error(f"Query Failed for '{title}': {error}")
            return
            
        if df.empty:
            st.info(f"No data returned for '{title}' (Check filters)")
            return

        # 2. DETERMINE AXES
        x_col = chart_config.get("x_column", df.columns[0])
        y_col = chart_config.get("y_column", df.columns[1] if len(df.columns) > 1 else df.columns[0])
        color_col = chart_config.get("color_column", None)

        try:
            # 3. GENERATE PLOTLY CHART
            if c_type == "bar":
                fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=title, template="plotly_dark")
            elif c_type == "line":
                fig = px.line(df, x=x_col, y=y_col, color=color_col, title=title, template="plotly_dark")
            elif c_type == "pie":
                fig = px.pie(df, names=x_col, values=y_col, title=title, template="plotly_dark")
            elif c_type == "scatter":
                fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=title, template="plotly_dark")
            elif c_type == "area":
                fig = px.area(df, x=x_col, y=y_col, color=color_col, title=title, template="plotly_dark")
            else:
                fig = px.bar(df, x=x_col, y=y_col, title=title, template="plotly_dark")

            fig.update_layout(self.layout_style)
            
            # 4. RENDER WITH SELECTION EVENTS
            # on_select="rerun" ensures the app reloads when clicked
            selection = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key=key)
            
            # Add Description/Insight
            if description:
                st.caption(f"💡 {description}")
                
            # 5. HANDLE CLICK EVENT
            if selection and selection["selection"]["points"]:
                point = selection["selection"]["points"][0]
                
                # Try to extract the category value (x-axis usually)
                if "x" in point:
                    selected_val = point["x"]
                    
                    # Update Session State and Rerun
                    st.session_state["active_filters"][x_col] = selected_val
                    st.rerun()

        except Exception as e:
            st.warning(f"Plotting Error in '{title}': {str(e)}")

    def _format_metric(self, val, fmt):
        """Helper to format raw numbers into strings."""
        try:
            if val is None: return "0"
            val = float(val)
            if fmt == "currency": return f"${val:,.2f}"
            elif fmt == "percent": return f"{val:.1f}%"
            else: 
                if val.is_integer(): return f"{int(val):,}"
                return f"{val:,.2f}"
        except:
            return str(val)