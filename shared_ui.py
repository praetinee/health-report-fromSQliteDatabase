import streamlit as st
import pandas as pd
import re
import html
import numpy as np
import textwrap
from collections import OrderedDict
from datetime import datetime
import json
import streamlit.components.v1 as components
import altair as alt

# --- Helper Functions ---
def is_empty(val):
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def normalize_name(name):
    if is_empty(name): return ""
    return re.sub(r'\s+', '', str(name).strip())

def get_float(col, person_data):
    try:
        val = person_data.get(col, "")
        if is_empty(val): return None
        return float(str(val).replace(",", "").strip())
    except: return None

def flag(val, low=None, high=None, higher_is_better=False):
    try:
        val = float(str(val).replace(",", "").strip())
    except: return "-", False
    formatted_val = f"{int(val):,}" if val == int(val) else f"{val:,.1f}"
    is_abnormal = False
    if higher_is_better:
        if low is not None and val < low: is_abnormal = True
    else:
        if low is not None and val < low: is_abnormal = True
        if high is not None and val > high: is_abnormal = True
    return formatted_val, is_abnormal

def clean_html_string(html_str):
    """
    ฟังก์ชันล้างช่องว่างนำหน้าบรรทัด (Indentation) และบรรทัดว่าง
    เพื่อให้ Streamlit Render HTML ได้อย่างถูกต้อง ไม่เพี้ยนเป็น Code Block
    การใช้ ' ' join แทน '' join เพื่อป้องกันคำติดกันเกินไปกรณีตัดบรรทัดในประโยค
    """
    if not html_str: return ""
    return " ".join([line.strip() for line in html_str.split('\n') if line.strip()])

def inject_keep_awake():
    js_code = """
    <script>
    (async () => {
        try {
            let wakeLock = null;
            const requestWakeLock = async () => {
                if ('wakeLock' in navigator) {
                    wakeLock = await navigator.wakeLock.request('screen');
                    console.log('✅ Wake Lock is active!');
                }
            };
            await requestWakeLock();
            document.addEventListener('visibilitychange', async () => {
                if (document.visibilityState === 'visible') await requestWakeLock();
            });
        } catch (err) { console.log('Wake Lock Error:', err); }
    })();
    </script>
    """
    components.html(js_code, height=0, width=0)

