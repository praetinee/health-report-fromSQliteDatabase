import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from datetime import datetime
import io
import time
import base64

# --- Import modules ---
from auth import check_password, logout
from visualization import (
    render_gauge_chart,
    render_history_chart,
    render_bmi_gauge,
    render_blood_pressure_gauge,
    render_risk_factors_chart
)
from utils import (
    load_data,
    get_unique_years,
    filter_data_by_year,
    safe_float,
    calculate_age,
    process_uploaded_file,
    sync_to_database
)
from admin_panel import render_admin_panel
from batch_print import render_batch_print_page
from performance_tests import render_performance_tests_summary
from print_report import generate_printable_report
from print_performance_report import generate_performance_report_html
from line_register import render_line_registration_ui # Import Line Registration UI

# --- Constants ---
DB_PATH = 'health_data.db'

# --- Page Config ---
st.set_page_config(
    page_title="Health Data Analytics",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Initialization ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'role' not in st.session_state:
    st.session_state.role = None
if 'selected_year' not in st.session_state:
    st.session_state.selected_year = None
if 'selected_hn' not in st.session_state:
    st.session_state.selected_hn = None
if 'show_history' not in st.session_state:
    st.session_state.show_history = False

# --- Helper Functions for UI ---
def format_value(val, unit=""):
    if pd.isna(val) or val == "":
        return "-"
    try:
        # Check if it's an integer stored as float
        if isinstance(val, float) and val.is_integer():
            return f"{int(val)} {unit}"
        # Check if it's a float
        elif isinstance(val, float):
             return f"{val:.2f} {unit}"
        return f"{val} {unit}"
    except:
        return f"{val} {unit}"

def get_status_color(val, low, high, reverse=False):
    if val is None:
        return "normal"
    try:
        val = float(val)
        if reverse:
             if val > high: return "normal" # Higher is better (e.g. HDL) -> Normal if > high
             if val < low: return "danger" # Too low
             return "warning" # In between
        else:
            if val < low: return "normal" # Too low is generally not flagged red in basic logic, or maybe warning. Let's assume normal for now or add 'low' logic.
            # Actually, standard logic:
            if low <= val <= high: return "normal"
            if val > high: return "danger"
            return "normal" # Default
    except:
        return "normal"
    
def display_kpi_card(title, value, unit, status="normal", sub_text=""):
    colors = {
        "normal": "#e8f5e9", # Light Green
        "warning": "#fff3e0", # Light Orange
        "danger": "#ffebee"   # Light Red
    }
    text_colors = {
        "normal": "#1b5e20",
        "warning": "#e65100",
        "danger": "#b71c1c"
    }
    
    st.markdown(
        f"""
        <div style="
            background-color: {colors.get(status, '#ffffff')};
            padding: 1rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
            height: 100%;
            border: 1px solid rgba(0,0,0,0.05);
        ">
            <h4 style="margin: 0; color: #555; font-size: 0.9rem;">{title}</h4>
            <h2 style="margin: 0.5rem 0; color: {text_colors.get(status, '#333')}; font-size: 1.8rem;">{value}</h2>
            <p style="margin: 0; color: #777; font-size: 0.8rem;">{unit}</p>
            {f'<p style="margin-top: 0.2rem; color: #666; font-size: 0.75rem;">{sub_text}</p>' if sub_text else ''}
        </div>
        """,
        unsafe_allow_html=True
    )

def render_custom_header_with_actions(person_data, available_years):
    """
    Renders a custom header with personal info on the left/center
    and action buttons (Print, History Toggle, Year Select) on the right.
    """
    # 1. Prepare Data
    name = person_data.get('ชื่อ-สกุล', 'Unknown')
    # Safe HN parsing
    raw_hn = person_data.get('HN')
    if pd.isna(raw_hn) or str(raw_hn).strip() == '':
        hn = '-'
    else:
        try:
            str_hn = str(raw_hn)
            # Remove decimals if present (e.g. "12345.0" -> "12345")
            if "." in str_hn:
                str_hn = str_hn.split(".")[0]
            hn = str_hn
        except:
             hn = str(raw_hn)
             
    age = person_data.get('อายุ', '-')
    if isinstance(age, float) and age.is_integer():
        age = int(age)

    # 2. Container Layout
    # Use columns to separate info and controls
    c1, c2 = st.columns([3, 2])

    with c1:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 15px;">
            <div style="background-color: #00796b; color: white; padding: 10px 15px; border-radius: 50%; font-weight: bold; font-size: 1.2rem;">
                {name[0] if name else '?'}
            </div>
            <div>
                <h2 style="margin: 0; color: #333;">{name}</h2>
                <p style="margin: 0; color: #666; font-size: 0.95rem;">
                    <strong>HN:</strong> {hn} &nbsp;|&nbsp; 
                    <strong>Age:</strong> {age} &nbsp;|&nbsp; 
                    <strong>Dep:</strong> {person_data.get('หน่วยงาน', '-')}
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        # Align controls to the right
        rc1, rc2, rc3 = st.columns([1.5, 1, 1])
        
        with rc1:
            # Year Selection
            selected_year = st.selectbox(
                "📅 ปีงบประมาณ",
                options=available_years,
                index=available_years.index(st.session_state.selected_year) if st.session_state.selected_year in available_years else 0,
                key="year_selector_header",
                label_visibility="collapsed"
            )
            if selected_year != st.session_state.selected_year:
                st.session_state.selected_year = selected_year
                st.rerun()

        with rc2:
             # History Toggle
            if st.button("📊 ประวัติ", use_container_width=True, type="primary" if st.session_state.show_history else "secondary"):
                st.session_state.show_history = not st.session_state.show_history
                st.rerun()

        with rc3:
            # Print Button (Opens Modal or Direct Action)
            # Since we can't easily pop up a print window from Streamlit directly without JS,
            # we'll use a link to a "printable" view or generate HTML.
            # For now, let's make it a download button for the HTML report.
            pass # We will handle print generation below in the main area to keep this clean or add a button here that triggers it.
            
    st.markdown("---")

# --- Main App Logic ---
def main_app(df):
    
    # --- Sidebar ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username} ({st.session_state.role})")
        if st.button("Logout", key="logout_btn", use_container_width=True):
            logout()
            st.rerun()
        
        st.markdown("---")
        
        # Navigation
        page = st.radio("Navigation", ["Dashboard", "Individual Report", "Batch Print", "Line Registration", "Admin Panel"] if st.session_state.role == 'admin' else ["Dashboard", "Individual Report", "Batch Print", "Line Registration"])
        
        # Year Filter (Global)
        available_years = get_unique_years(df)
        if not available_years:
            st.error("No data available.")
            return

        # Ensure selected year is valid
        if st.session_state.selected_year not in available_years:
             st.session_state.selected_year = available_years[0]
    
    # --- Filter Data by Year ---
    df_year = filter_data_by_year(df, st.session_state.selected_year)
    
    # --- Page Routing ---
    if page == "Dashboard":
        st.title(f"📊 Health Analytics Dashboard ({st.session_state.selected_year})")
        
        # 1. Key Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        with m1: display_kpi_card("Total Staff", len(df_year), "Persons")
        with m2: 
            bmi_high = df_year[pd.to_numeric(df_year['BMI'], errors='coerce') >= 25]
            display_kpi_card("Overweight/Obese", len(bmi_high), "Persons", "warning", f"{len(bmi_high)/len(df_year)*100:.1f}%")
        with m3:
            sbp_high = df_year[pd.to_numeric(df_year['SBP'], errors='coerce') >= 140]
            display_kpi_card("High BP", len(sbp_high), "Persons", "danger", f"{len(sbp_high)/len(df_year)*100:.1f}%")
        with m4:
             # Example: Vision Issues
             vision_issues = df_year[df_year['สรุปเหมาะสมกับงาน'].astype(str).str.contains('ผิดปกติ', na=False)]
             display_kpi_card("Vision Issues", len(vision_issues), "Persons", "warning")

        # 2. Charts Row 1
        st.markdown("### 📈 Health Trends & Distributions")
        c1, c2 = st.columns(2)
        with c1:
            render_bmi_gauge(df_year)
        with c2:
            render_blood_pressure_gauge(df_year)
            
        # 3. Risk Factors
        st.markdown("### ⚠️ Risk Factors Analysis")
        render_risk_factors_chart(df_year)

    elif page == "Individual Report":
        # Search / Select Person
        # Combine HN and Name for search
        df_year['Search_Label'] = df_year['HN'].astype(str) + " - " + df_year['ชื่อ-สกุล']
        
        # If a person was selected previously, try to find them in the current year's list
        default_idx = 0
        if st.session_state.selected_hn:
             match = df_year[df_year['HN'].astype(str) == str(st.session_state.selected_hn)]
             if not match.empty:
                 # Find index in the dropdown
                 options = df_year['Search_Label'].tolist()
                 try:
                    default_idx = options.index(match.iloc[0]['Search_Label'])
                 except: pass

        selected_person_label = st.sidebar.selectbox(
            "🔍 Search Person",
            df_year['Search_Label'],
            index=default_idx
        )
        
        if selected_person_label:
            # Get selected row
            person_row = df_year[df_year['Search_Label'] == selected_person_label].iloc[0]
            st.session_state.selected_hn = person_row['HN'] # Update session state
            
            # --- Custom Header ---
            render_custom_header_with_actions(person_row, available_years)

            # --- Main Content Area ---
            tab1, tab2, tab3 = st.tabs(["📋 General Health", "👁️ Performance Tests", "🖨️ Printable Report"])
            
            with tab1:
                # 1. Vitals & Basic Labs (Cards Layout)
                st.markdown("#### Vital Signs")
                v1, v2, v3, v4 = st.columns(4)
                with v1: display_kpi_card("BMI", format_value(person_row.get('BMI')), "kg/m²")
                with v2: display_kpi_card("Blood Pressure", f"{format_value(person_row.get('SBP'), '')}/{format_value(person_row.get('DBP'), '')}", "mmHg")
                with v3: display_kpi_card("Fasting Sugar", format_value(person_row.get('FBS')), "mg/dL", "normal" if safe_float(person_row.get('FBS')) < 100 else "warning")
                with v4: display_kpi_card("Cholesterol", format_value(person_row.get('CHOL')), "mg/dL")

                st.markdown("#### Laboratory Results")
                # Create a clean dataframe for lab results
                lab_data = {
                    "Test": ["Hb", "WBC", "Platelet", "Creatinine", "Uric Acid", "SGOT", "SGPT"],
                    "Value": [
                        format_value(person_row.get('Hb(%)')),
                        format_value(person_row.get('WBC (cumm)')),
                        format_value(person_row.get('Plt (/mm)')),
                        format_value(person_row.get('Cr')),
                        format_value(person_row.get('Uric Acid')),
                        format_value(person_row.get('SGOT')),
                        format_value(person_row.get('SGPT'))
                    ],
                    "Reference": ["12-16", "4000-10000", "150000-450000", "0.5-1.2", "2.4-6.0", "<40", "<40"]
                }
                st.table(pd.DataFrame(lab_data))
                
                # History Chart (If toggled)
                if st.session_state.show_history:
                    st.markdown("### 📉 Historical Trends")
                    # Filter all data for this person across all years
                    person_history = df[df['HN'] == person_row['HN']].sort_values('Year')
                    render_history_chart(person_history)

            with tab2:
                render_performance_tests_summary(person_row, df)
            
            with tab3:
                st.info("Generating printable report...")
                
                # Filter history for charts in print view
                person_history = df[df['HN'] == person_row['HN']].sort_values('Year')
                
                # 1. Main Health Report
                html_report = generate_printable_report(person_row, person_history)
                
                # 2. Performance Report
                html_perf_report = generate_performance_report_html(person_row, person_history)
                
                c_print1, c_print2 = st.columns(2)
                
                with c_print1:
                    st.markdown("#### 📄 Main Health Report")
                    # Convert to base64 for download link
                    b64_report = base64.b64encode(html_report.encode()).decode()
                    href_report = f'<a href="data:text/html;base64,{b64_report}" download="Health_Report_{person_row["HN"]}.html" class="button-primary">Download Health Report (HTML)</a>'
                    st.markdown(href_report, unsafe_allow_html=True)
                    
                    # Preview (iframe)
                    st.components.v1.html(html_report, height=600, scrolling=True)

                with c_print2:
                    st.markdown("#### 👁️ Performance Report")
                    b64_perf = base64.b64encode(html_perf_report.encode()).decode()
                    href_perf = f'<a href="data:text/html;base64,{b64_perf}" download="Performance_Report_{person_row["HN"]}.html" class="button-primary">Download Performance Report (HTML)</a>'
                    st.markdown(href_perf, unsafe_allow_html=True)
                    
                    # Preview
                    st.components.v1.html(html_perf_report, height=600, scrolling=True)

    elif page == "Batch Print":
        render_batch_print_page(df_year, df) # Pass full df for history

    elif page == "Line Registration":
        render_line_registration_ui(df)

    elif page == "Admin Panel":
        render_admin_panel(df)


# --- Entry Point ---
if __name__ == "__main__":
    if not st.session_state.authenticated:
        # Login Screen
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.title("🏥 Health Data Analytics System")
            st.markdown("Please login to continue.")
            
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")
                
                if submit:
                    if check_password(username, password):
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.role = "admin" if username == "admin" else "user" # Simple role logic
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
    else:
        # Load Data
        df = load_data(DB_PATH)
        
        if df is None:
            st.warning("No data found in database. Please upload a file in the Admin Panel.")
            # Still show main app but with empty structure or redirect to admin if admin
            if st.session_state.role == 'admin':
                main_app(pd.DataFrame()) # Pass empty DF to handle UI structure
            else:
                 st.stop()
        else:
             main_app(df)
