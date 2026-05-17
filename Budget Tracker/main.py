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


def _ensure_date_col(df, col_name='date'):
    if df.empty:
        return df
    out = df.copy()
    out[col_name] = pd.to_datetime(out[col_name], errors='coerce')
    return out


def _to_csv(df):
    return df.to_csv(index=False).encode('utf-8')


def _style_plot(fig, font_family, base_size, chart_height):
    fig.update_layout(
        font={"family": font_family, "size": base_size},
        template="simple_white",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        height=chart_height,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(15,23,42,0.08)", zeroline=False)
    return fig


def _create_3d_like_pie(df, value_col, name_col, title):
    pie_df = df.groupby(name_col, as_index=False)[value_col].sum()
    if pie_df.empty:
        return None

    # Layered donut traces create a subtle 3D-like depth effect.
    base = go.Pie(
        labels=pie_df[name_col],
        values=pie_df[value_col],
        hole=0.35,
        textinfo='none',
        marker={"colors": ["rgba(30,64,175,0.25)", "rgba(15,23,42,0.25)", "rgba(14,116,144,0.25)", "rgba(21,128,61,0.25)", "rgba(180,83,9,0.25)", "rgba(190,24,93,0.25)"]},
        sort=False,
        direction='clockwise',
        domain={"x": [0, 1], "y": [0.04, 1]},
    )
    top = go.Pie(
        labels=pie_df[name_col],
        values=pie_df[value_col],
        hole=0.35,
        textinfo='percent+label',
        textposition='inside',
        textfont={"color": "#e5e9f0", "size": 14},
        automargin=True,
        sort=False,
        direction='clockwise',
        marker={"line": {"color": "white", "width": 1}},
        domain={"x": [0, 1], "y": [0.10, 1]},
    )

    fig = go.Figure(data=[base, top])
    fig.update_layout(title=title, showlegend=False)
    return fig


def _apply_ui_typography(font_family, ui_scale, density_mode):
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
        }}

        html, body, [class*="css"], .stApp {{
            font-family: var(--app-font-family) !important;
            font-size: calc(16px * var(--app-scale));
            line-height: 1.45;
            color: #0f172a;
        }}

        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        }}

        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #e2e8f0 0%, #cbd5e1 100%) !important;
            border-right: 1px solid rgba(100,116,139,0.45);
        }}

        [data-testid="stSidebar"] * {{
            color: #0b1220 !important;
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
            color: #0b1220 !important;
            font-weight: 700 !important;
        }}

        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-baseweb="input"] > div,
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea {{
            background: #ffffff !important;
            color: #0b1220 !important;
            border: 1px solid #64748b !important;
        }}

        [data-testid="stSidebar"] [role="radiogroup"] label {{
            color: #0b1220 !important;
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
            color: #0b1220;
        }}

        h1 {{
            font-weight: 800;
            color: #0a1020;
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
            color: #0b1220 !important;
            font-weight: 800 !important;
        }}

        [data-testid="stMetricValue"] {{
            color: #0b1220 !important;
            font-weight: 800 !important;
            text-shadow: none !important;
            opacity: 1 !important;
        }}

        [data-testid="stMetric"] {{
            background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(241,245,249,0.98) 100%);
            border: 1px solid rgba(100,116,139,0.45);
            border-radius: var(--app-radius);
            padding: var(--app-card-padding);
            box-shadow: 0 2px 6px rgba(15,23,42,0.08);
        }}

        [data-testid="stMetric"] * {{
            color: #0b1220 !important;
            opacity: 1 !important;
        }}

        [data-testid="stMetricLabel"] {{
            font-weight: 600;
            color: #1e293b !important;
        }}

        [data-testid="stMetricDelta"] {{
            color: #334155 !important;
            font-weight: 700;
        }}

        [data-testid="stDataFrameResizable"] {{
            border: 1px solid rgba(148,163,184,0.30);
            border-radius: var(--app-radius);
            overflow: hidden;
        }}

        .stAlert {{
            border-radius: var(--app-radius);
        }}

        .stButton > button {{
            border-radius: 10px;
            border: 1px solid #1d4ed8;
            font-weight: 600;
            padding-top: 0.4rem;
            padding-bottom: 0.4rem;
            background: #1d4ed8 !important;
            color: #ffffff !important;
            opacity: 1 !important;
        }}

        .stForm button,
        [data-testid="stForm"] button,
        [data-testid="stFormSubmitButton"] button,
        button[kind="primary"],
        button[kind="secondary"] {{
            background: #1d4ed8 !important;
            color: #ffffff !important;
            border: 1px solid #1e40af !important;
            font-weight: 700 !important;
            text-shadow: none !important;
            opacity: 1 !important;
        }}

        .stForm button:hover,
        [data-testid="stForm"] button:hover,
        [data-testid="stFormSubmitButton"] button:hover,
        button[kind="primary"]:hover,
        button[kind="secondary"]:hover {{
            background: #1e40af !important;
            color: #ffffff !important;
            border-color: #1e3a8a !important;
        }}

        .stForm button span,
        [data-testid="stForm"] button span,
        [data-testid="stFormSubmitButton"] button span {{
            color: #ffffff !important;
            opacity: 1 !important;
        }}

        .stButton > button:hover {{
            background: #1e40af !important;
            border-color: #1e40af !important;
            color: #ffffff !important;
        }}

        .stDownloadButton > button {{
            border-radius: 10px;
            font-weight: 600;
            border: 1px solid #334155;
            background: #ffffff !important;
            color: #0f172a !important;
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
            color: #0b5fff;
            border-bottom-color: #0b5fff !important;
        }}

        .stTabs [data-baseweb="tab"] p {{
            color: #0b1220 !important;
            font-size: calc(1.08rem * var(--app-scale)) !important;
            font-weight: 700 !important;
            letter-spacing: 0.2px;
        }}

        label, .stSelectbox label, .stSlider label, .stNumberInput label {{
            color: #0f172a !important;
            font-weight: 700 !important;
            opacity: 1 !important;
        }}

        [data-baseweb="select"] > div {{
            background: #ffffff !important;
            border: 1px solid #64748b !important;
            min-height: 2.5rem;
        }}

        [data-baseweb="select"] * {{
            color: #0f172a !important;
            opacity: 1 !important;
        }}

        [data-testid="stSlider"] * {{
            color: #0f172a !important;
            opacity: 1 !important;
        }}

        [data-testid="stSidebar"] [data-testid="stSlider"] * {{
            color: #0b1220 !important;
            opacity: 1 !important;
            font-weight: 700 !important;
        }}

        [data-testid="stSlider"] [role="slider"] {{
            background: #1d4ed8 !important;
            border: 2px solid #1e3a8a !important;
        }}

        [data-testid="stSliderTickBarMin"],
        [data-testid="stSliderTickBarMax"],
        [data-testid="stSliderTickBar"] {{
            color: #1e293b !important;
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
ui_scale = float(get_setting('ui_scale', '1.00'))
layout_density = get_setting('layout_density', 'Comfortable')
if layout_density not in ["Compact", "Comfortable"]:
    layout_density = "Comfortable"
chart_height_setting = int(get_setting('chart_height', '460'))
chart_height_setting = max(360, min(chart_height_setting, 780))

_apply_ui_typography(selected_font_css, ui_scale, layout_density)

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
    view_option = st.selectbox("View Perspective", ["Weekly", "Monthly", "Yearly"])
    
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
        
        # Filter based on view_option (showing current period)
        today = pd.Timestamp.now()
        if view_option == "Weekly":
            start_date = today - timedelta(days=today.weekday())
        elif view_option == "Monthly":
            start_date = today.replace(day=1)
        else: # Yearly
            start_date = today.replace(month=1, day=1)
            
        current_exp = df_exp[df_exp['date'] >= start_date] if not df_exp.empty else pd.DataFrame()
        current_inc = df_inc[df_inc['date'] >= start_date] if not df_inc.empty else pd.DataFrame()
        
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
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if not current_exp.empty:
                st.subheader("Expense Distribution")
                fig = _create_3d_like_pie(current_exp, 'amount', 'category', 'Expense Distribution (3D-style)')
                if fig is not None:
                    fig = _style_plot(fig, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig, use_container_width=True)
        with col_c2:
            st.subheader("Income vs Expenses")
            exp_series = current_exp.groupby('date', as_index=False)['amount'].sum() if not current_exp.empty else pd.DataFrame(columns=['date', 'amount'])
            exp_series['kind'] = 'Expenses'
            inc_series = current_inc.groupby('date', as_index=False)['amount'].sum() if not current_inc.empty else pd.DataFrame(columns=['date', 'amount'])
            inc_series['kind'] = 'Income'
            compare_df = pd.concat([exp_series, inc_series], ignore_index=True)
            if not compare_df.empty:
                fig = px.bar(compare_df, x='date', y='amount', color='kind', barmode='group')
                fig.update_layout(yaxis_title=f"Amount ({currency})")
                fig = _style_plot(fig, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig, use_container_width=True)

        st.subheader("Trendlines")
        t1, t2 = st.columns(2)
        with t1:
            if not current_exp.empty:
                exp_trend = current_exp.groupby('date', as_index=False)['amount'].sum().sort_values('date')
                exp_trend['rolling_7'] = exp_trend['amount'].rolling(7, min_periods=1).mean()
                fig_exp_trend = go.Figure()
                fig_exp_trend.add_trace(go.Scatter(x=exp_trend['date'], y=exp_trend['amount'], mode='lines+markers', name='Daily Expenses'))
                fig_exp_trend.add_trace(go.Scatter(x=exp_trend['date'], y=exp_trend['rolling_7'], mode='lines', name='7-day Trend', line={"width": 3}))
                fig_exp_trend.update_layout(title='Expense Trendline', yaxis_title=f'Amount ({currency})')
                fig_exp_trend = _style_plot(fig_exp_trend, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig_exp_trend, use_container_width=True)
            else:
                st.info("Add expense history to see trendlines.")
        with t2:
            if not current_inc.empty:
                inc_trend = current_inc.groupby('date', as_index=False)['amount'].sum().sort_values('date')
                inc_trend['rolling_7'] = inc_trend['amount'].rolling(7, min_periods=1).mean()
                fig_inc_trend = go.Figure()
                fig_inc_trend.add_trace(go.Scatter(x=inc_trend['date'], y=inc_trend['amount'], mode='lines+markers', name='Daily Income'))
                fig_inc_trend.add_trace(go.Scatter(x=inc_trend['date'], y=inc_trend['rolling_7'], mode='lines', name='7-day Trend', line={"width": 3}))
                fig_inc_trend.update_layout(title='Income Trendline', yaxis_title=f'Amount ({currency})')
                fig_inc_trend = _style_plot(fig_inc_trend, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig_inc_trend, use_container_width=True)
            else:
                st.info("Add income history to see trendlines.")

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

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            if not chart_df.empty:
                pie_source = chart_df.dropna(subset=['category'])
                if not pie_source.empty:
                    pie = _create_3d_like_pie(pie_source, 'amount', 'category', 'Expense Share (3D-style)')
                    if pie is not None:
                        pie = _style_plot(pie, selected_font_css, plot_font_size, chart_height_setting)
                        pie.update_layout(uniformtext_minsize=11, uniformtext_mode='show')
                        st.plotly_chart(pie, use_container_width=True)
                else:
                    st.info("Add categories to see chart distribution.")
            else:
                st.info("Add expenses to see chart distribution.")

        with chart_col2:
            if not chart_df.empty:
                bar_source = chart_df.dropna(subset=['date']).copy()
                if not bar_source.empty:
                    bar_source['date'] = pd.to_datetime(bar_source['date'], errors='coerce')
                    bar_source = bar_source.groupby('date', as_index=False)['amount'].sum()
                    bar = px.bar(bar_source, x='date', y='amount')
                    bar.update_layout(yaxis_title=f"Amount ({currency})")
                    bar = _style_plot(bar, selected_font_css, plot_font_size, chart_height_setting)
                    st.plotly_chart(bar, use_container_width=True)
                else:
                    st.info("Add valid dates to see timeline chart.")
            else:
                st.info("Add expenses to see timeline chart.")

        if not chart_df.empty:
            trend_df = chart_df.dropna(subset=['date']).copy()
            trend_df['date'] = pd.to_datetime(trend_df['date'], errors='coerce')
            trend_df = trend_df.dropna(subset=['date'])
            if not trend_df.empty:
                trend_df = trend_df.groupby('date', as_index=False)['amount'].sum().sort_values('date')
                trend_df['rolling_7'] = trend_df['amount'].rolling(7, min_periods=1).mean()
                fig_editor_trend = go.Figure()
                fig_editor_trend.add_trace(go.Scatter(x=trend_df['date'], y=trend_df['amount'], mode='lines+markers', name='Daily'))
                fig_editor_trend.add_trace(go.Scatter(x=trend_df['date'], y=trend_df['rolling_7'], mode='lines', name='7-day Trend', line={"width": 3}))
                fig_editor_trend.update_layout(title='Expense Trendline (Editor Data)', yaxis_title=f'Amount ({currency})')
                fig_editor_trend = _style_plot(fig_editor_trend, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig_editor_trend, use_container_width=True)


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
                st.plotly_chart(fig_inc, use_container_width=True)

                trend_income = chart_inc.groupby('date', as_index=False)['amount'].sum().sort_values('date')
                trend_income['rolling_7'] = trend_income['amount'].rolling(7, min_periods=1).mean()
                fig_inc_trend2 = go.Figure()
                fig_inc_trend2.add_trace(go.Scatter(x=trend_income['date'], y=trend_income['amount'], mode='lines+markers', name='Daily'))
                fig_inc_trend2.add_trace(go.Scatter(x=trend_income['date'], y=trend_income['rolling_7'], mode='lines', name='7-day Trend', line={"width": 3}))
                fig_inc_trend2.update_layout(title='Income Trendline (Editor Data)', yaxis_title=f'Amount ({currency})')
                fig_inc_trend2 = _style_plot(fig_inc_trend2, selected_font_css, plot_font_size, chart_height_setting)
                st.plotly_chart(fig_inc_trend2, use_container_width=True)
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
            elif ratio <= 1.0:
                status = "Near limit"
            else:
                status = "Over budget"

            st.write(f"{cat}: {currency}{spent:,.2f} / {currency}{limit:,.2f}")
            st.progress(min(ratio, 1.0), text=f"{ratio * 100:,.1f}% · {status}")
            if ratio < 0.8:
                st.success(f"Remaining this month: {currency}{max(0.0, remaining):,.2f}")
            elif ratio <= 1.0:
                st.warning(f"You are close to the limit. Remaining: {currency}{max(0.0, remaining):,.2f}")
            else:
                st.error(f"Over budget by {currency}{abs(remaining):,.2f}")

            if st.button(f"Delete Goal: {cat}", key=f"delete_goal_{cat}"):
                delete_budget(cat)
                st.success(f"Deleted budget goal for {cat}.")
                st.rerun()
    else:
        st.info("No budget goals set yet.")

# --- Tab: Settings ---
with tab_settings:
    st.header("Settings")
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