def inject_custom_css():
    """
    Inject CSS: Modern Luxury Medical Theme
    """
    css_content = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');
        
        :root {
            /* Theme Colors */
            --primary: #00695c;       /* Deep Teal */
            --primary-light: #e0f2f1;
            --secondary: #26a69a;
            --accent: #f9a825;        /* Muted Gold */
            
            /* Backgrounds */
            --bg-body: #f8f9fa;
            --card-bg: #ffffff;
            
            /* Text */
            --text-main: #37474f;
            --text-muted: #78909c;
            
            /* Status Colors */
            --status-normal-bg: #e8f5e9;
            --status-normal-text: #2e7d32;
            --status-warning-bg: #fff3e0;
            --status-warning-text: #ef6c00;
            --status-danger-bg: #ffebee;
            --status-danger-text: #c62828;
            --status-neutral-bg: #eceff1;
            --status-neutral-text: #546e7a;
            
            /* UI Elements */
            --radius-card: 16px;
            --radius-sm: 8px;
            --shadow-card: 0 4px 20px rgba(0, 0, 0, 0.05);
            --shadow-hover: 0 8px 25px rgba(0, 0, 0, 0.08);
        }

        html, body, [class*="st-"] {
            font-family: 'Sarabun', sans-serif !important;
            color: var(--text-main);
        }

        /* --- Global Layout --- */
        .block-container { padding-top: 2rem; padding-bottom: 4rem; }

        /* --- Tabs Styling --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: transparent;
            padding-bottom: 5px;
            border-bottom: 2px solid #f0f0f0;
        }
        .stTabs [data-baseweb="tab"] {
            height: auto;
            background-color: transparent;
            border-radius: 50px;
            padding: 8px 20px;
            color: var(--text-muted);
            font-weight: 600;
            border: 1px solid transparent;
            transition: all 0.2s ease;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: var(--primary);
            background-color: var(--primary-light);
        }
        .stTabs [aria-selected="true"] {
            background-color: var(--primary) !important;
            color: white !important;
            box-shadow: 0 4px 10px rgba(0,105,92,0.3);
        }
        .stTabs [data-baseweb="tab-border"] { display: none; }

        /* --- Section Header --- */
        .section-header-styled {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--primary);
            margin: 30px 0 15px 0;
            display: flex;
            align-items: center;
            gap: 12px;
            letter-spacing: -0.02em;
        }
        .section-header-styled::before {
            content: "";
            display: block;
            width: 6px;
            height: 24px;
            background: linear-gradient(180deg, var(--accent), var(--primary));
            border-radius: 4px;
        }

        /* --- Modern Cards --- */
        .card-container {
            background: var(--card-bg);
            border-radius: var(--radius-card);
            padding: 24px;
            box-shadow: var(--shadow-card);
            border: 1px solid rgba(0,0,0,0.02);
            margin-bottom: 20px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .card-container:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-hover);
        }

        /* --- Tables --- */
        .table-title {
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 12px;
            font-size: 1rem;
            border-bottom: 2px solid var(--primary-light);
            padding-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .table-responsive { width: 100%; overflow-x: auto; }
        .lab-table, .info-detail-table { 
            width: 100%; min-width: 300px; 
            border-collapse: separate; 
            border-spacing: 0;
            font-size: 0.95rem; 
        }
        .lab-table th, .info-detail-table th {
            background-color: #f1f8e9;
            color: var(--primary);
            font-weight: 700;
            padding: 12px 15px;
            text-align: left;
            border-bottom: 2px solid #c5e1a5;
        }
        .lab-table td, .info-detail-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #f0f0f0;
            vertical-align: middle;
            color: var(--text-main);
        }
        .lab-table tr:last-child td { border-bottom: none; }
        
        .abnormal-row { background-color: #fff9f9 !important; }
        .text-danger { color: var(--status-danger-text) !important; font-weight: 700; }

        /* --- Header Profile --- */
        .report-header-container {
            background: white;
            border-radius: var(--radius-card);
            padding: 24px;
            box-shadow: var(--shadow-card);
            margin-bottom: 25px;
            border-left: 6px solid var(--primary);
            background-image: linear-gradient(to right, #ffffff, #fdfdfd);
        }
        .header-main { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 20px; }
        .patient-profile { display: flex; gap: 15px; align-items: center; flex: 1 1 300px; }
        .profile-icon {
            width: 64px; height: 64px;
            background: linear-gradient(135deg, var(--primary-light), white);
            color: var(--primary);
            border-radius: 20px;
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
            font-size: 1.5rem;
        }
        .patient-name { font-size: 1.4rem; font-weight: 800; color: var(--text-main); margin-bottom: 2px; }
        .patient-meta { font-size: 0.9rem; color: var(--text-muted); font-weight: 500; }
        .patient-dept {
            background: #f5f5f5; color: var(--text-main);
            padding: 4px 10px; border-radius: 6px;
            font-size: 0.8rem; font-weight: 600; display: inline-block; margin-top: 6px;
        }
        .report-meta { text-align: right; flex: 1 1 200px; }
        .hospital-brand .hosp-name { font-weight: 800; color: var(--primary); font-size: 1.1rem; }

        /* --- Vitals Cards --- */
        .vitals-grid-container {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px;
        }
        .vital-card {
            background: white; border-radius: var(--radius-card); padding: 18px;
            box-shadow: var(--shadow-card);
            border: 1px solid #f0f0f0;
            display: flex; align-items: center; gap: 15px;
            transition: all 0.2s;
        }
        .vital-card:hover { transform: translateY(-3px); border-color: var(--primary-light); }
        .vital-icon-box {
            width: 48px; height: 48px; border-radius: 14px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.2rem;
            flex-shrink: 0;
        }
        .bg-blue-light { background: #e1f5fe; color: #0277bd; }
        .bg-green-light { background: #e8f5e9; color: #2e7d32; }
        .bg-red-light { background: #ffebee; color: #c62828; }
        .bg-orange-light { background: #fff3e0; color: #ef6c00; }
        
        .vital-content { flex-grow: 1; }
        .vital-value { font-size: 1.2rem; font-weight: 800; color: var(--text-main); line-height: 1.2; }
        .vital-label { font-size: 0.8rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
        .vital-sub { font-size: 0.8rem; color: var(--text-muted); margin-top: 2px; }

        /* --- Result Cards (Modern) --- */
        .result-card-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;
        }
        .result-card {
            background: white; border-radius: var(--radius-card); padding: 20px;
            box-shadow: var(--shadow-card); border: 1px solid #f0f0f0;
            position: relative; overflow: hidden;
        }
        .result-card::before {
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 5px;
            background: linear-gradient(90deg, var(--primary), var(--accent));
        }
        .res-header {
            display: flex; align-items: center; gap: 12px; margin-bottom: 15px;
            border-bottom: 1px solid #f5f5f5; padding-bottom: 10px;
        }
        .res-icon {
            width: 40px; height: 40px; border-radius: 12px;
            display: flex; align-items: center; justify-content: center; font-size: 1.2rem;
            background: #f2f2f2; color: #555;
        }
        .res-title { font-weight: 700; font-size: 1.1rem; color: var(--text-main); }
        .res-status-badge {
            display: inline-flex; align-items: center; padding: 6px 12px;
            border-radius: 50px; font-size: 0.9rem; font-weight: 700;
            margin-bottom: 12px;
        }
        .badge-normal { background: var(--status-normal-bg); color: var(--status-normal-text); border: 1px solid rgba(46, 125, 50, 0.2); }
        .badge-abnormal { background: var(--status-danger-bg); color: var(--status-danger-text); border: 1px solid rgba(198, 40, 40, 0.2); }
        .badge-warning { background: var(--status-warning-bg); color: var(--status-warning-text); border: 1px solid rgba(239, 108, 0, 0.2); }
        .badge-neutral { background: var(--status-neutral-bg); color: var(--status-neutral-text); }

        .res-detail-row {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 8px; padding: 10px;
            background-color: #fafafa; border-radius: 10px;
            font-size: 0.9rem;
        }
        .res-detail-label { color: var(--text-muted); font-weight: 500; display: flex; align-items: center; gap: 6px; }
        .res-detail-value { font-weight: 700; color: var(--text-main); }

        /* --- Advice Box --- */
        .advice-box-styled {
            background-color: #fffde7; 
            border: 1px solid #fff59d;
            border-left: 5px solid #fbc02d;
            padding: 16px 20px; 
            border-radius: 12px;
            color: #5d4037; font-size: 0.95rem; line-height: 1.6;
            margin-top: 15px;
            display: flex; gap: 15px; align-items: flex-start;
        }
        .advice-icon { font-size: 1.5rem; flex-shrink: 0; margin-top: -2px; }

        @media (max-width: 768px) {
            .header-main { flex-direction: column; }
            .report-meta { text-align: left; margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee; }
            .vitals-grid-container { grid-template-columns: 1fr 1fr; }
        }
        @media (max-width: 480px) {
            .vitals-grid-container { grid-template-columns: 1fr; }
        }
    </style>
    """
    st.markdown(clean_html_string(css_content), unsafe_allow_html=True)

def render_section_header(title):
    st.markdown(clean_html_string(f"""<div class="section-header-styled">{title}</div>"""), unsafe_allow_html=True)

def render_lab_table_html(title, headers, rows, table_class="lab-table"):
    header_html = f"<div class='table-title'>{title}</div>"
    thead = "<thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i in [0, 2] else "center"
        thead += f"<th style='text-align: {align};'>{h}</th>"
    thead += "</tr></thead>"
    tbody = "<tbody>"
    for row in rows:
        is_row_abnormal = any(item[1] for item in row)
        row_class = "abnormal-row" if is_row_abnormal else ""
        tbody += f"<tr class='{row_class}'>"
        tbody += f"<td style='text-align: left; font-weight: 500;'>{row[0][0]}</td>"
        val_class = "text-danger" if row[1][1] else ""
        tbody += f"<td class='{val_class}' style='text-align: center; font-weight: bold;'>{row[1][0]}</td>"
        tbody += f"<td style='text-align: left; opacity: 0.8;'>{row[2][0]}</td>"
        tbody += "</tr>"
    tbody += "</tbody>"
    
    html_content = clean_html_string(f"""
    <div class="card-container">
        {header_html}
        <div class='table-responsive'>
            <table class='{table_class}'>
                <colgroup><col style='width:40%;'><col style='width:20%;'><col style='width:40%;'></colgroup>
                {thead}{tbody}
            </table>
        </div>
    </div>""")
    return html_content

def safe_text(val): return "-" if str(val).strip().lower() in ["", "none", "nan", "-"] else str(val).strip()
def safe_value(val):
    val = str(val or "").strip()
    return "-" if val.lower() in ["", "nan", "none", "-"] else val

def parse_range_or_number(val):
    val = val.replace("cell/hpf", "").replace("cells/hpf", "").replace("cell", "").strip().lower()
    try:
        if "-" in val: return map(float, val.split("-"))
        else: num = float(val); return num, num
    except: return None, None

def interpret_rbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]: return "-"
    _, high = parse_range_or_number(val)
    if high is None: return value
    if high <= 2: return "ปกติ"
    if high <= 5: return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
    return "พบเม็ดเลือดแดงในปัสสาวะ"

def interpret_wbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]: return "-"
    _, high = parse_range_or_number(val)
    if high is None: return value
    if high <= 5: return "ปกติ"
    if high <= 10: return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    return "พบเม็ดเลือดขาวในปัสสาวะ"

def is_urine_abnormal(test_name, value, normal_range):
    val = str(value or "").strip().lower()
    if val in ["", "-", "none", "nan", "null"]: return False
    if test_name == "กรด-ด่าง (pH)":
        try: return not (5.0 <= float(val) <= 8.0)
        except: return True
    if test_name == "ความถ่วงจำเพาะ (Sp.gr)":
        try: return not (1.003 <= float(val) <= 1.030)
        except: return True
    if test_name == "เม็ดเลือดแดง (RBC)": return "พบ" in interpret_rbc(val).lower()
    if test_name == "เม็ดเลือดขาว (WBC)": return "พบ" in interpret_wbc(val).lower()
    if test_name == "น้ำตาล (Sugar)": return val.lower() not in ["negative"]
    if test_name == "โปรตีน (Albumin)": return val.lower() not in ["negative", "trace"]
    if test_name == "สี (Colour)": return val not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"]
    return False

def interpret_stool_exam(val):
    if is_empty(val): return "ไม่ได้ตรวจ"
    val_lower = str(val).strip().lower()
    if val_lower == "normal": return "ไม่พบเม็ดเลือดขาวในอุจจาระ ถือว่าปกติ"
    if "wbc" in val_lower or "เม็ดเลือดขาว" in val_lower: return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
    return val

def interpret_stool_cs(value):
    if is_empty(value): return "ไม่ได้ตรวจ"
    val_strip = str(value).strip()
    if "ไม่พบ" in val_strip or "ปกติ" in val_strip: return "ไม่พบการติดเชื้อ"
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"

def get_ekg_col_name(year):
    current_thai_year = datetime.now().year + 543
    return "EKG" if year == current_thai_year else f"EKG{str(year)[-2:]}"

def interpret_ekg(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้ตรวจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]): return f"<span class='text-danger'>{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม</span>"
    return val

def hepatitis_b_advice(hbsag, hbsab, hbcab):
    hbsag, hbsab, hbcab = str(hbsag).lower(), str(hbsab).lower(), str(hbcab).lower()
    if "positive" in hbsag: return "ติดเชื้อไวรัสตับอักเสบบี", "infection"
    if "positive" in hbsab and "positive" not in hbsag: return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี", "immune"
    if "positive" in hbcab and "positive" not in hbsab: return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน", "unclear"
    if all(x == "negative" for x in [hbsag, hbsab, hbcab]): return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน", "no_immune"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ", "unclear"

def interpret_bp(sbp, dbp):
    try:
        sbp, dbp = float(sbp), float(dbp)
        if sbp == 0 or dbp == 0: return "-"
        if sbp >= 160 or dbp >= 100: return "ความดันสูง"
        if sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
        if sbp < 120 and dbp < 80: return "ความดันปกติ"
        return "ความดันค่อนข้างสูง"
    except: return "-"

def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้ตรวจ"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]): return f"<span class='text-danger'>{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม</span>"
    return val

def interpret_bmi(bmi):
    if bmi is None: return ""
    if bmi < 18.5: return "น้ำหนักน้อยกว่าเกณฑ์"
    elif 18.5 <= bmi < 23: return "น้ำหนักปกติ"
    elif 23 <= bmi < 25: return "น้ำหนักเกิน (ท้วม)"
    elif 25 <= bmi < 30: return "เข้าเกณฑ์โรคอ้วน"
    elif bmi >= 30: return "เข้าเกณฑ์โรคอ้วนอันตราย"
    return ""

def display_common_header(person_data):
    name = person_data.get('ชื่อ-สกุล', '-')
    age = str(int(float(person_data.get('อายุ')))) if str(person_data.get('อายุ')).replace('.', '', 1).isdigit() else person_data.get('อายุ', '-')
    sex = person_data.get('เพศ', '-')
    hn = str(int(float(person_data.get('HN')))) if str(person_data.get('HN')).replace('.', '', 1).isdigit() else person_data.get('HN', '-')
    department = person_data.get('หน่วยงาน', '-')
    check_date = person_data.get("วันที่ตรวจ", "-")
    
    # คำนวณค่าต่างๆ
    try:
        sbp_int, dbp_int = int(float(person_data.get("SBP", ""))), int(float(person_data.get("DBP", "")))
        bp_val = f"{sbp_int}/{dbp_int}"
        bp_desc = interpret_bp(sbp_int, dbp_int)
    except:
        bp_val = "-"
        bp_desc = "ไม่มีข้อมูล"
    try: pulse_val = f"{int(float(person_data.get('pulse', '-')))}"
    except: pulse_val = "-"
    weight = get_float('น้ำหนัก', person_data)
    height = get_float('ส่วนสูง', person_data)
    weight_val = f"{weight}" if weight is not None else "-"
    height_val = f"{height}" if height is not None else "-"
    waist_val = f"{person_data.get('รอบเอว', '-')}"
    bmi_val_str = "-"
    bmi_desc = ""
    if weight is not None and height is not None and height > 0:
        bmi = weight / ((height / 100) ** 2)
        bmi_val_str = f"{bmi:.1f}"
        bmi_desc = interpret_bmi(bmi)

    icon_profile = """<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>"""
    icon_body = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>"""
    icon_waist = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M8 12h8"></path></svg>"""
    icon_heart = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>"""
    icon_pulse = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>"""

    html_content = clean_html_string(f"""
    <div class="report-header-container">
        <div class="header-main">
            <div class="patient-profile">
                <div class="profile-icon">{icon_profile}</div>
                <div class="profile-details">
                    <div class="patient-name">{name}</div>
                    <div class="patient-meta"><span>HN: {hn}</span> | <span>เพศ: {sex}</span> | <span>อายุ: {age} ปี</span></div>
                    <div class="patient-dept">หน่วยงาน: {department}</div>
                </div>
            </div>
            <div class="report-meta">
                <div class="meta-date">วันที่ตรวจ: {check_date}</div>
                <div class="hospital-brand">
                    <div class="hosp-name">คลินิกตรวจสุขภาพ</div>
                    <div class="hosp-dept">อาชีวเวชกรรม</div>
                    <div class="hosp-sub">รพ.สันทราย</div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="vitals-grid-container">
        <div class="vital-card">
            <div class="vital-icon-box bg-blue-light">{icon_body}</div>
            <div class="vital-content">
                <div class="vital-label">สัดส่วนร่างกาย</div>
                <div class="vital-value">{weight_val} <span class="unit">kg</span> / {height_val} <span class="unit">cm</span></div>
                <div class="vital-sub">BMI: {bmi_val_str} ({bmi_desc})</div>
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon-box bg-green-light">{icon_waist}</div>
            <div class="vital-content">
                <div class="vital-label">รอบเอว</div>
                <div class="vital-value">{waist_val} <span class="unit">cm</span></div>
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon-box bg-red-light">{icon_heart}</div>
            <div class="vital-content">
                <div class="vital-label">ความดันโลหิต</div>
                <div class="vital-value">{bp_val} <span class="unit">mmHg</span></div>
                <div class="vital-sub">{bp_desc}</div>
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon-box bg-orange-light">{icon_pulse}</div>
            <div class="vital-content">
                <div class="vital-label">ชีพจร</div>
                <div class="vital-value">{pulse_val} <span class="unit">bpm</span></div>
            </div>
        </div>
    </div>
    """)
    st.markdown(html_content, unsafe_allow_html=True)

def render_vision_details_table(person_data):
    vision_config = [
        {'id': 'V_Binocular_Far', 'label': '1. การมองด้วย 2 ตา (Binocular vision)', 'keys': ['ป.การรวมภาพ', 'ผ.การรวมภาพ', 'Binocular', 'Binocular Vision']},
        {'id': 'V_Both_Far', 'label': '2. ความชัดระยะไกล - สองตา (Far vision - Both)', 'keys': ['ป.ความชัดของภาพระยะไกล', 'ผ.ความชัดของภาพระยะไกล', 'Far Both', 'V_Both_Far']},
        {'id': 'V_R_Far', 'label': '3. ความชัดระยะไกล - ตาขวา (Far vision - Right)', 'keys': ['V_R_Far', 'R_Far', 'Right Far', 'Far Vision Right', 'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)', 'R-Far']},
        {'id': 'V_L_Far', 'label': '4. ความชัดระยะไกล - ตาซ้าย (Far vision - Left)', 'keys': ['V_L_Far', 'L_Far', 'Left Far', 'Far Vision Left', 'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)', 'L-Far']},
        {'id': 'Stereo', 'label': '5. การมองภาพ 3 มิติ (Stereo depth)', 'keys': ['ป.การกะระยะและมองความชัดลึกของภาพ', 'ผ.การกะระยะและมองความชัดลึกของภาพ', 'Stereo', 'Stereopsis']},
        {'id': 'Color_Blind', 'label': '6. การจำแนกสี (Color discrimination)', 'keys': ['Color_Blind', 'ColorBlind', 'Ishihara', 'Color', 'ตาบอดสี', 'ป.การจำแนกสี', 'ผ.การจำแนกสี']},
        {'id': 'Phoria_V_Far', 'label': '7. สมดุลกล้ามเนื้อตาแนวดิ่ง (Far vertical phoria)', 'keys': ['ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง', 'Far Vertical Phoria', 'Phoria V Far']},
        {'id': 'Phoria_H_Far', 'label': '8. สมดุลกล้ามเนื้อตาแนวนอน (Far lateral phoria)', 'keys': ['ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน', 'Far Lateral Phoria', 'Phoria H Far']},
        {'id': 'V_Both_Near', 'label': '9. ความชัดระยะใกล้ - สองตา (Near vision - Both)', 'keys': ['ป.ความชัดของภาพระยะใกล้', 'ผ.ความชัดของภาพระยะใกล้', 'Near Both', 'V_Both_Near']},
        {'id': 'V_R_Near', 'label': '10. ความชัดระยะใกล้ - ตาขวา (Near vision - Right)', 'keys': ['V_R_Near', 'R_Near', 'Right Near', 'Near Vision Right', 'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)', 'R-Near']},
        {'id': 'V_L_Near', 'label': '11. ความชัดระยะใกล้ - ตาซ้าย (Near vision - Left)', 'keys': ['V_L_Near', 'L_Near', 'Left Near', 'Near Vision Left', 'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)', 'L-Near']},
        {'id': 'Phoria_H_Near', 'label': '12. สมดุลกล้ามเนื้อตาแนวนอน-ใกล้ (Near lateral phoria)', 'keys': ['ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน', 'Near Lateral Phoria', 'Phoria H Near']},
        {'id': 'Visual_Field', 'label': '13. ลานสายตา (Visual field)', 'keys': ['ป.ลานสายตา', 'ผ.ลานสายตา', 'Visual Field', 'Perimetry']}
    ]
    
    def check_vision(val, test_type):
        if is_empty(val): return "-", "vision-not-tested", "badge-neutral"
        val_str = str(val).strip().lower()
        normal_keywords = ['normal', 'ปกติ', 'pass', 'ผ่าน', 'within normal', 'no', 'none', 'ortho', 'orthophoria', 'clear', 'ok', 'good', 'binocular', '6/6', '20/20']
        warning_keywords = ['mild', 'slight', 'เล็กน้อย', 'trace', 'low', 'ต่ำ', 'below', 'drop']
        abnormal_keywords = ['abnormal', 'ผิดปกติ', 'fail', 'ไม่ผ่าน', 'detect', 'found', 'พบ', 'deficiency', 'color blind', 'blind', 'eso', 'exo', 'hyper', 'hypo']
        
        if val_str in normal_keywords: return "ปกติ", "vision-result vision-normal", "badge-normal"
        if any(kw in val_str for kw in abnormal_keywords):
            if any(kw in val_str for kw in warning_keywords): return "ต่ำกว่าเกณฑ์", "vision-result vision-warning", "badge-warning"
            return "ผิดปกติ", "vision-result vision-abnormal", "badge-abnormal"
        if any(kw in val_str for kw in warning_keywords): return "ต่ำกว่าเกณฑ์", "vision-result vision-warning", "badge-warning"
        if re.match(r'^\d+/\d+$', val_str): return str(val), "vision-result vision-normal", "badge-normal"
        return str(val), "vision-result vision-normal", "badge-normal"

    html_rows = ""
    any_data_found = False
    for item in vision_config:
        val = None
        for key in item['keys']:
            if not is_empty(person_data.get(key)):
                val = person_data.get(key)
                any_data_found = True
                break
        res_text, _, res_badge = check_vision(val, item['id'])
        html_rows += f"<tr><td>{item['label']}</td><td class='result-cell' style='text-align:center;'><span class='res-status-badge {res_badge}' style='margin-bottom:0;'>{res_text}</span></td></tr>"
    
    doctor_advice = person_data.get('แนะนำABN EYE', '')
    summary_advice = person_data.get('สรุปเหมาะสมกับงาน', '')
    footer_html = ""
    if not is_empty(summary_advice) or not is_empty(doctor_advice):
        footer_html = "<div class='advice-box-styled'><div class='advice-icon'>💡</div><div>"
        if not is_empty(summary_advice): footer_html += f"<b>สรุป:</b> {summary_advice}<br>"
        if not is_empty(doctor_advice): footer_html += f"<b>คำแนะนำ:</b> {doctor_advice}"
        footer_html += "</div></div>"
        
    html_content = clean_html_string(f"""
    <div class='card-container'>
        <div class='table-title'>ผลการตรวจสมรรถภาพการมองเห็น (Vision Test)</div>
        <div class='table-responsive'>
            <table class='lab-table'>
                <thead><tr><th>รายการทดสอบ</th><th style='text-align: center; width: 150px;'>ผลการตรวจ</th></tr></thead>
                <tbody>{html_rows}</tbody>
            </table>
        </div>
        {footer_html}
    </div>""")
    
    if any_data_found: st.markdown(html_content, unsafe_allow_html=True)
    else: st.info("ไม่พบข้อมูลการตรวจสายตา")

def display_performance_report_vision(person_data):
    render_vision_details_table(person_data)

def display_performance_report_hearing(person_data, all_person_history_df):
    from performance_tests import interpret_audiogram
    results = interpret_audiogram(person_data, all_person_history_df)
    
    # --- Audiogram Graph using Altair ---
    freq_map = {'250 Hz': 250, '500 Hz': 500, '1000 Hz': 1000, '2000 Hz': 2000, '3000 Hz': 3000, '4000 Hz': 4000, '6000 Hz': 6000, '8000 Hz': 8000}
    chart_data = []
    all_freqs = ['250 Hz', '500 Hz', '1000 Hz', '2000 Hz', '3000 Hz', '4000 Hz', '6000 Hz', '8000 Hz']
    
    for freq_str in all_freqs:
        freq_num = freq_map[freq_str]
        r_val = None
        l_val = None
        if freq_str in results['raw_values']:
            r_val = results['raw_values'][freq_str]['right']
            l_val = results['raw_values'][freq_str]['left']
        else:
            suffix = str(freq_num)
            if freq_num >= 1000: suffix = f"{freq_num//1000}k"
            r_keys = [f"R{suffix}", f"R_{suffix}", f"R{suffix}Hz"]
            l_keys = [f"L{suffix}", f"L_{suffix}", f"L{suffix}Hz"]
            for k in r_keys:
                if not is_empty(person_data.get(k)): 
                    try: r_val = int(float(person_data.get(k))); break
                    except: pass
            for k in l_keys:
                if not is_empty(person_data.get(k)): 
                    try: l_val = int(float(person_data.get(k))); break
                    except: pass

        if r_val is not None: chart_data.append({'Frequency': freq_num, 'dB': r_val, 'Ear': 'Right (หูขวา)'})
        if l_val is not None: chart_data.append({'Frequency': freq_num, 'dB': l_val, 'Ear': 'Left (หูซ้าย)'})

    if chart_data:
        df_chart = pd.DataFrame(chart_data)
        x_domain = [125, 8500] 
        y_domain = [-10, 100]
        
        # Green Zone (Normal Hearing)
        normal_band = alt.Chart(pd.DataFrame({'y': [-10], 'y2': [25]})).mark_rect(
            color='#4CAF50', opacity=0.1
        ).encode(y='y', y2='y2')

        base = alt.Chart(df_chart).encode(
            x=alt.X('Frequency:Q', scale=alt.Scale(type='log', domain=x_domain), title='ความถี่ (Hz)'),
            y=alt.Y('dB:Q', scale=alt.Scale(domain=y_domain, reverse=True), title='ระดับการได้ยิน (dB)'),
            color=alt.Color('Ear:N', scale=alt.Scale(domain=['Right (หูขวา)', 'Left (หูซ้าย)'], range=['#ef5350', '#42a5f5']), legend=alt.Legend(title="ข้างที่ตรวจ")),
            tooltip=['Ear', 'Frequency', 'dB']
        )
        lines = base.mark_line(point=True).encode(shape=alt.Shape('Ear:N', scale=alt.Scale(domain=['Right (หูขวา)', 'Left (หูซ้าย)'], range=['circle', 'cross'])))
        rule = alt.Chart(pd.DataFrame({'y': [25]})).mark_rule(color='green', strokeDash=[5, 5]).encode(y='y')
        final_chart = (normal_band + rule + lines).properties(title="กราฟแสดงผลการตรวจการได้ยิน (Audiogram) [โซนสีเขียว = ปกติ]", height=350).interactive()
        st.altair_chart(final_chart, use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลกราฟการได้ยิน")

    # --- Modern Result Cards ---
    def get_status_props(text):
        txt = str(text)
        if "ปกติ" in txt: return "badge-normal", "ปกติ"
        if "ผิดปกติ" in txt or "เสื่อม" in txt: return "badge-abnormal", "ผิดปกติ"
        if "N/A" in txt or "ไม่ได้ตรวจ" in txt: return "badge-neutral", "ไม่ได้ตรวจ"
        return "badge-warning", txt

    def fmt_db(val):
        if val is None: return "-"
        try: return f"{float(val):.1f} dB"
        except: return str(val)

    r_cls, r_txt = get_status_props(results['summary']['right'])
    l_cls, l_txt = get_status_props(results['summary']['left'])

    # *** FIX RAW CODE ISSUE: Ensure pure HTML string without indentation issues ***
    html_cards = clean_html_string(f"""
    <div class="result-card-grid">
        <!-- Right Ear -->
        <div class="result-card">
            <div class="res-header">
                <div class="res-icon" style="background:#e3f2fd; color:#1565c0;">👂</div>
                <div class="res-title">หูขวา (Right Ear)</div>
            </div>
            <div class="res-status-badge {r_cls}">{r_txt}</div>
            <div class="res-detail-row">
                <span class="res-detail-label">🗣️ เสียงพูด (500-2k Hz)</span>
                <span class="res-detail-value">{fmt_db(results['averages']['right_500_2000'])}</span>
            </div>
            <div class="res-detail-row">
                <span class="res-detail-label">🔔 เสียงสูง (3k-6k Hz)</span>
                <span class="res-detail-value">{fmt_db(results['averages']['right_3000_6000'])}</span>
            </div>
        </div>

        <!-- Left Ear -->
        <div class="result-card">
            <div class="res-header">
                <div class="res-icon" style="background:#f3e5f5; color:#7b1fa2;">👂</div>
                <div class="res-title">หูซ้าย (Left Ear)</div>
            </div>
            <div class="res-status-badge {l_cls}">{l_txt}</div>
            <div class="res-detail-row">
                <span class="res-detail-label">🗣️ เสียงพูด (500-2k Hz)</span>
                <span class="res-detail-value">{fmt_db(results['averages']['left_500_2000'])}</span>
            </div>
            <div class="res-detail-row">
                <span class="res-detail-label">🔔 เสียงสูง (3k-6k Hz)</span>
                <span class="res-detail-value">{fmt_db(results['averages']['left_3000_6000'])}</span>
            </div>
        </div>
    </div>
    """)
    st.markdown(html_cards, unsafe_allow_html=True)

    # Advice
    advice = results.get('advice', '')
    if advice and advice != 'ไม่มีคำแนะนำเพิ่มเติม':
        st.markdown(clean_html_string(f"""
        <div class="advice-box-styled">
            <div class="advice-icon">💡</div>
            <div>
                <div style="font-weight:700; margin-bottom:4px;">คำแนะนำจากแพทย์</div>
                {advice}
            </div>
        </div>
        """), unsafe_allow_html=True)

def display_performance_report_lung(person_data):
    from performance_tests import interpret_lung_capacity
    summary, advice, raw_data = interpret_lung_capacity(person_data)
    
    st.markdown(clean_html_string("""
    <div class="vitals-grid-container" style="grid-template-columns: 1fr 1fr;">
        <div class="vital-card">
            <div class="vital-icon-box bg-blue-light">🫁</div>
            <div class="vital-content">
                <div class="vital-label">FVC (ความจุปอด)</div>
                <div class="vital-sub">ปริมาตรอากาศที่เป่าออกเต็มที่</div>
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon-box bg-green-light">💨</div>
            <div class="vital-content">
                <div class="vital-label">FEV1 (ลมเป่าเร็ว)</div>
                <div class="vital-sub">ปริมาตรอากาศเป่าออกใน 1 วินาที</div>
            </div>
        </div>
    </div>
    """), unsafe_allow_html=True)

    lung_items = [("FVC (ความจุปอด)", raw_data['FVC predic'], raw_data['FVC'], raw_data['FVC %']), ("FEV1 (ปริมาตรลมเป่าเร็ว)", raw_data['FEV1 predic'], raw_data['FEV1'], raw_data['FEV1 %']), ("FEV1/FVC Ratio (สัดส่วน)", "-", raw_data['FEV1/FVC %'], "-")]
    
    def make_bar(val):
        try:
            v = float(str(val).replace('%','').strip())
            color = "#2e7d32" if v >= 80 else "#ef6c00" if v >= 60 else "#c62828"
            return f"<div style='background:#eee;height:8px;border-radius:4px;width:80px;display:inline-block;vertical-align:middle;margin-right:8px;'><div style='width:{min(v,100)}%;background:{color};height:100%;border-radius:4px;'></div></div> {v}%"
        except: return str(val)

    rows_html = ""
    for label, pred, act, per in lung_items:
        display_per = make_bar(per) if per != "-" else "-"
        rows_html += f"<tr><td>{label}</td><td style='text-align:center;'>{pred}</td><td style='text-align:center;'>{act}</td><td>{display_per}</td></tr>"

    st.markdown(clean_html_string(f"""
    <div class='card-container'>
        <div class='table-title'>ผลการตรวจสมรรถภาพปอด (Spirometry)</div>
        <div class='table-responsive'>
            <table class='lab-table'>
                <thead><tr><th style='width: 30%;'>รายการ</th><th style='text-align: center;'>ค่ามาตรฐาน</th><th style='text-align: center;'>ค่าที่วัดได้</th><th style='width: 35%;'>ผลเทียบมาตรฐาน (%)</th></tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
        <div class="advice-box-styled" style="margin-top:20px; border-left-color: var(--primary);">
            <div class="advice-icon">📋</div>
            <div>
                <div style="font-weight:700;">สรุปผลการตรวจ</div>
                {summary}
                <div style="margin-top:5px; font-size:0.9rem; color:#666;">{advice}</div>
            </div>
        </div>
    </div>
    """), unsafe_allow_html=True)

def display_performance_report(person_data, report_type, all_person_history_df=None):
    if report_type == 'lung':
        render_section_header("ผลตรวจสมรรถภาพปอด (Lung Function Test)")
        display_performance_report_lung(person_data)
    elif report_type == 'vision':
        render_section_header("ผลตรวจการมองเห็น (Vision Test)")
        display_performance_report_vision(person_data)
    elif report_type == 'hearing':
        render_section_header("ผลตรวจการได้ยิน (Audiometry)")
        display_performance_report_hearing(person_data, all_person_history_df)

def render_urine_section(person_data, sex, year):
    urine_config = [("สี (Colour)", "Color", "Yellow"), ("น้ำตาล (Sugar)", "sugar", "Negative"), ("โปรตีน (Albumin)", "Alb", "Negative"), ("กรด-ด่าง (pH)", "pH", "5.0 - 8.0"), ("ความถ่วงจำเพาะ (Sp.gr)", "Spgr", "1.003 - 1.030"), ("เม็ดเลือดแดง (RBC)", "RBC1", "0 - 2"), ("เม็ดเลือดขาว (WBC)", "WBC1", "0 - 5"), ("เซลล์เยื่อบุผิว (Epit)", "SQ-epi", "0 - 10"), ("อื่นๆ", "ORTER", "-")]
    rows = []
    for label, col, norm in urine_config:
        val = person_data.get(col)
        is_abn = is_urine_abnormal(label, val, norm)
        rows.append([(label, is_abn), (safe_value(val), is_abn), (norm, is_abn)])
    st.markdown(render_lab_table_html("ผลการตรวจปัสสาวะ (Urinalysis)", ["รายการ", "ผลตรวจ", "ค่าปกติ"], rows), unsafe_allow_html=True)

def render_stool_html_table(exam_result, cs_result):
    return render_lab_table_html("ผลการตรวจอุจจาระ (Stool Examination)", ["รายการ", "ผลตรวจ"], [[("Stool Examination", False), (exam_result, False)], [("Stool Culture", False), (cs_result, False)]])

def display_main_report(person_data, all_person_history_df):
    person = person_data
    sex = str(person.get("เพศ", "")).strip()
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_config = [("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None), ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None), ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000), ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70), ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44), ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9), ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9), ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3), ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000)]
    cbc_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high in cbc_config for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high)]]

    blood_config = [("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106), ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2), ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120), ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37), ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41), ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200), ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150), ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True), ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160), ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20), ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17), ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True)]
    blood_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high, *opt in blood_config for higher in [opt[0] if opt else False] for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high, higher)]]

    with st.container():
        render_section_header("ผลการตรวจทางห้องปฏิบัติการ (Laboratory Results)")
        col1, col2 = st.columns(2)
        with col1: st.markdown(render_lab_table_html("ผลตรวจความสมบูรณ์ของเม็ดเลือด (CBC)", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
        with col2: st.markdown(render_lab_table_html("ผลตรวจเลือด (Blood Chemistry)", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

    selected_year = person.get("Year", datetime.now().year + 543)

    with st.container():
        render_section_header("ผลการตรวจอื่นๆ (Other Examinations)")
        col_ua_left, col_ua_right = st.columns(2)
        with col_ua_left:
            render_urine_section(person, sex, selected_year)
            st.markdown(render_stool_html_table(interpret_stool_exam(person.get("Stool exam", "")), interpret_stool_cs(person.get("Stool C/S", ""))), unsafe_allow_html=True)

        with col_ua_right:
            # Special Exams Table
            cxr_val = person.get("CXR")
            if is_empty(cxr_val):
                cxr_col = f"CXR{str(selected_year)[-2:]}"
                cxr_val = person.get(cxr_col)
            ekg_val = person.get("EKG")
            if is_empty(ekg_val):
                ekg_col = f"EKG{str(selected_year)[-2:]}"
                ekg_val = person.get(ekg_col)
            hep_a_val = person.get("Hepatitis A")
            if is_empty(hep_a_val):
                hep_a_col = f"Hepatitis A{str(selected_year)[-2:]}"
                hep_a_val = person.get(hep_a_col)
            
            # Use interpret functions from shared_ui (copied from performance_tests/print_report logic)
            # But shared_ui needs them. Let's use the ones defined above.
            from performance_tests import interpret_cxr as perf_interpret_cxr # Import to match logic if needed, but local functions are defined
            
            # Using local functions defined in this file for shared UI display
            cxr_display, _ = interpret_cxr(cxr_val)
            ekg_display, _ = interpret_ekg(ekg_val)
            hep_a_display = safe_text(hep_a_val) if not is_empty(hep_a_val) else "ไม่ได้ตรวจ"

            sp_rows = [
                [("ผลเอกซเรย์ (Chest X-ray)", False), (cxr_display, False)],
                [("ผลคลื่นไฟฟ้าหัวใจ (EKG)", False), (ekg_display, False)],
                [("ไวรัสตับอักเสบเอ (Hepatitis A)", False), (hep_a_display, False)]
            ]
            st.markdown(render_lab_table_html("ผลตรวจพิเศษ (Special Exams)", ["รายการ", "ผลตรวจ"], sp_rows, table_class="info-detail-table"), unsafe_allow_html=True)

            # Hepatitis B
            hbsag_col, hbsab_col, hbcab_col = "HbsAg", "HbsAb", "HBcAB"
            if selected_year != (datetime.now().year + 543):
                suffix = str(selected_year)[-2:]
                if f"HbsAg{suffix}" in person: hbsag_col = f"HbsAg{suffix}"
                if f"HbsAb{suffix}" in person: hbsab_col = f"HbsAb{suffix}"
                if f"HBcAB{suffix}" in person: hbcab_col = f"HBcAB{suffix}"
            
            hbsag = safe_text(person.get(hbsag_col))
            hbsab = safe_text(person.get(hbsab_col))
            hbcab = safe_text(person.get(hbcab_col))
            if hbcab == "-" and hbsag != "-" and hbsab != "-": hbcab = "Negative"

            hep_rows = [[("HBsAg", False), (hbsag, False)], [("HBsAb", False), (hbsab, False)], [("HBcAb", False), (hbcab, False)]]
            # Use specific header for hep B
            st.markdown(clean_html_string(f"""
            <div class="card-container">
                <div class='table-title'>ผลการตรวจไวรัสตับอักเสบบี (Hepatitis B)</div>
                <div class='table-responsive'>
                    <table class='lab-table'>
                        <thead><tr><th style='text-align:center'>HBsAg</th><th style='text-align:center'>HBsAb</th><th style='text-align:center'>HBcAb</th></tr></thead>
                        <tbody><tr><td style='text-align:center'>{hbsag}</td><td style='text-align:center'>{hbsab}</td><td style='text-align:center'>{hbcab}</td></tr></tbody>
                    </table>
                </div>
                {(f"<div class='advice-box-styled'><div class='advice-icon'>ℹ️</div><div>{hepatitis_b_advice(hbsag, hbsab, hbcab)[0]}</div></div>" if not (is_empty(hbsag) and is_empty(hbsab) and is_empty(hbcab)) else "")}
            </div>
            """), unsafe_allow_html=True)

    with st.container():
        from performance_tests import generate_comprehensive_recommendations
        render_section_header("สรุปและคำแนะนำการปฏิบัติตัว (Summary & Recommendations)")
        recommendations_html = generate_comprehensive_recommendations(person_data)
        st.markdown(clean_html_string(f"<div class='card-container' style='border-left: 5px solid var(--accent);'>{recommendations_html}</div>"), unsafe_allow_html=True)
