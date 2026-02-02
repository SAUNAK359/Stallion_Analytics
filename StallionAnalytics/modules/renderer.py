import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

class StallionRenderer:
    """
    The Big Data Visualizer.
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

    def render(self, config):
        """Main rendering loop."""
        st.subheader(config.get("dashboard_title", "Analytics Dashboard"))
        
        # 1. Render KPI Row
        if "kpi_cards" in config:
            self._render_sql_kpis(config["kpi_cards"])
            
        st.markdown("---")
        
        # 2. Render Charts Grid
        if "charts" in config:
            self._render_sql_charts(config["charts"])

    def _render_sql_kpis(self, kpis):
        """Calculates and renders metric cards using SQL."""
        cols = st.columns(len(kpis))
        
        for idx, kpi in enumerate(kpis):
            with cols[idx]:
                sql = kpi.get("sql_query")
                label = kpi.get("label", "Metric")
                
                # EXECUTE SQL
                # The query should return a single value (e.g., SELECT SUM(sales)...)
                df, error = self.db.run_query(sql)
                
                if error:
                    value = "Err"
                    st.error(f"SQL Error: {error}")
                elif df.empty:
                    value = "N/A"
                else:
                    # Get the single value from the first cell (row 0, col 0)
                    raw_val = df.iloc[0, 0]
                    value = self._format_metric(raw_val, kpi.get("format"))

                # HTML Card for Glassmorphism
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
                self._draw_chart(charts[i])
            
            # Chart 2 (if exists)
            if i + 1 < len(charts):
                with c2:
                    self._draw_chart(charts[i+1])

    def _draw_chart(self, chart_config):
        """Executes SQL and draws a single Plotly chart."""
        title = chart_config.get("title", "Untitled Chart")
        sql = chart_config.get("sql_query")
        c_type = chart_config.get("type", "bar")
        description = chart_config.get("description")
        
        # 1. EXECUTE SQL
        df, error = self.db.run_query(sql)
        
        if error:
            st.error(f"Query Failed for '{title}': {error}")
            return
            
        if df.empty:
            st.info(f"No data returned for '{title}'")
            return

        # 2. DETERMINE AXES
        # Use AI's suggested columns if present, otherwise auto-detect
        # Default: X is col 0, Y is col 1
        x_col = chart_config.get("x_column", df.columns[0])
        # If there's a second column, use it for Y. If not, re-use X (rare case)
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
                # Fallback
                fig = px.bar(df, x=x_col, y=y_col, title=title, template="plotly_dark")

            # Apply Glass Effect
            fig.update_layout(self.layout_style)
            st.plotly_chart(fig, use_container_width=True)
            
            # Add Description/Insight
            if description:
                st.caption(f"💡 {description}")
                
        except Exception as e:
            st.warning(f"Plotting Error in '{title}': {str(e)}")

    def _format_metric(self, val, fmt):
        """Helper to format raw numbers into strings."""
        try:
            if val is None:
                return "0"
                
            val = float(val)
            
            if fmt == "currency": 
                return f"${val:,.2f}"
            elif fmt == "percent": 
                return f"{val:.1f}%"
            else: 
                # Smart integer formatting (no decimals if whole number)
                if val.is_integer():
                    return f"{int(val):,}"
                return f"{val:,.2f}"
        except:
            return str(val)