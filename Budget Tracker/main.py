import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import (
    add_category,
    add_expense,
    add_income,
    delete_budget,
    delete_category,
    get_all_expenses,
    get_all_income,
    get_budgets,
    get_categories,
    get_setting,
    set_budget,
    set_setting,
    update_expenses_from_df,
    update_income_from_df,
)
from datetime import date, timedelta

st.set_page_config(page_title="Personal Finance Tracker", layout="wide")

st.title("💰 Enhanced Personal Finance Tracker")

FONT_OPTIONS = {
    "Atkinson Hyperlegible": "'Atkinson Hyperlegible', 'Segoe UI', sans-serif",
    "Source Sans Pro": "'Source Sans 3', 'Segoe UI', sans-serif",
    "Merriweather Sans": "'Merriweather Sans', 'Trebuchet MS', sans-serif",
    "Verdana": "Verdana, Geneva, sans-serif",
}

THEME_COLORS = {}


def _ensure_date_col(df, col_name='date'):
    if df.empty:
        return df
    out = df.copy()
    out[col_name] = pd.to_datetime(out[col_name], errors='coerce')
    return out


def _to_csv(df):
    return df.to_csv(index=False).encode('utf-8')


def _range_start_from_label(range_label, ref_date):
    if range_label == "Last 30 Days":
        return ref_date - pd.Timedelta(days=29)
    if range_label == "Last 12 Weeks":
        return ref_date - pd.Timedelta(weeks=12)
    if range_label == "Last 12 Months":
        return ref_date - pd.DateOffset(months=12)
    if range_label == "Year to Date":
        return ref_date.replace(month=1, day=1)
    return None


def _freq_for_granularity(granularity):
    if granularity == "Daily":
        return "D"
    if granularity == "Weekly":
        return "W-MON"
    if granularity == "Monthly":
        return "MS"
    return "YS"


def _month_bounds(ref_date):
    ts = pd.Timestamp(ref_date)
    start = ts.replace(day=1)
    end = (start + pd.offsets.MonthEnd(1)).normalize()
    return start, end


def _previous_month_bounds(ref_date):
    this_start, _ = _month_bounds(ref_date)
    prev_end = this_start - pd.Timedelta(days=1)
    prev_start = prev_end.replace(day=1)
    return prev_start, prev_end


def _format_period_label(series, granularity):
    if granularity == "Daily":
        return series.dt.strftime("%Y-%m-%d")
    if granularity == "Weekly":
        return "Week of " + series.dt.strftime("%Y-%m-%d")
    if granularity == "Monthly":
        return series.dt.strftime("%b %Y")
    return series.dt.strftime("%Y")


def _aggregate_series(df, date_col, value_col, granularity):
    if df.empty or date_col not in df.columns or value_col not in df.columns:
        return pd.DataFrame(columns=["period_start", "period_label", "amount", "cumulative_amount"])

    freq = _freq_for_granularity(granularity)
    temp = df.copy()
    temp[date_col] = pd.to_datetime(temp[date_col], errors='coerce')
    temp[value_col] = pd.to_numeric(temp[value_col], errors='coerce').fillna(0.0)
    temp = temp.dropna(subset=[date_col])
    if temp.empty:
        return pd.DataFrame(columns=["period_start", "period_label", "amount", "cumulative_amount"])

    grouped = (
        temp.groupby(pd.Grouper(key=date_col, freq=freq), as_index=False)[value_col]
        .sum()
        .sort_values(date_col)
        .rename(columns={date_col: "period_start", value_col: "amount"})
    )
    grouped["period_label"] = _format_period_label(grouped["period_start"], granularity)
    grouped["cumulative_amount"] = grouped["amount"].cumsum()
    return grouped


def _aggregate_by_group(df, date_col, value_col, group_col, granularity):
    if df.empty or group_col not in df.columns:
        return pd.DataFrame(columns=["period_start", "period_label", group_col, "amount"])

    freq = _freq_for_granularity(granularity)
    temp = df.copy()
    temp[date_col] = pd.to_datetime(temp[date_col], errors='coerce')
    temp[value_col] = pd.to_numeric(temp[value_col], errors='coerce').fillna(0.0)
    temp[group_col] = temp[group_col].fillna("Uncategorized").astype(str)
    temp = temp.dropna(subset=[date_col])
    if temp.empty:
        return pd.DataFrame(columns=["period_start", "period_label", group_col, "amount"])

    grouped = (
        temp.groupby([pd.Grouper(key=date_col, freq=freq), group_col], as_index=False)[value_col]
        .sum()
        .sort_values([date_col, group_col])
        .rename(columns={date_col: "period_start", value_col: "amount"})
    )
    grouped["period_label"] = _format_period_label(grouped["period_start"], granularity)
    return grouped


def _get_theme_palette(theme_mode):
    if theme_mode == "Dark":
        return {
            "mode": "Dark",
            "app_bg_top": "#0b1220",
            "app_bg_bottom": "#111827",
            "sidebar_bg_top": "#0f172a",
            "sidebar_bg_bottom": "#111827",
            "text": "#e5e7eb",
            "text_muted": "#cbd5e1",
            "heading": "#f8fafc",
            "heading_strong": "#ffffff",
            "input_bg": "#0f172a",
            "input_border": "#475569",
            "metric_bg_start": "rgba(15,23,42,0.95)",
            "metric_bg_end": "rgba(30,41,59,0.95)",
            "metric_border": "rgba(148,163,184,0.35)",
            "metric_shadow": "0 2px 8px rgba(2,6,23,0.45)",
            "button_primary": "#2563eb",
            "button_hover": "#1d4ed8",
            "button_border": "#1e40af",
            "download_bg": "#0f172a",
            "download_text": "#e5e7eb",
            "download_border": "#64748b",
            "popover_bg": "#0f172a",
            "popover_hover": "#1e293b",
            "tab_active": "#60a5fa",
            "dataframe_border": "rgba(148,163,184,0.35)",
            "plot_template": "plotly_dark",
            "plot_grid": "rgba(148,163,184,0.25)",
            "plot_bg": "#0f172a",
            "plot_paper_bg": "#111827",
            "progress_bg": "#334155",
            "progress_status_text": "#e2e8f0",
            "progress_details_text": "#cbd5e1",
            "gdg_text_dark": "#f8fafc",
            "gdg_text_medium": "#cbd5e1",
            "gdg_text_light": "#94a3b8",
            "gdg_bg_cell": "#0f172a",
            "gdg_bg_cell_medium": "#111827",
            "gdg_bg_header": "#1f2937",
            "gdg_bg_header_focus": "#1d4ed8",
            "gdg_bg_search": "#1e3a8a",
            "gdg_border": "#334155",
            "gdg_link": "#60a5fa",
        }

    return {
        "mode": "Light",
        "app_bg_top": "#f8fafc",
        "app_bg_bottom": "#f1f5f9",
        "sidebar_bg_top": "#e2e8f0",
        "sidebar_bg_bottom": "#cbd5e1",
        "text": "#0f172a",
        "text_muted": "#334155",
        "heading": "#0b1220",
        "heading_strong": "#0a1020",
        "input_bg": "#ffffff",
        "input_border": "#64748b",
        "metric_bg_start": "rgba(255,255,255,0.98)",
        "metric_bg_end": "rgba(241,245,249,0.98)",
        "metric_border": "rgba(100,116,139,0.45)",
        "metric_shadow": "0 2px 6px rgba(15,23,42,0.08)",
        "button_primary": "#1d4ed8",
        "button_hover": "#1e40af",
        "button_border": "#1e40af",
        "download_bg": "#ffffff",
        "download_text": "#0f172a",
        "download_border": "#334155",
        "popover_bg": "#ffffff",
        "popover_hover": "#dbeafe",
        "tab_active": "#0b5fff",
        "dataframe_border": "rgba(148,163,184,0.30)",
        "plot_template": "simple_white",
        "plot_grid": "rgba(15,23,42,0.08)",
        "plot_bg": "#ffffff",
        "plot_paper_bg": "#f8fafc",
        "progress_bg": "#e2e8f0",
        "progress_status_text": "#1e293b",
        "progress_details_text": "#334155",
        "gdg_text_dark": "#0f172a",
        "gdg_text_medium": "#334155",
        "gdg_text_light": "#64748b",
        "gdg_bg_cell": "#ffffff",
        "gdg_bg_cell_medium": "#f8fafc",
        "gdg_bg_header": "#f1f5f9",
        "gdg_bg_header_focus": "#dbeafe",
        "gdg_bg_search": "#dbeafe",
        "gdg_border": "#cbd5e1",
        "gdg_link": "#1d4ed8",
    }


