import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

class StallionRenderer:
    def __init__(self, df):
        self.df = df
        self.layout_style = dict(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#fafafa'),
            margin=dict(t=30, l=10, r=10, b=10),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
        )

    def render(self, config):
        st.subheader(config.get("dashboard_title", "Analytics Dashboard"))
        if "kpi_cards" in config:
            self._render_kpis(config["kpi_cards"])
        st.markdown("---")
        if "charts" in config:
            self._render_charts(config["charts"])

    def _render_kpis(self, kpis):
        cols = st.columns(len(kpis))
        for idx, kpi in enumerate(kpis):
            with cols[idx]:
                try:
                    value = self._calculate_metric(kpi)
                    label = kpi.get("label", "Metric")
                    st.markdown(f"""
                    <div class="css-1r6slb0">
                        <h4 style='margin:0; color:#94a3b8; font-size:14px;'>{label}</h4>
                        <h2 style='margin:0; color:#fff; font-size:28px;'>{value}</h2>
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"KPI Error: {str(e)}")

    def _calculate_metric(self, kpi):
        col = kpi.get("column")
        op = kpi.get("operation", "count").lower()
        fmt = kpi.get("format", "number")
        if col not in self.df.columns and op != "count":
            return "N/A"
        if op == "sum":
            val = self.df[col].sum()
        elif op == "avg":
            val = self.df[col].mean()
        elif op == "max":
            val = self.df[col].max()
        elif op == "min":
            val = self.df[col].min()
        elif op == "count":
            val = len(self.df)
        else:
             val = 0
        
        if fmt == "currency":
            return f"${val:,.2f}"
        elif fmt == "percent":
            return f"{val:.1f}%"
        else:
            return f"{val:,.0f}" if isinstance(val, (int, float)) else str(val)

    def _render_charts(self, charts):
        for i in range(0, len(charts), 2):
            c1, c2 = st.columns(2)
            with c1:
                self._draw_single_chart(charts[i])
            if i + 1 < len(charts):
                with c2:
                    self._draw_single_chart(charts[i+1])

    def _draw_single_chart(self, chart_config):
        try:
            chart_type = chart_config.get("type", "bar")
            x = chart_config.get("x_column")
            y = chart_config.get("y_column")
            color = chart_config.get("color_column", None)
            title = chart_config.get("title", "Untitled Chart")
            if x and x not in self.df.columns:
                st.warning(f"Column '{x}' not found for chart '{title}'")
                return
            
            if chart_type == "bar":
                fig = px.bar(self.df, x=x, y=y, color=color, title=title, template="plotly_dark")
            elif chart_type == "line":
                fig = px.line(self.df, x=x, y=y, color=color, title=title, template="plotly_dark")
            elif chart_type == "scatter":
                fig = px.scatter(self.df, x=x, y=y, color=color, title=title, template="plotly_dark")
            elif chart_type == "pie":
                fig = px.pie(self.df, names=x, values=y, title=title, template="plotly_dark")
            elif chart_type == "area":
                fig = px.area(self.df, x=x, y=y, color=color, title=title, template="plotly_dark")
            else:
                st.warning(f"Unsupported chart type: {chart_type}")
                return
            fig.update_layout(self.layout_style)
            st.plotly_chart(fig, use_container_width=True)
            if "description" in chart_config:
                st.caption(f"💡 {chart_config['description']}")
        except Exception as e:
            st.error(f"Chart Error: {str(e)}")
