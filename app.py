import streamlit as st
import sqlite3
import requests
import pandas as pd
import tempfile
import os
import json
from collections import OrderedDict
from datetime import datetime

# --- Import Authentication & Consent ---
from auth import authentication_flow, pdpa_consent_page

# --- Import CSV Saving Function ---
try:
    from line_register import save_new_user_to_csv, liff_initializer_component, check_if_user_registered, normalize_db_name_field
except ImportError:
    # Fallback function
    def save_new_user_to_csv(f, l, uid): return True, "Saved"
    def liff_initializer_component(): pass
    def check_if_user_registered(uid): return False, None
    def normalize_db_name_field(s): return s, ""

# --- Import Print Functions ---
try:
    from print_report import generate_printable_report
except Exception:
    def generate_printable_report(*args): return ""

try:
    from print_performance_report import generate_performance_report_html
except Exception:
    def generate_performance_report_html(*args): return ""

# --- Import Utils ---
try:
    from utils import (
        is_empty, has_basic_health_data, 
        has_vision_data, has_hearing_data, has_lung_data, has_visualization_data
    )
except Exception as e:
    st.error(f"Error loading utils: {e}")
    def is_empty(v): return pd.isna(v) or str(v).strip() == ""
    def has_basic_health_data(r): return True
    def has_vision_data(r): return False
    def has_hearing_data(r): return False
    def has_lung_data(r): return False
    def has_visualization_data(d): return False

# --- Import Visualization ---
try:
    from visualization import display_visualization_tab
except Exception:
    def display_visualization_tab(d, a): st.info("No visualization module")

# --- Import Shared UI (Main Display Logic) ---
# แก้ไข: Import display functions จาก shared_ui แทน admin_panel
try:
    from shared_ui import (
        inject_custom_css, 
        display_common_header,
        display_main_report, 
        display_performance_report
    )
except Exception as e:
    st.error(f"Critical Error loading shared_ui: {e}")
    def inject_custom_css(): pass
    def display_common_header(data): st.write(f"**รายงานผลสุขภาพ:** {data.get('ชื่อ-สกุล', '-')}")
    def display_main_report(p, a): st.error("Main Report Module Missing")
    def display_performance_report(p, t, a=None): pass

# --- Import Admin Panel ---
try:
    from admin_panel import display_admin_panel
except Exception:
    def display_admin_panel(df): st.error("Admin Panel Error")

# --- Data Loading ---
@st.cache_data(ttl=600)
def load_sqlite_data():
    tmp_path = None
    try:
        file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name
        conn = sqlite3.connect(tmp_path)
        df_loaded = pd.read_sql("SELECT * FROM health_data", conn)
        conn.close()
        df_loaded.columns = df_loaded.columns.str.strip()
        def clean_hn(hn_val):
            if pd.isna(hn_val): return ""
            s_val = str(hn_val).strip()
            return s_val[:-2] if s_val.endswith('.0') else s_val
        df_loaded['HN'] = df_loaded['HN'].apply(clean_hn)
        df_loaded['ชื่อ-สกุล'] = df_loaded['ชื่อ-สกุล'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
        df_loaded['เลขบัตรประชาชน'] = df_loaded['เลขบัตรประชาชน'].astype(str).str.strip()
        df_loaded['Year'] = df_loaded['Year'].astype(int)
        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].astype(str).str.strip().replace('nan', '')
        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)

# --- Main App Logic (แก้ใหม่ให้โหลดข้อมูลชัวร์ๆ) ---
def main_app(df):
    st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
    inject_custom_css()

    # --- Inject Custom CSS สำหรับปุ่ม Sidebar โดยเฉพาะ ---
    st.markdown("""
    <style>
        /* --- Sidebar Toggle Button Customization (Gemini Pro Edition) --- */
        
        /* 1. จัดการปุ่มหลัก: ดีไซน์วงกลม ทันสมัย */
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarExpandButton"] {
            background-color: white !important;
            border-radius: 50% !important; /* วงกลม */
            width: 36px !important;
            height: 36px !important;
            border: 1px solid #e0e0e0 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08) !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
            
            /* สำคัญ: ซ่อน text เดิมด้วยสีใส */
            color: transparent !important;
        }

        /* 2. บังคับซ่อนลูกทุกตัว (SVG, Text Nodes, Tooltips) */
        [data-testid="stSidebarCollapseButton"] > *,
        [data-testid="stSidebarExpandButton"] > * {
            display: none !important;
            width: 0 !important;
            height: 0 !important;
        }

        /* 3. Hover Effects: สีเขียวธีมหลัก */
        [data-testid="stSidebarCollapseButton"]:hover,
        [data-testid="stSidebarExpandButton"]:hover {
            background-color: #f1f8e9 !important; /* เขียวอ่อนจางๆ */
            border-color: #00B900 !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.12) !important;
            transform: scale(1.1) !important;
        }

        /* 4. สร้างไอคอนใหม่ด้วย ::after */
        [data-testid="stSidebarCollapseButton"]::after {
            content: "«" !important; /* Double Angle Quote Left */
            font-size: 22px !important;
            color: #00B900 !important;
            font-family: monospace, sans-serif !important;
            font-weight: bold !important;
            line-height: 1 !important;
            margin-top: -2px; /* Fine-tune center */
        }

        [data-testid="stSidebarExpandButton"]::after {
            content: "»" !important; /* Double Angle Quote Right */
            font-size: 22px !important;
            color: #00B900 !important;
            font-family: monospace, sans-serif !important;
            font-weight: bold !important;
            line-height: 1 !important;
            margin-top: -2px;
        }
        /* --- End Sidebar Customization --- */


        /* Styling เฉพาะปุ่ม Primary (พิมพ์รายงาน) ใน Sidebar - สีเขียวด้าน */
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {
            background-color: #1B5E20 !important; /* Dark Green Matte */
            color: #ffffff !important;
            border: none !important;
            padding: 10px 20px !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            border-radius: 8px !important; /* Rounded corners */
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
            transition: all 0.2s ease-in-out !important;
            letter-spacing: 0.5px !important;
            width: 100%;
            margin-bottom: 10px;
            position: relative;
            overflow: hidden;
        }
        
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]:hover {
            background-color: #2E7D32 !important; /* Slightly lighter on hover */
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3) !important;
        }
        
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]:active {
            background-color: #1B5E20 !important;
            transform: translateY(1px) !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2) !important;
        }

        /* Styling เฉพาะปุ่ม Secondary (ออกจากระบบ) ใน Sidebar - สีแดงด้าน */
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"] {
            background-color: #c62828 !important; /* Matte Dark Red */
            color: #ffffff !important;
            border: none !important;
            padding: 10px 20px !