def _style_plot(
    fig,
    font_family,
    base_size,
    chart_height,
    legend_orientation="h",
    legend_x=1,
    legend_y=1.02,
    legend_xanchor="right",
    legend_yanchor="bottom",
    margin_right=20,
):
    theme = THEME_COLORS or _get_theme_palette("Light")
    fig.update_layout(
        font={"family": font_family, "size": base_size, "color": theme["text"]},
        template=theme["plot_template"],
        margin={"l": 20, "r": margin_right, "t": 50, "b": 20},
        height=chart_height,
        paper_bgcolor=theme["plot_paper_bg"],
        plot_bgcolor=theme["plot_bg"],
        title={"font": {"color": theme["text"]}},
        legend={
            "orientation": legend_orientation,
            "yanchor": legend_yanchor,
            "y": legend_y,
            "xanchor": legend_xanchor,
            "x": legend_x,
            "font": {"color": theme["text"]},
            "title": {"font": {"color": theme["text"]}},
            "bgcolor": theme["plot_bg"],
            "bordercolor": theme["input_border"],
            "borderwidth": 1,
        },
    )
    fig.update_xaxes(showgrid=False, zeroline=False, tickfont={"color": theme["text"]}, title_font={"color": theme["text"]})
    fig.update_yaxes(showgrid=True, gridcolor=theme["plot_grid"], zeroline=False, tickfont={"color": theme["text"]}, title_font={"color": theme["text"]})
    return fig


def _render_colored_progress(label, ratio, status_text, bar_color, details_text):
    theme = THEME_COLORS or _get_theme_palette("Light")
    bounded_ratio = max(0.0, min(float(ratio), 1.0))
    percent_text = f"{ratio * 100:,.1f}%"
    st.write(label)
    st.markdown(
        f"""
        <div style="margin: 0.25rem 0 0.35rem 0;">
            <div style="height: 0.72rem; width: 100%; background: {theme['progress_bg']}; border-radius: 999px; overflow: hidden; border: 1px solid rgba(100,116,139,0.25);">
                <div style="height: 100%; width: {bounded_ratio * 100:.2f}%; background: {bar_color}; transition: width 220ms ease;"></div>
            </div>
            <div style="margin-top: 0.25rem; font-weight: 700; color: {theme['progress_status_text']};">{percent_text} · {status_text}</div>
            <div style="margin-top: 0.10rem; color: {theme['progress_details_text']};">{details_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _create_pie_chart(df, value_col, name_col, title):
    pie_df = df.groupby(name_col, as_index=False)[value_col].sum()
    if pie_df.empty:
        return None

    pie = go.Pie(
        labels=pie_df[name_col],
        values=pie_df[value_col],
        hole=0.25,
        textinfo='percent+label',
        textposition='inside',
        textfont={"size": 13},
        automargin=True,
        sort=False,
        direction='clockwise',
        marker={"line": {"color": "white", "width": 1}},
    )

    fig = go.Figure(data=[pie])
    fig.update_layout(title=title, showlegend=False)
    return fig


def _apply_ui_typography(font_family, ui_scale, density_mode, theme):
    if density_mode == "Compact":
        block_gap = "0.45rem"
        section_gap = "0.6rem"
        container_top = "0.9rem"
        container_side = "1.1rem"
        card_padding = "0.65rem"
        radius = "10px"
    else:
        block_gap = "0.8rem"
        section_gap = "1rem"
        container_top = "1.4rem"
        container_side = "1.5rem"
        card_padding = "0.9rem"
        radius = "12px"

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Merriweather+Sans:wght@400;700&family=Source+Sans+3:wght@400;700&display=swap');

        :root {{
            --app-font-family: {font_family};
            --app-scale: {ui_scale};
            --app-block-gap: {block_gap};
            --app-section-gap: {section_gap};
            --app-container-top: {container_top};
            --app-container-side: {container_side};
            --app-card-padding: {card_padding};
            --app-radius: {radius};
            --app-bg-top: {theme['app_bg_top']};
            --app-bg-bottom: {theme['app_bg_bottom']};
            --app-sidebar-top: {theme['sidebar_bg_top']};
            --app-sidebar-bottom: {theme['sidebar_bg_bottom']};
            --app-text: {theme['text']};
            --app-text-muted: {theme['text_muted']};
            --app-heading: {theme['heading']};
            --app-heading-strong: {theme['heading_strong']};
            --app-input-bg: {theme['input_bg']};
            --app-input-border: {theme['input_border']};
            --app-metric-bg-start: {theme['metric_bg_start']};
            --app-metric-bg-end: {theme['metric_bg_end']};
            --app-metric-border: {theme['metric_border']};
            --app-metric-shadow: {theme['metric_shadow']};
            --app-primary: {theme['button_primary']};
            --app-primary-hover: {theme['button_hover']};
            --app-primary-border: {theme['button_border']};
            --app-download-bg: {theme['download_bg']};
            --app-download-text: {theme['download_text']};
            --app-download-border: {theme['download_border']};
            --app-popover-bg: {theme['popover_bg']};
            --app-popover-hover: {theme['popover_hover']};
            --app-tab-active: {theme['tab_active']};
            --app-dataframe-border: {theme['dataframe_border']};
            --app-color-scheme: {theme['mode'].lower()};
            --gdg-text-dark: {theme['gdg_text_dark']};
            --gdg-text-medium: {theme['gdg_text_medium']};
            --gdg-text-light: {theme['gdg_text_light']};
            --gdg-bg-cell: {theme['gdg_bg_cell']};
            --gdg-bg-cell-medium: {theme['gdg_bg_cell_medium']};
            --gdg-bg-header: {theme['gdg_bg_header']};
            --gdg-bg-header-has-focus: {theme['gdg_bg_header_focus']};
            --gdg-bg-search-result: {theme['gdg_bg_search']};
            --gdg-border-color: {theme['gdg_border']};
            --gdg-link-color: {theme['gdg_link']};
        }}

        html, body, [class*="css"], .stApp {{
            font-family: var(--app-font-family) !important;
            font-size: calc(16px * var(--app-scale));
            line-height: 1.45;
            color: var(--app-text) !important;
            color-scheme: var(--app-color-scheme);
            forced-color-adjust: none;
        }}

        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(180deg, var(--app-bg-top) 0%, var(--app-bg-bottom) 100%) !important;
        }}

        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"],
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] li,
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] span,
        [data-testid="stAppViewContainer"] .stAlert,
        [data-testid="stAppViewContainer"] .stAlert p,
        [data-testid="stAppViewContainer"] .stInfo,
        [data-testid="stAppViewContainer"] .stWarning,
        [data-testid="stAppViewContainer"] .stSuccess,
        [data-testid="stAppViewContainer"] .stError {{
            color: var(--app-text) !important;
        }}

        [data-testid="stAppViewContainer"] [data-baseweb="input"] > div,
        [data-testid="stAppViewContainer"] input,
        [data-testid="stAppViewContainer"] textarea {{
            background: var(--app-input-bg) !important;
            color: var(--app-text) !important;
            border: 1px solid var(--app-input-border) !important;
        }}

        [data-testid="stAppViewContainer"] input::placeholder,
        [data-testid="stAppViewContainer"] textarea::placeholder {{
            color: var(--app-text-muted) !important;
            opacity: 1 !important;
        }}

        [data-testid="stPlotlyChart"] > div,
        [data-testid="stPlotlyChart"] .js-plotly-plot,
        [data-testid="stPlotlyChart"] .plotly,
        [data-testid="stPlotlyChart"] .svg-container {{
            background: var(--app-bg-bottom) !important;
            border-radius: var(--app-radius);
        }}

        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, var(--app-sidebar-top) 0%, var(--app-sidebar-bottom) 100%) !important;
            border-right: 1px solid var(--app-input-border);
        }}

        [data-testid="stSidebar"] * {{
            color: var(--app-text) !important;
            opacity: 1 !important;
            text-shadow: none !important;
        }}

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] .stRadio,
        [data-testid="stSidebar"] .stSelectbox,
        [data-testid="stSidebar"] .stTextInput,
        [data-testid="stSidebar"] .stNumberInput,
        [data-testid="stSidebar"] .stDateInput {{
            color: var(--app-text) !important;
            font-weight: 700 !important;
        }}

        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-baseweb="input"] > div,
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea {{
            background: var(--app-input-bg) !important;
            color: var(--app-text) !important;
            border: 1px solid var(--app-input-border) !important;
        }}

        [data-testid="stSidebar"] [role="radiogroup"] label {{
            color: var(--app-text) !important;
            font-weight: 700 !important;
        }}

        [data-testid="stAppViewContainer"] > .main .block-container {{
            padding-top: var(--app-container-top);
            padding-left: var(--app-container-side);
            padding-right: var(--app-container-side);
        }}

        [data-testid="stVerticalBlock"] {{
            gap: var(--app-block-gap);
        }}

        .stDivider {{
            margin-top: var(--app-section-gap);
            margin-bottom: var(--app-section-gap);
        }}

        h1, h2, h3 {{
            letter-spacing: 0.2px;
            color: var(--app-heading);
        }}

        h1 {{
            font-weight: 800;
            color: var(--app-heading-strong);
        }}

        h2 {{
            margin-top: calc(var(--app-section-gap) * 0.2);
            margin-bottom: calc(var(--app-section-gap) * 0.5);
        }}

        h3 {{
            margin-top: calc(var(--app-section-gap) * 0.15);
            margin-bottom: calc(var(--app-section-gap) * 0.35);
        }}

        .stMetricValue {{
            font-size: calc(1.5rem * var(--app-scale));
            color: var(--app-heading) !important;
            font-weight: 800 !important;
        }}

        [data-testid="stMetricValue"] {{
            color: var(--app-heading) !important;
            font-weight: 800 !important;
            text-shadow: none !important;
            opacity: 1 !important;
        }}

        [data-testid="stMetric"] {{
            background: linear-gradient(180deg, var(--app-metric-bg-start) 0%, var(--app-metric-bg-end) 100%);
            border: 1px solid var(--app-metric-border);
            border-radius: var(--app-radius);
            padding: var(--app-card-padding);
            box-shadow: var(--app-metric-shadow);
        }}

        [data-testid="stMetric"] * {{
            color: var(--app-text) !important;
            opacity: 1 !important;
        }}

        [data-testid="stMetricLabel"] {{
            font-weight: 600;
            color: var(--app-text-muted) !important;
        }}

        [data-testid="stMetricDelta"] {{
            color: var(--app-text-muted) !important;
            font-weight: 700;
        }}

        [data-testid="stDataFrameResizable"] {{
            border: 1px solid var(--app-dataframe-border);
            border-radius: var(--app-radius);
            overflow: hidden;
        }}

        .stAlert {{
            border-radius: var(--app-radius);
        }}

        .stButton > button {{
            border-radius: 10px;
            border: 1px solid var(--app-primary-border);
            font-weight: 600;
            padding-top: 0.4rem;
            padding-bottom: 0.4rem;
            background: var(--app-primary) !important;
            color: #ffffff !important;
            opacity: 1 !important;
        }}

        .stForm button,
        [data-testid="stForm"] button,
        [data-testid="stFormSubmitButton"] button,
        button[kind="primary"],
        button[kind="secondary"] {{
            background: var(--app-primary) !important;
            color: #ffffff !important;
            border: 1px solid var(--app-primary-border) !important;
            font-weight: 700 !important;
            text-shadow: none !important;
            opacity: 1 !important;
        }}

        .stForm button:hover,
        [data-testid="stForm"] button:hover,
        [data-testid="stFormSubmitButton"] button:hover,
        button[kind="primary"]:hover,
        button[kind="secondary"]:hover {{
            background: var(--app-primary-hover) !important;
            color: #ffffff !important;
            border-color: var(--app-primary-border) !important;
        }}

        .stForm button span,
        [data-testid="stForm"] button span,
        [data-testid="stFormSubmitButton"] button span {{
            color: #ffffff !important;
            opacity: 1 !important;
        }}

        .stButton > button:hover {{
            background: var(--app-primary-hover) !important;
            border-color: var(--app-primary-border) !important;
            color: #ffffff !important;
        }}

        .stDownloadButton > button {{
            border-radius: 10px;
            font-weight: 600;
            border: 1px solid var(--app-download-border);
            background: var(--app-download-bg) !important;
            color: var(--app-download-text) !important;
            opacity: 1 !important;
        }}

        .stTabs [data-baseweb="tab"] {{
            font-weight: 600;
            font-size: calc(1.14rem * var(--app-scale));
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
            min-height: 2.6rem;
        }}

        .stTabs [aria-selected="true"] {{
            color: var(--app-tab-active);
            border-bottom-color: var(--app-tab-active) !important;
        }}

        .stTabs [data-baseweb="tab"] p {{
            color: var(--app-text) !important;
            font-size: calc(1.08rem * var(--app-scale)) !important;
            font-weight: 700 !important;
            letter-spacing: 0.2px;
        }}

        label, .stSelectbox label, .stSlider label, .stNumberInput label {{
            color: var(--app-text) !important;
            font-weight: 700 !important;
            opacity: 1 !important;
        }}

        [data-baseweb="select"] > div {{
            background: var(--app-input-bg) !important;
            border: 1px solid var(--app-input-border) !important;
            min-height: 2.5rem;
        }}

        [data-baseweb="select"] * {{
            color: var(--app-text) !important;
            opacity: 1 !important;
        }}

        [data-baseweb="popover"],
        [data-baseweb="menu"] {{
            background: var(--app-popover-bg) !important;
            color: var(--app-text) !important;
            border: 1px solid var(--app-input-border) !important;
        }}

        [data-baseweb="popover"] [role="listbox"],
        [data-baseweb="menu"] ul,
        [data-baseweb="popover"] [role="option"],
        [data-baseweb="menu"] [role="option"],
        [data-baseweb="popover"] [role="option"] *,
        [data-baseweb="menu"] [role="option"] * {{
            background: var(--app-popover-bg) !important;
            color: var(--app-text) !important;
            opacity: 1 !important;
        }}

        [data-baseweb="popover"] [role="option"]:hover,
        [data-baseweb="menu"] [role="option"]:hover,
        [data-baseweb="popover"] [role="option"][aria-selected="true"],
        [data-baseweb="menu"] [role="option"][aria-selected="true"] {{
            background: var(--app-popover-hover) !important;
            color: var(--app-text) !important;
        }}

        /* Data editor (Glide) theme overrides for readable cell and dropdown/menu text. */
        [data-testid="stDataFrame"] .stDataFrameGlideDataEditor,
        [data-testid="stDataEditor"] .stDataFrameGlideDataEditor,
        [data-testid="stDataFrame"] .dvn-scroller,
        [data-testid="stDataEditor"] .dvn-scroller {{
            --gdg-text-dark: var(--gdg-text-dark) !important;
            --gdg-text-medium: var(--gdg-text-medium) !important;
            --gdg-text-light: var(--gdg-text-light) !important;
            --gdg-bg-cell: var(--gdg-bg-cell) !important;
            --gdg-bg-cell-medium: var(--gdg-bg-cell-medium) !important;
            --gdg-bg-header: var(--gdg-bg-header) !important;
            --gdg-bg-header-has-focus: var(--gdg-bg-header-has-focus) !important;
            --gdg-bg-search-result: var(--gdg-bg-search-result) !important;
            --gdg-border-color: var(--gdg-border-color) !important;
            --gdg-link-color: var(--gdg-link-color) !important;
            color: var(--app-text) !important;
        }}

        [data-testid="stSlider"] * {{
            color: var(--app-text) !important;
            opacity: 1 !important;
        }}

        [data-testid="stSidebar"] [data-testid="stSlider"] * {{
            color: var(--app-text) !important;
            opacity: 1 !important;
            font-weight: 700 !important;
        }}

        [data-testid="stSlider"] [role="slider"] {{
            background: var(--app-primary) !important;
            border: 2px solid var(--app-primary-border) !important;
        }}

        [data-testid="stSliderTickBarMin"],
        [data-testid="stSliderTickBarMax"],
        [data-testid="stSliderTickBar"] {{
            color: var(--app-text-muted) !important;
            opacity: 1 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _expense_signatures(df):
    if df.empty:
        return set()
    temp = df.copy()
    temp['date'] = pd.to_datetime(temp['date'], errors='coerce').dt.date
    temp['description'] = temp['description'].fillna('').astype(str).str.strip().str.lower()
    temp['amount'] = pd.to_numeric(temp['amount'], errors='coerce').fillna(0.0)
    return set(zip(temp['date'], temp['amount'].round(2), temp['description']))


currency = get_setting('currency', '$')
selected_font_name = get_setting('font_family_name', 'Atkinson Hyperlegible')
selected_font_css = FONT_OPTIONS.get(selected_font_name, FONT_OPTIONS['Atkinson Hyperlegible'])
selected_theme_mode = get_setting('theme_mode', 'Light')
if selected_theme_mode not in ["Light", "Dark"]:
    selected_theme_mode = "Light"
ui_scale = float(get_setting('ui_scale', '1.00'))
layout_density = get_setting('layout_density', 'Comfortable')
if layout_density not in ["Compact", "Comfortable"]:
    layout_density = "Comfortable"
chart_height_setting = int(get_setting('chart_height', '460'))
chart_height_setting = max(360, min(chart_height_setting, 780))

THEME_COLORS = _get_theme_palette(selected_theme_mode)

_apply_ui_typography(selected_font_css, ui_scale, layout_density, THEME_COLORS)

plot_font_size = max(12, int(13 * ui_scale))

# Sidebar - Shared Inputs
st.sidebar.header("Quick Add")
categories = get_categories()

add_type = st.sidebar.radio("Entry Type", ["Expense", "Income"])

if add_type == "Expense":
    with st.sidebar.form("expense_form", clear_on_submit=True):
        exp_date = st.date_input("Date", value=date.today())
        exp_cat = st.selectbox("Category", categories)
        exp_amt = st.number_input("Amount", min_value=0.0, format="%.2f")
        exp_store = st.text_input("Store (Optional)")
        exp_place = st.text_input("Place (Optional)")
        exp_desc = st.text_input("Description")
        submit = st.form_submit_button("Add Expense")
        if submit and exp_amt > 0:
            add_expense(exp_date, exp_cat, exp_amt, exp_desc, exp_store, exp_place)
            st.sidebar.success("Expense added!")
            st.rerun()

else:
    with st.sidebar.form("income_form", clear_on_submit=True):
        inc_date = st.date_input("Date", value=date.today())
        inc_source = st.text_input("Source (e.g., Salary, Gift)")
        inc_amt = st.number_input("Amount", min_value=0.0, format="%.2f")
        submit = st.form_submit_button("Add Income")
        if submit and inc_amt > 0:
            add_income(inc_date, inc_source, inc_amt)
            st.sidebar.success("Income added!")
            st.rerun()

# Main Area Tabs
tab_overview, tab_expenses, tab_income, tab_budgets, tab_settings = st.tabs([
    "📊 Budget Overview", "💸 Expenses", "🏦 Income", "🎯 Budget Goals", "⚙️ Settings"
])

# --- Tab: Overview ---
with tab_overview:
    st.header("Financial Overview")
    overview_range = st.selectbox(
        "Time Range",
        ["Last 30 Days", "Last 12 Weeks", "Last 12 Months", "Year to Date", "All Time"],
        index=0,
        key="overview_time_range",
    )
    overview_granularity = st.selectbox(
        "Chart Granularity",
        ["Daily", "Weekly", "Monthly", "Yearly"],
        index=2,
        key="overview_granularity",
    )
    
    # Data loading
    exp_data = get_all_expenses()
    inc_data = get_all_income()
    
    df_exp = pd.DataFrame([
        {"date": e.date, "amount": e.amount, "category": e.category, "description": e.description}
        for e in exp_data
    ])
    df_inc = pd.DataFrame([
        {"date": i.date, "amount": i.amount, "source": i.source}
        for i in inc_data
    ])
    
    if not df_exp.empty or not df_inc.empty:
        if not df_exp.empty:
            df_exp = _ensure_date_col(df_exp)
        if not df_inc.empty:
            df_inc = _ensure_date_col(df_inc)

        today = pd.Timestamp.now().normalize()
        start_date = _range_start_from_label(overview_range, today)

        monthly_calendar_mode = overview_granularity == "Monthly"
        if monthly_calendar_mode:
            month_start, month_end = _month_bounds(today)
            current_exp = (
                df_exp[(df_exp['date'] >= month_start) & (df_exp['date'] <= month_end)]
                if not df_exp.empty else pd.DataFrame()
            )
            current_inc = (
                df_inc[(df_inc['date'] >= month_start) & (df_inc['date'] <= month_end)]
                if not df_inc.empty else pd.DataFrame()
            )
            overview_period_text = f"Calendar Month: {month_start.strftime('%b %Y')}"
        else:
            current_exp = (
                df_exp[df_exp['date'] >= start_date] if (start_date is not None and not df_exp.empty) else df_exp.copy()
            ) if not df_exp.empty else pd.DataFrame()
            current_inc = (
                df_inc[df_inc['date'] >= start_date] if (start_date is not None and not df_inc.empty) else df_inc.copy()
            ) if not df_inc.empty else pd.DataFrame()
            overview_period_text = overview_range
        
        total_exp = current_exp['amount'].sum() if not current_exp.empty else 0
        total_inc = current_inc['amount'].sum() if not current_inc.empty else 0
        balance = total_inc - total_exp
        
        savings_rate = ((balance / total_inc) * 100) if total_inc > 0 else 0.0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Income", f"{currency}{total_inc:,.2f}")
        m2.metric("Total Expenses", f"{currency}{total_exp:,.2f}", delta=-total_exp, delta_color="inverse")
        m3.metric("Net Balance", f"{currency}{balance:,.2f}", delta=balance)
        m4.metric("Savings Rate", f"{savings_rate:,.1f}%")
        
        st.divider()

        period_label = f"{overview_granularity} ({overview_period_text})"
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if not current_exp.empty:
                st.subheader("Expense Distribution")
                fig = _create_pie_chart(current_exp, 'amount', 'category', f'Expense Distribution - {overview_period_text}')
                if fig is not None:
                    fig = _style_plot(fig, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig, width="stretch")
        with col_c2:
            st.subheader("Income vs Expenses")
            exp_series = _aggregate_series(current_exp, 'date', 'amount', overview_granularity)
            exp_series['kind'] = f"Expenses ({overview_granularity})"
            inc_series = _aggregate_series(current_inc, 'date', 'amount', overview_granularity)
            inc_series['kind'] = f"Income ({overview_granularity})"
            compare_df = pd.concat([
                exp_series[['period_start', 'amount', 'kind']],
                inc_series[['period_start', 'amount', 'kind']],
            ], ignore_index=True)
            if not compare_df.empty:
                fig = px.bar(compare_df, x='period_start', y='amount', color='kind', barmode='group')
                fig.update_layout(yaxis_title=f"Amount ({currency})")
                fig = _style_plot(fig, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig, width="stretch")

        st.subheader(f"Trendlines - {period_label}")
        t1, t2 = st.columns(2)
        with t1:
            if not current_exp.empty:
                exp_trend = _aggregate_series(current_exp, 'date', 'amount', overview_granularity)
                exp_trend['rolling_avg'] = exp_trend['amount'].rolling(3, min_periods=1).mean()
                fig_exp_trend = go.Figure()
                fig_exp_trend.add_trace(go.Scatter(
                    x=exp_trend['period_start'],
                    y=exp_trend['amount'],
                    mode='lines+markers',
                    name=f'{overview_granularity} Expenses',
                ))
                fig_exp_trend.add_trace(go.Scatter(
                    x=exp_trend['period_start'],
                    y=exp_trend['rolling_avg'],
                    mode='lines',
                    name=f'{overview_granularity} Avg Trend',
                    line={"width": 3},
                ))
                fig_exp_trend.update_layout(title=f'Expense Trendline - {period_label}', yaxis_title=f'Amount ({currency})')
                fig_exp_trend = _style_plot(fig_exp_trend, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig_exp_trend, width="stretch")
            else:
                st.info("Add expense history to see trendlines.")
        with t2:
            if not current_inc.empty:
                inc_trend = _aggregate_series(current_inc, 'date', 'amount', overview_granularity)
                inc_trend['rolling_avg'] = inc_trend['amount'].rolling(3, min_periods=1).mean()
                fig_inc_trend = go.Figure()
                fig_inc_trend.add_trace(go.Scatter(
                    x=inc_trend['period_start'],
                    y=inc_trend['amount'],
                    mode='lines+markers',
                    name=f'{overview_granularity} Income',
                ))
                fig_inc_trend.add_trace(go.Scatter(
                    x=inc_trend['period_start'],
                    y=inc_trend['rolling_avg'],
                    mode='lines',
                    name=f'{overview_granularity} Avg Trend',
                    line={"width": 3},
                ))
                fig_inc_trend.update_layout(title=f'Income Trendline - {period_label}', yaxis_title=f'Amount ({currency})')
                fig_inc_trend = _style_plot(fig_inc_trend, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig_inc_trend, width="stretch")
            else:
                st.info("Add income history to see trendlines.")

        st.subheader("Categorized Totals")
        ctot1, ctot2 = st.columns(2)
        with ctot1:
            exp_cat_totals = (
                current_exp.groupby('category', as_index=False)['amount'].sum().sort_values('amount', ascending=False)
                if not current_exp.empty else pd.DataFrame(columns=['category', 'amount'])
            )
            if not exp_cat_totals.empty:
                fig_exp_cat = px.bar(
                    exp_cat_totals,
                    x='category',
                    y='amount',
                    color='category',
                    title=f'Expense by Category - {overview_period_text}',
                )
                fig_exp_cat.update_layout(showlegend=False, yaxis_title=f"Amount ({currency})")
                fig_exp_cat = _style_plot(fig_exp_cat, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig_exp_cat, width="stretch")
            else:
                st.info("No categorized expense data for the selected range.")
        with ctot2:
            inc_src_totals = (
                current_inc.groupby('source', as_index=False)['amount'].sum().sort_values('amount', ascending=False)
                if not current_inc.empty else pd.DataFrame(columns=['source', 'amount'])
            )
            if not inc_src_totals.empty:
                fig_inc_src = px.bar(
                    inc_src_totals,
                    x='source',
                    y='amount',
                    color='source',
                    title=f'Income by Source - {overview_period_text}',
                )
                fig_inc_src.update_layout(showlegend=False, yaxis_title=f"Amount ({currency})")
                fig_inc_src = _style_plot(fig_inc_src, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig_inc_src, width="stretch")
            else:
                st.info("No categorized income data for the selected range.")

        st.subheader("Past-Month Expense Insights")
        months_back = st.slider(
            "Months to Analyze",
            min_value=3,
            max_value=36,
            value=12,
            step=1,
            key="overview_months_back",
        )
        if not df_exp.empty:
            monthly_start = (today - pd.DateOffset(months=months_back - 1)).replace(day=1)
            monthly_exp = df_exp[df_exp['date'] >= monthly_start].copy()
            monthly_exp['month'] = monthly_exp['date'].dt.to_period('M').dt.to_timestamp()
            available_cats = sorted(monthly_exp['category'].dropna().astype(str).unique().tolist())
            selected_cats = st.multiselect(
                "Categories to Include",
                options=available_cats,
                default=available_cats,
                key="overview_monthly_categories",
            )
            if selected_cats:
                monthly_exp = monthly_exp[monthly_exp['category'].isin(selected_cats)]

            if not monthly_exp.empty:
                past_month_chart_height = min(920, max(560, chart_height_setting + 120))
                monthly_cat = (
                    monthly_exp.groupby(['month', 'category'], as_index=False)['amount']
                    .sum()
                    .sort_values(['month', 'category'])
                )
                monthly_total = (
                    monthly_exp.groupby('month', as_index=False)['amount']
                    .sum()
                    .sort_values('month')
                )
                monthly_total['cumulative_amount'] = monthly_total['amount'].cumsum()

                pm1, pm2 = st.columns(2)
                with pm1:
                    fig_monthly_cat = px.bar(
                        monthly_cat,
                        x='month',
                        y='amount',
                        color='category',
                        title=f'Monthly Categorized Expenses - Last {months_back} Months',
                    )
                    fig_monthly_cat.update_layout(yaxis_title=f"Amount ({currency})", legend_title_text="Category")
                    fig_monthly_cat = _style_plot(
                        fig_monthly_cat,
                        selected_font_css,
                        plot_font_size,
                        past_month_chart_height,
                        legend_orientation="v",
                        legend_x=1.02,
                        legend_y=1,
                        legend_xanchor="left",
                        legend_yanchor="top",
                        margin_right=180,
                    )
                    st.plotly_chart(fig_monthly_cat, width="stretch")

                with pm2:
                    fig_monthly_cum = go.Figure()
                    fig_monthly_cum.add_trace(go.Bar(
                        x=monthly_total['month'],
                        y=monthly_total['amount'],
                        name='Monthly Total',
                    ))
                    fig_monthly_cum.add_trace(go.Scatter(
                        x=monthly_total['month'],
                        y=monthly_total['cumulative_amount'],
                        mode='lines+markers',
                        name='Cumulative Total',
                        line={"width": 3},
                    ))
                    fig_monthly_cum.update_layout(
                        title=f'Monthly and Cumulative Expense - Last {months_back} Months',
                        yaxis_title=f'Amount ({currency})',
                    )
                    fig_monthly_cum = _style_plot(fig_monthly_cum, selected_font_css, plot_font_size, past_month_chart_height)
                    st.plotly_chart(fig_monthly_cum, width="stretch")
            else:
                st.info("No monthly expense data found for the selected categories/time range.")
        else:
            st.info("Add expenses to analyze monthly categorized and cumulative totals.")

        if not current_exp.empty:
            top_spend = current_exp.groupby('category', as_index=False)['amount'].sum().sort_values('amount', ascending=False).head(1)
            if not top_spend.empty:
                st.info(
                    f"Top spending category: {top_spend.iloc[0]['category']} "
                    f"({currency}{top_spend.iloc[0]['amount']:,.2f})"
                )
    else:
        st.info("No data available for the selected period.")

# --- Tab: Expenses ---
with tab_expenses:
    st.header("Expenses")
    expenses = get_all_expenses()
    df = pd.DataFrame([
        {"id": e.id, "date": e.date, "category": e.category, "amount": e.amount,
         "store": e.store, "place": e.place, "description": e.description} for e in expenses
    ])

    base_columns = ["id", "date", "category", "amount", "store", "place", "description"]
    if df.empty:
        df = pd.DataFrame(columns=base_columns)

    sort_option_exp = st.selectbox(
        "Expense Date Sort",
        ["Newest first", "Oldest first"],
        index=0,
        key="expense_sort_option",
    )
    sort_ascending_exp = sort_option_exp == "Oldest first"

    df_for_editor = df.copy()
    if not df_for_editor.empty:
        df_for_editor["date"] = pd.to_datetime(df_for_editor["date"], errors='coerce')
        df_for_editor = df_for_editor.sort_values(by=["date", "id"], ascending=[sort_ascending_exp, sort_ascending_exp])

    chart_container_exp = st.container()
    editor_container_exp = st.container()

    income_for_compare = get_all_income()
    df_inc_for_compare = pd.DataFrame([
        {"date": i.date, "amount": i.amount, "source": i.source}
        for i in income_for_compare
    ])
    if not df_inc_for_compare.empty:
        df_inc_for_compare = _ensure_date_col(df_inc_for_compare)

    with editor_container_exp:
        st.subheader("Manage Expenses")
        edited_df = st.data_editor(
            df_for_editor,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "category": st.column_config.SelectboxColumn("Category", options=categories, required=True),
                "amount": st.column_config.NumberColumn("Amount", format=f"{currency}%.2f"),
                "date": st.column_config.DateColumn("Date"),
            },
            hide_index=True,
            num_rows="dynamic",
            key="exp_editor",
        )

        cleaned_edited = edited_df.copy()
        if 'date' in cleaned_edited.columns:
            cleaned_edited['date'] = pd.to_datetime(cleaned_edited['date'], errors='coerce').dt.date

        delete_count = 0
        if 'id' in df.columns and 'id' in cleaned_edited.columns:
            original_ids = set(df['id'].dropna().astype(int).tolist()) if not df.empty else set()
            edited_ids = set(cleaned_edited['id'].dropna().astype(int).tolist()) if not cleaned_edited.empty else set()
            delete_count = len(original_ids - edited_ids)

        if st.button("Save Expenses", key="save_expenses_button"):
            if delete_count > 0:
                st.session_state['pending_expense_save'] = True
                st.session_state['pending_expense_delete_count'] = delete_count
            else:
                update_expenses_from_df(cleaned_edited)
                st.success("Expenses saved!")
                st.rerun()

        if st.session_state.get('pending_expense_save', False):
            pending_delete_count = st.session_state.get('pending_expense_delete_count', 0)
            st.warning(f"This save will permanently delete {pending_delete_count} expense row(s) from the database.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Confirm Save", key="confirm_expense_save"):
                    update_expenses_from_df(cleaned_edited)
                    st.session_state['pending_expense_save'] = False
                    st.session_state['pending_expense_delete_count'] = 0
                    st.success("Expenses saved!")
                    st.rerun()
            with c2:
                if st.button("Cancel", key="cancel_expense_save"):
                    st.session_state['pending_expense_save'] = False
                    st.session_state['pending_expense_delete_count'] = 0

        st.download_button(
            "Download Expenses CSV",
            data=_to_csv(cleaned_edited),
            file_name="expenses.csv",
            mime="text/csv",
        )

        st.subheader("Bulk Import Expenses")
        uploaded = st.file_uploader("Upload expenses CSV", type=['csv'], key='expense_csv_upload')
        if uploaded is not None:
            try:
                import_df = pd.read_csv(uploaded)
                required_cols = {'date', 'category', 'amount', 'description'}
                if not required_cols.issubset(set(import_df.columns)):
                    missing = sorted(required_cols - set(import_df.columns))
                    st.error(f"Missing required columns: {', '.join(missing)}")
                else:
                    existing_signatures = _expense_signatures(df)
                    added_count = 0
                    skipped_count = 0
                    for _, row in import_df.iterrows():
                        row_date = pd.to_datetime(row.get('date'), errors='coerce')
                        if pd.isna(row_date):
                            skipped_count += 1
                            continue
                        row_amount = pd.to_numeric(row.get('amount'), errors='coerce')
                        if pd.isna(row_amount):
                            skipped_count += 1
                            continue
                        row_desc = str(row.get('description', '')).strip()
                        signature = (row_date.date(), round(float(row_amount), 2), row_desc.lower())
                        if signature in existing_signatures:
                            skipped_count += 1
                            continue

                        add_expense(
                            row_date.date(),
                            str(row.get('category')).strip(),
                            float(row_amount),
                            row_desc,
                            str(row.get('store')).strip() if pd.notna(row.get('store')) else None,
                            str(row.get('place')).strip() if pd.notna(row.get('place')) else None,
                        )
                        existing_signatures.add(signature)
                        added_count += 1

                    st.success(f"Import complete. Added: {added_count}, Skipped duplicates/invalid: {skipped_count}")
                    if added_count > 0:
                        st.rerun()
            except Exception as exc:
                st.error(f"CSV import failed: {exc}")

    with chart_container_exp:
        st.subheader("Real-Time Expense Charts")
        chart_df = cleaned_edited.copy()
        if not chart_df.empty:
            chart_df['amount'] = pd.to_numeric(chart_df['amount'], errors='coerce').fillna(0.0)
            chart_df['date'] = pd.to_datetime(chart_df['date'], errors='coerce')

        today_date = date.today()
        default_start = today_date - timedelta(days=90)
        f1, f2, f3 = st.columns([1, 1, 1.2])
        with f1:
            exp_start_date = st.date_input("From", value=default_start, key="exp_chart_from")
        with f2:
            exp_end_date = st.date_input("To", value=today_date, key="exp_chart_to")
        with f3:
            expense_granularity = st.selectbox(
                "Chart Grouping",
                ["Daily", "Weekly", "Monthly", "Yearly"],
                index=2,
                key="expense_chart_granularity",
            )

        monthly_mode_exp = expense_granularity == "Monthly"
        if monthly_mode_exp:
            exp_month_start, exp_month_end = _month_bounds(exp_end_date)
            exp_start_date = exp_month_start.date()
            exp_end_date = exp_month_end.date()
            st.caption(f"Monthly mode uses calendar month: {exp_month_start.strftime('%b %Y')}")

        if exp_start_date > exp_end_date:
            st.warning("'From' date is after 'To' date. Please adjust the range.")
            filtered_chart_df = pd.DataFrame(columns=chart_df.columns)
        else:
            filtered_chart_df = chart_df.copy()
            if not filtered_chart_df.empty:
                filtered_chart_df = filtered_chart_df.dropna(subset=['date'])
                filtered_chart_df = filtered_chart_df[
                    (filtered_chart_df['date'] >= pd.Timestamp(exp_start_date))
                    & (filtered_chart_df['date'] <= pd.Timestamp(exp_end_date))
                ]

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            if not filtered_chart_df.empty:
                pie_source = filtered_chart_df.dropna(subset=['category'])
                if not pie_source.empty:
                    pie = _create_pie_chart(
                        pie_source,
                        'amount',
                        'category',
                        f'Expense Share ({expense_granularity}) - {exp_start_date} to {exp_end_date}',
                    )
                    if pie is not None:
                        pie = _style_plot(pie, selected_font_css, plot_font_size, chart_height_setting)
                        pie.update_layout(uniformtext_minsize=11, uniformtext_mode='show')
                        st.plotly_chart(pie, width="stretch")
                else:
                    st.info("Add categories to see chart distribution.")
            else:
                st.info("No expenses found in the selected range.")

        with chart_col2:
            if not filtered_chart_df.empty:
                grouped_source = _aggregate_series(filtered_chart_df, 'date', 'amount', expense_granularity)
                if not grouped_source.empty:
                    bar = px.bar(
                        grouped_source,
                        x='period_start',
                        y='amount',
                        title=(
                            f"Total Expenses by {expense_granularity} "
                            f"({exp_start_date} to {exp_end_date})"
                        ),
                    )
                    bar.update_layout(
                        yaxis_title=f"Amount ({currency})",
                        legend_title_text=f"{expense_granularity} Totals",
                    )
                    bar = _style_plot(bar, selected_font_css, plot_font_size, chart_height_setting)
                    st.plotly_chart(bar, width="stretch")
                else:
                    st.info("Add valid dates to see timeline chart.")
            else:
                st.info("No timeline data in selected range.")

        if not filtered_chart_df.empty:
            cat_totals_exp = (
                filtered_chart_df.groupby('category', as_index=False)['amount']
                .sum()
                .sort_values('amount', ascending=False)
            )
            if not cat_totals_exp.empty:
                fig_cat_totals_exp = px.bar(
                    cat_totals_exp,
                    x='category',
                    y='amount',
                    color='category',
                    title=(
                        f"Categorized Total Expenses ({exp_start_date} to {exp_end_date})"
                    ),
                )
                fig_cat_totals_exp.update_layout(showlegend=False, yaxis_title=f"Amount ({currency})")
                fig_cat_totals_exp = _style_plot(fig_cat_totals_exp, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig_cat_totals_exp, width="stretch")
            else:
                st.info("No categorized totals available for the selected range.")

        comparison_mode_exp = st.toggle("Comparison Mode (vs Previous Period)", value=False, key="expenses_compare_mode")
        if comparison_mode_exp:
            if exp_start_date > exp_end_date:
                st.info("Comparison Mode requires a valid date range.")
            else:
                current_start_ts = pd.Timestamp(exp_start_date)
                current_end_ts = pd.Timestamp(exp_end_date)
                if monthly_mode_exp:
                    prev_start, prev_end = _previous_month_bounds(current_end_ts)
                else:
                    window_days = max(1, (current_end_ts - current_start_ts).days + 1)
                    prev_end = current_start_ts - pd.Timedelta(days=1)
                    prev_start = prev_end - pd.Timedelta(days=window_days - 1)

                current_exp_total = float(filtered_chart_df['amount'].sum()) if not filtered_chart_df.empty else 0.0
                prev_exp_df = chart_df[
                    (chart_df['date'] >= prev_start) &
                    (chart_df['date'] <= prev_end)
                ] if not chart_df.empty else pd.DataFrame()
                prev_exp_total = float(prev_exp_df['amount'].sum()) if not prev_exp_df.empty else 0.0

                current_inc_df = df_inc_for_compare[
                    (df_inc_for_compare['date'] >= current_start_ts) &
                    (df_inc_for_compare['date'] <= current_end_ts)
                ] if not df_inc_for_compare.empty else pd.DataFrame()
                prev_inc_df = df_inc_for_compare[
                    (df_inc_for_compare['date'] >= prev_start) &
                    (df_inc_for_compare['date'] <= prev_end)
                ] if not df_inc_for_compare.empty else pd.DataFrame()

                current_inc_total = float(current_inc_df['amount'].sum()) if not current_inc_df.empty else 0.0
                prev_inc_total = float(prev_inc_df['amount'].sum()) if not prev_inc_df.empty else 0.0
                current_balance = current_inc_total - current_exp_total
                prev_balance = prev_inc_total - prev_exp_total

                st.subheader("Comparison vs Previous Period")
                pc1, pc2, pc3 = st.columns(3)
                pc1.metric("Income Change", f"{currency}{current_inc_total:,.2f}", delta=f"{(current_inc_total - prev_inc_total):,.2f}")
                pc2.metric("Expense Change", f"{currency}{current_exp_total:,.2f}", delta=f"{(current_exp_total - prev_exp_total):,.2f}", delta_color="inverse")
                pc3.metric("Balance Change", f"{currency}{current_balance:,.2f}", delta=f"{(current_balance - prev_balance):,.2f}")

                compare_rows = pd.DataFrame([
                    {"metric": "Income", "Current": current_inc_total, "Previous": prev_inc_total},
                    {"metric": "Expenses", "Current": current_exp_total, "Previous": prev_exp_total},
                    {"metric": "Net Balance", "Current": current_balance, "Previous": prev_balance},
                ])
                compare_long = compare_rows.melt(id_vars="metric", var_name="period", value_name="amount")
                fig_cmp = px.bar(compare_long, x='metric', y='amount', color='period', barmode='group')
                fig_cmp.update_layout(
                    title=(
                        f"Current vs Previous ({'Calendar Month' if monthly_mode_exp else 'Expenses Date Range'})\n"
                        f"Current: {current_start_ts.date()} to {current_end_ts.date()} | Previous: {prev_start.date()} to {prev_end.date()}"
                    ),
                    yaxis_title=f"Amount ({currency})",
                )
                fig_cmp = _style_plot(fig_cmp, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig_cmp, width="stretch")

                current_cat = (
                    filtered_chart_df.groupby('category', as_index=False)['amount'].sum()
                    .rename(columns={'amount': 'Current'})
                    if not filtered_chart_df.empty else pd.DataFrame(columns=['category', 'Current'])
                )
                prev_cat = (
                    prev_exp_df.groupby('category', as_index=False)['amount'].sum()
                    .rename(columns={'amount': 'Previous'})
                    if not prev_exp_df.empty else pd.DataFrame(columns=['category', 'Previous'])
                )

                compare_cat = pd.merge(current_cat, prev_cat, on='category', how='outer').fillna(0.0)
                if not compare_cat.empty:
                    compare_cat_long = compare_cat.melt(id_vars='category', var_name='period', value_name='amount')
                    fig_cat_cmp = px.bar(
                        compare_cat_long,
                        x='category',
                        y='amount',
                        color='period',
                        barmode='group',
                        title='Categorized Expense Totals: Current vs Previous',
                    )
                    fig_cat_cmp.update_layout(yaxis_title=f"Amount ({currency})")
                    fig_cat_cmp = _style_plot(fig_cat_cmp, selected_font_css, plot_font_size, chart_height_setting)
                    st.plotly_chart(fig_cat_cmp, width="stretch")
                else:
                    st.info("No categorized comparison data available for the selected range.")

        if not filtered_chart_df.empty:
            trend_df = _aggregate_series(filtered_chart_df, 'date', 'amount', expense_granularity)
            if not trend_df.empty:
                trend_df['rolling_avg'] = trend_df['amount'].rolling(3, min_periods=1).mean()
                fig_editor_trend = go.Figure()
                fig_editor_trend.add_trace(go.Bar(
                    x=trend_df['period_start'],
                    y=trend_df['amount'],
                    name=f'{expense_granularity} Total',
                ))
                fig_editor_trend.add_trace(go.Scatter(
                    x=trend_df['period_start'],
                    y=trend_df['cumulative_amount'],
                    mode='lines+markers',
                    name='Cumulative Total',
                    line={"width": 3},
                ))
                fig_editor_trend.add_trace(go.Scatter(
                    x=trend_df['period_start'],
                    y=trend_df['rolling_avg'],
                    mode='lines',
                    name=f'{expense_granularity} Avg Trend',
                    line={"width": 2, "dash": "dot"},
                ))
                fig_editor_trend.update_layout(
                    title=(
                        f'Expense Total and Cumulative Trend - {expense_granularity} '
                        f'({exp_start_date} to {exp_end_date})'
                    ),
                    yaxis_title=f'Amount ({currency})',
                    legend_title_text=f'{expense_granularity} Metrics',
                )
                fig_editor_trend = _style_plot(fig_editor_trend, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig_editor_trend, width="stretch")
        else:
            st.info("Select a valid time frame with expense data to see totals and cumulative charts.")


# --- Tab: Income ---
with tab_income:
    st.header("Income")
    income = get_all_income()
    df_i = pd.DataFrame([{"id": i.id, "date": i.date, "source": i.source, "amount": i.amount} for i in income])

    if df_i.empty:
        df_i = pd.DataFrame(columns=["id", "date", "source", "amount"])

    sort_option_inc = st.selectbox(
        "Income Date Sort",
        ["Newest first", "Oldest first"],
        index=0,
        key="income_sort_option",
    )
    sort_ascending_inc = sort_option_inc == "Oldest first"

    df_i_for_editor = df_i.copy()
    if not df_i_for_editor.empty:
        df_i_for_editor["date"] = pd.to_datetime(df_i_for_editor["date"], errors='coerce')
        df_i_for_editor = df_i_for_editor.sort_values(by=["date", "id"], ascending=[sort_ascending_inc, sort_ascending_inc])

    chart_container_inc = st.container()
    editor_container_inc = st.container()

    with editor_container_inc:
        st.subheader("Manage Income")
        edited_inc = st.data_editor(
            df_i_for_editor,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "amount": st.column_config.NumberColumn("Amount", format=f"{currency}%.2f"),
                "date": st.column_config.DateColumn("Date"),
            },
            hide_index=True,
            num_rows="dynamic",
            key="inc_editor",
        )

        cleaned_inc = edited_inc.copy()
        if 'date' in cleaned_inc.columns:
            cleaned_inc['date'] = pd.to_datetime(cleaned_inc['date'], errors='coerce').dt.date

        delete_income_count = 0
        if 'id' in df_i.columns and 'id' in cleaned_inc.columns:
            original_income_ids = set(df_i['id'].dropna().astype(int).tolist()) if not df_i.empty else set()
            edited_income_ids = set(cleaned_inc['id'].dropna().astype(int).tolist()) if not cleaned_inc.empty else set()
            delete_income_count = len(original_income_ids - edited_income_ids)

        if st.button("Save Income", key="save_income_button"):
            if delete_income_count > 0:
                st.session_state['pending_income_save'] = True
                st.session_state['pending_income_delete_count'] = delete_income_count
            else:
                update_income_from_df(cleaned_inc)
                st.success("Income saved!")
                st.rerun()

        if st.session_state.get('pending_income_save', False):
            pending_income_delete = st.session_state.get('pending_income_delete_count', 0)
            st.warning(f"This save will permanently delete {pending_income_delete} income row(s) from the database.")
            i1, i2 = st.columns(2)
            with i1:
                if st.button("Confirm Income Save", key="confirm_income_save"):
                    update_income_from_df(cleaned_inc)
                    st.session_state['pending_income_save'] = False
                    st.session_state['pending_income_delete_count'] = 0
                    st.success("Income saved!")
                    st.rerun()
            with i2:
                if st.button("Cancel Income Save", key="cancel_income_save"):
                    st.session_state['pending_income_save'] = False
                    st.session_state['pending_income_delete_count'] = 0

        st.download_button(
            "Download Income CSV",
            data=_to_csv(cleaned_inc),
            file_name="income.csv",
            mime="text/csv",
        )

    with chart_container_inc:
        st.subheader("Real-Time Income Chart")
        chart_inc = cleaned_inc.copy()
        if not chart_inc.empty:
            chart_inc['amount'] = pd.to_numeric(chart_inc['amount'], errors='coerce').fillna(0.0)
            chart_inc['date'] = pd.to_datetime(chart_inc['date'], errors='coerce')
            chart_inc = chart_inc.dropna(subset=['date'])
            if not chart_inc.empty:
                grouped_inc = chart_inc.groupby(['date', 'source'], as_index=False)['amount'].sum()
                fig_inc = px.bar(grouped_inc, x='date', y='amount', color='source', barmode='group')
                fig_inc.update_layout(yaxis_title=f"Amount ({currency})")
                fig_inc = _style_plot(fig_inc, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig_inc, width="stretch")

                trend_income = chart_inc.groupby('date', as_index=False)['amount'].sum().sort_values('date')
                trend_income['rolling_7'] = trend_income['amount'].rolling(7, min_periods=1).mean()
                fig_inc_trend2 = go.Figure()
                fig_inc_trend2.add_trace(go.Scatter(x=trend_income['date'], y=trend_income['amount'], mode='lines+markers', name='Daily'))
                fig_inc_trend2.add_trace(go.Scatter(x=trend_income['date'], y=trend_income['rolling_7'], mode='lines', name='7-day Trend', line={"width": 3}))
                fig_inc_trend2.update_layout(title='Income Trendline (Editor Data)', yaxis_title=f'Amount ({currency})')
                fig_inc_trend2 = _style_plot(fig_inc_trend2, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig_inc_trend2, width="stretch")
            else:
                st.info("Add valid income dates to visualize trends.")
        else:
            st.info("Add income rows to visualize trends.")

# --- Tab: Budget Goals ---
with tab_budgets:
    st.header("Category Budget Goals")

    with st.form("set_budget_form", clear_on_submit=True):
        budget_category = st.selectbox("Category", categories)
        budget_limit = st.number_input("Monthly Limit", min_value=0.0, format="%.2f")
        budget_submit = st.form_submit_button("Set Budget")
        if budget_submit:
            set_budget(budget_category, budget_limit)
            st.success("Budget goal saved.")
            st.rerun()

    budget_rows = get_budgets()
    if budget_rows:
        budget_df = pd.DataFrame([
            {"category": b.category, "monthly_limit": b.monthly_limit}
            for b in budget_rows
        ])

        exp_month_df = pd.DataFrame([
            {"date": e.date, "category": e.category, "amount": e.amount}
            for e in get_all_expenses()
        ])
        exp_month_df = _ensure_date_col(exp_month_df)

        today = pd.Timestamp.today()
        month_start = today.replace(day=1)
        if not exp_month_df.empty:
            current_month = exp_month_df[exp_month_df['date'] >= month_start]
            spend_by_category = current_month.groupby('category', as_index=False)['amount'].sum()
        else:
            spend_by_category = pd.DataFrame(columns=['category', 'amount'])

        st.subheader("Current Month Progress")
        for _, row in budget_df.iterrows():
            cat = row['category']
            limit = float(row['monthly_limit'])
            spent_row = spend_by_category[spend_by_category['category'] == cat]
            spent = float(spent_row['amount'].sum()) if not spent_row.empty else 0.0
            ratio = (spent / limit) if limit > 0 else 0.0
            remaining = limit - spent

            if ratio < 0.8:
                status = "On track"
                bar_color = "#16a34a"
                details = f"Great control. Remaining this month: {currency}{max(0.0, remaining):,.2f}"
            elif ratio <= 1.0:
                status = "Near limit"
                bar_color = "#f59e0b"
                details = f"You are close to the limit. Remaining: {currency}{max(0.0, remaining):,.2f}"
            else:
                status = "Over budget"
                bar_color = "#dc2626"
                details = f"Over budget by {currency}{abs(remaining):,.2f}. Consider reducing spending in this category."

            _render_colored_progress(
                f"{cat}: {currency}{spent:,.2f} / {currency}{limit:,.2f}",
                ratio,
                status,
                bar_color,
                details,
            )

            if st.button(f"Delete Goal: {cat}", key=f"delete_goal_{cat}"):
                delete_budget(cat)
                st.success(f"Deleted budget goal for {cat}.")
                st.rerun()

    else:
        st.info("No budget goals set yet.")

    st.divider()
    st.subheader("Monthly Savings Goal")

    exp_month_df_for_savings = pd.DataFrame([
        {"date": e.date, "amount": e.amount}
        for e in get_all_expenses()
    ])
    exp_month_df_for_savings = _ensure_date_col(exp_month_df_for_savings)

    inc_month_df = pd.DataFrame([
        {"date": i.date, "amount": i.amount}
        for i in get_all_income()
    ])
    inc_month_df = _ensure_date_col(inc_month_df)

    today = pd.Timestamp.today()
    month_start = today.replace(day=1)

    if not inc_month_df.empty:
        current_month_income = float(inc_month_df[inc_month_df['date'] >= month_start]['amount'].sum())
    else:
        current_month_income = 0.0
    if not exp_month_df_for_savings.empty:
        current_month_expenses = float(exp_month_df_for_savings[exp_month_df_for_savings['date'] >= month_start]['amount'].sum())
    else:
        current_month_expenses = 0.0
    current_month_savings = current_month_income - current_month_expenses

    configured_goal = float(get_setting('monthly_savings_goal', '0') or 0)
    if configured_goal <= 0:
        auto_goal = round(current_month_income * 0.2, 2) if current_month_income > 0 else 100.0
        configured_goal = auto_goal
        set_setting('monthly_savings_goal', f"{configured_goal:.2f}")
        st.info(
            f"No savings goal was set, so a default goal of {currency}{configured_goal:,.2f} was created."
        )

    savings_goal_input = st.number_input(
        "Monthly Savings Goal",
        min_value=0.0,
        value=float(configured_goal),
        format="%.2f",
        key="monthly_savings_goal_input",
    )
    if st.button("Save Savings Goal", key="save_savings_goal"):
        set_setting('monthly_savings_goal', f"{float(savings_goal_input):.2f}")
        st.success("Savings goal updated.")
        st.rerun()

    savings_goal = float(savings_goal_input)
    savings_ratio = (current_month_savings / savings_goal) if savings_goal > 0 else 0.0
    if savings_goal > 0 and current_month_savings >= savings_goal:
        savings_status = "Goal achieved"
        savings_color = "#16a34a"
        savings_details = (
            f"Excellent. You are above your savings target by "
            f"{currency}{(current_month_savings - savings_goal):,.2f}."
        )
    elif savings_goal > 0 and current_month_savings >= (0.7 * savings_goal):
        savings_status = "Almost there"
        savings_color = "#f59e0b"
        savings_details = (
            f"Good progress. You need {currency}{max(0.0, savings_goal - current_month_savings):,.2f} more "
            f"to hit your goal."
        )
    else:
        savings_status = "Below goal"
        savings_color = "#dc2626"
        savings_details = (
            f"Savings are behind target by {currency}{max(0.0, savings_goal - current_month_savings):,.2f}."
        )

    _render_colored_progress(
        (
            f"Saved this month: {currency}{current_month_savings:,.2f} "
            f"/ Goal: {currency}{savings_goal:,.2f}"
        ),
        savings_ratio if savings_goal > 0 else 0.0,
        savings_status,
        savings_color,
        savings_details,
    )

# --- Tab: Settings ---
with tab_settings:
    st.header("Settings")

    st.subheader("Appearance")
    theme_options = ["Light", "Dark"]
    current_theme_index = theme_options.index(selected_theme_mode) if selected_theme_mode in theme_options else 0
    chosen_theme_mode = st.selectbox("Color Mode", theme_options, index=current_theme_index)
    if st.button("Save Appearance"):
        set_setting('theme_mode', chosen_theme_mode)
        st.success("Appearance updated.")
        st.rerun()

    st.subheader("Currency")
    currency_options = ["$", "€", "£", "₹", "CHF"]
    current_currency = get_setting('currency', '$')
    default_index = currency_options.index(current_currency) if current_currency in currency_options else 0
    selected_currency = st.selectbox("Display Currency", currency_options, index=default_index)
    if st.button("Save Currency"):
        set_setting('currency', selected_currency)
        st.success("Currency updated.")
        st.rerun()

    st.subheader("Typography")
    font_names = list(FONT_OPTIONS.keys())
    default_font_index = font_names.index(selected_font_name) if selected_font_name in font_names else 0
    chosen_font_name = st.selectbox("Font Family", font_names, index=default_font_index)
    chosen_scale = st.slider("UI Scale", min_value=0.90, max_value=1.30, value=ui_scale, step=0.05)
    density_options = ["Compact", "Comfortable"]
    default_density_index = density_options.index(layout_density) if layout_density in density_options else 1
    chosen_density = st.selectbox("Layout Density", density_options, index=default_density_index)
    chosen_chart_height = st.slider("Chart Scale", min_value=360, max_value=780, value=chart_height_setting, step=20)
    if st.button("Save Typography"):
        set_setting('font_family_name', chosen_font_name)
        set_setting('ui_scale', f"{chosen_scale:.2f}")
        set_setting('layout_density', chosen_density)
        set_setting('chart_height', str(chosen_chart_height))
        st.success("Typography updated.")
        st.rerun()

    st.subheader("Manage Categories")
    new_cat = st.text_input("New Category Name")
    if st.button("Add Category"):
        if new_cat:
            created = add_category(new_cat)
            if created:
                st.success(f"Category '{new_cat}' added!")
                st.rerun()
            else:
                st.info("Category already exists or is invalid.")

    if categories:
        remove_cat = st.selectbox("Delete Category", options=categories)
        if st.button("Delete Selected Category"):
            deleted = delete_category(remove_cat)
            if deleted:
                st.success(f"Category '{remove_cat}' deleted.")
                st.rerun()
            else:
                st.warning("Cannot delete this category because it is in use by existing expenses.")

    st.write("Current Categories:", ", ".join(categories))

    st.subheader("Export All Data")
    all_exp = pd.DataFrame([
        {
            "id": e.id,
            "date": e.date,
            "category": e.category,
            "amount": e.amount,
            "store": e.store,
            "place": e.place,
            "description": e.description,
        }
        for e in get_all_expenses()
    ])
    all_inc = pd.DataFrame([
        {
            "id": i.id,
            "date": i.date,
            "source": i.source,
            "amount": i.amount,
        }
        for i in get_all_income()
    ])

    st.download_button(
        "Download All Expenses CSV",
        data=_to_csv(all_exp),
        file_name="all_expenses.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download All Income CSV",
        data=_to_csv(all_inc),
        file_name="all_income.csv",
        mime="text/csv",
    )
