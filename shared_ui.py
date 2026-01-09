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
import altair as alt # เพิ่ม import altair สำหรับกราฟ

# --- Helper Functions ---
def is_empty(val):
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def normalize_name(name):
    if is_empty(name):
        return ""
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
    ฟังก์ชันล้างช่องว่างนำหน้าบรรทัด (Indentation) ทั้งหมด
    เพื่อป้องกันไม่ให้ Streamlit ตีความ HTML เป็น Code Block
    """
    if not html_str: return ""
    return "\n".join([line.strip() for line in html_str.split('\n') if line.strip()])

def inject_keep_awake():
    """
    ฝัง JavaScript เพื่อป้องกันหน้าจอ Sleep (Wake Lock API)
    เหมาะสำหรับแพทย์ที่เปิดหน้าจอทิ้งไว้ดูผลตรวจ
    """
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
            
            // เรียกขอสิทธิ์ทันทีที่โหลด
            await requestWakeLock();
            
            // ขอสิทธิ์ใหม่เมื่อกลับมาที่แท็บเดิม (เผื่อหลุด)
            document.addEventListener('visibilitychange', async () => {
                if (document.visibilityState === 'visible') {
                    await requestWakeLock();
                }
            });
        } catch (err) {
            console.log('Wake Lock Error:', err);
        }
    })();
    </script>
    """
    # ใช้ height=0 เพื่อซ่อน component ไม่ให้รกหน้าจอ
    components.html(js_code, height=0, width=0)

def inject_custom_css():
    """
    Inject CSS เพื่อปรับแต่งหน้าตาของแอปพลิเคชัน
    เน้นการรองรับ Responsive (มือถือ/Desktop) และ Theme (Light/Dark Mode)
    """
    css_content = clean_html_string("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');
        
        :root {
            /* ใช้ตัวแปรสีของ Streamlit เพื่อรองรับ Light/Dark Mode อัตโนมัติ */
            --bg-color: var(--background-color);
            --text-color: var(--text-color);
            --card-bg: var(--secondary-background-color); /* ใช้สีพื้นหลังรองของ Streamlit */
            --border-color: rgba(128, 128, 128, 0.2);     /* สีขอบแบบจางๆ */
            
            /* สีธีมหลัก */
            --primary: #00796B;
            --primary-light: rgba(0, 121, 107, 0.1);
            
            /* สีสถานะ (ปรับให้ดูนุ่มนวลขึ้นใน Dark Mode ได้ถ้าต้องการ แต่สีพื้นฐานนี้ใช้ได้ดีทั้งคู่) */
            --danger-text: #FF5252;
            --warning-text: #FF9800;
            --success-text: #4CAF50;
            
            --danger-bg: rgba(255, 82, 82, 0.1);
            --warning-bg: rgba(255, 152, 0, 0.1);
            --success-bg: rgba(76, 175, 80, 0.1);
            
            /* สี Header ตาราง (ปรับความเข้มให้เหมาะกับธีม) */
            --header-bg: rgba(128, 128, 128, 0.1); 
        }

        /* บังคับใช้ Font Sarabun ทั้งหมด */
        html, body, [class*="st-"], h1, h2, h3, h4, h5, h6, p, div, span, th, td {
            font-family: 'Sarabun', sans-serif !important;
        }
        
        /* --- Customized Tabs Style (Green Bar Theme) --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: var(--primary); 
            border-radius: 10px 10px 0px 0px;
            padding: 10px 10px 0px 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            flex-wrap: wrap; /* ให้แท็บขึ้นบรรทัดใหม่ได้ถ้าหน้าจอเล็กมาก */
        }

        .stTabs [data-baseweb="tab"] {
            height: auto;
            white-space: pre-wrap;
            background-color: transparent; 
            border-radius: 8px 8px 0px 0px;
            gap: 1px;
            padding: 8px 16px; /* ลด Padding เล็กน้อยเพื่อให้พอดีจอมือถือ */
            color: rgba(255, 255, 255, 0.85);
            font-weight: 600;
            font-size: 0.95rem;
            border: none; 
            transition: all 0.2s ease;
            flex-grow: 1; /* ให้แท็บขยายเต็มพื้นที่ที่มี */
            text-align: center;
        }

        .stTabs [data-baseweb="tab"]:hover {
            color: #ffffff;
            background-color: rgba(255, 255, 255, 0.15);
        }

        .stTabs [aria-selected="true"] {
            background-color: #ffffff !important; /* เปลี่ยนเป็นสีขาวตามที่ขอ */
            color: var(--primary) !important;
            border-radius: 10px 10px 0px 0px;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.1); 
            padding: 10px 20px;
            font-weight: 700;
            position: relative;
            top: 1px;
        }
        
        .stTabs [data-baseweb="tab-border"] { display: none; }

        /* --------------------------- */

        /* หัวข้อ Section */
        .section-header-styled {
            font-size: 1.2rem; 
            font-weight: 600; 
            color: var(--primary);
            border-left: 5px solid var(--primary); 
            padding-left: 15px; 
            margin-top: 25px; 
            margin-bottom: 15px;
            background: linear-gradient(90deg, var(--primary-light) 0%, rgba(0,0,0,0) 100%);
            padding-top: 8px; 
            padding-bottom: 8px; 
            border-radius: 0 8px 8px 0;
        }
        
        .section-subtitle { 
            font-weight: 600; 
            color: var(--text-color); 
            opacity: 0.9; 
            margin-top: 1rem; 
            margin-bottom: 0.5rem; 
            font-size: 1rem; 
        }

        /* Card Container (กล่องขาว/ดำ รองรับ Theme) */
        .card-container {
            background-color: var(--card-bg); 
            border-radius: 12px; 
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); 
            border: 1px solid var(--border-color);
            margin-bottom: 15px; 
            color: var(--text-color);
            overflow: hidden; /* ป้องกันเนื้อหาล้น */
        }

        /* ตาราง (Table) */
        .table-title { 
            font-weight: 700; 
            color: var(--text-color); 
            margin-bottom: 12px; 
            font-size: 1rem; 
            border-bottom: 2px solid var(--border-color); 
            padding-bottom: 8px; 
        }
        
        .table-responsive { 
            width: 100%;
            overflow-x: auto; /* เลื่อนแนวนอนได้ถ้าตารางกว้างเกินจอ */
            -webkit-overflow-scrolling: touch; /* เลื่อนลื่นๆ บน iOS */
        }
        
        .lab-table, .info-detail-table { 
            width: 100%; 
            min-width: 300px; /* กำหนดความกว้างขั้นต่ำป้องกันตารางบีบเกินไป */
            border-collapse: collapse; 
            font-size: 0.9rem; 
            color: var(--text-color); 
        }
        
        .lab-table th, .info-detail-table th {
            background-color: var(--header-bg); 
            color: var(--text-color); 
            font-weight: 600; 
            padding: 10px; 
            font-size: 0.85rem; 
            border-bottom: 2px solid var(--border-color);
            text-align: left;
            white-space: nowrap; /* ป้องกันหัวตารางตัดคำถ้าไม่จำเป็น */
            /* ลบ text-transform: uppercase; ออกแล้ว */
        }
        
        .lab-table td, .info-detail-table td { 
            padding: 10px; 
            border-bottom: 1px solid var(--border-color); 
            vertical-align: middle;
        }
        
        /* แก้ไข: ลบคำสั่งซ่อนเส้นขอบล่างของแถวสุดท้ายออก เพื่อให้มีเส้นปิดท้ายตารางเสมอ */
        /* .lab-table tr:last-child td { border-bottom: none; } */
        
        .abnormal-row { background-color: var(--danger-bg) !important; }
        .text-danger { color: var(--danger-text) !important; font-weight: bold; }

        /* Report Header (ส่วนหัวข้อมูลผู้ป่วย) */
        .report-header-container {
            background-color: var(--card-bg); 
            border-radius: 12px; 
            padding: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); 
            border: 1px solid var(--border-color); 
            margin-bottom: 20px; 
            color: var(--text-color);
        }
        
        .header-main { 
            display: flex; 
            justify-content: space-between; 
            align-items: flex-start; 
            flex-wrap: wrap; 
            gap: 15px; 
        }
        
        .patient-profile { 
            display: flex; 
            gap: 15px; 
            align-items: center; 
            flex: 1 1 300px; /* ยืดหยุ่นแต่มีความกว้างขั้นต่ำ */
        }
        
        .profile-icon {
            width: 50px; height: 50px; 
            background-color: var(--primary-light); 
            color: var(--primary);
            border-radius: 50%; 
            display: flex; 
            align-items: center; 
            justify-content: center;
            flex-shrink: 0; /* ไม่ให้ไอคอนหดตัว */
        }
        
        .patient-name { font-size: 1.3rem; font-weight: 700; line-height: 1.2; margin-bottom: 4px; }
        .patient-meta { opacity: 0.8; font-size: 0.9rem; }
        .patient-dept {
            background-color: var(--header-bg); 
            display: inline-block; 
            padding: 2px 8px;
            border-radius: 4px; 
            font-size: 0.8rem; 
            margin-top: 6px; 
            font-weight: 500;
        }
        
        .report-meta { 
            text-align: right; 
            flex: 1 1 200px;
        }
        
        .hospital-brand .hosp-name { font-weight: 700; color: var(--primary); font-size: 1.1rem; }
        .hospital-brand .hosp-dept { font-size: 0.95rem; opacity: 0.9; }
        .hospital-brand .hosp-sub { font-size: 0.85rem; opacity: 0.7; }

        /* Vitals Grid (ตารางค่าชีพจรต่างๆ) */
        .vitals-grid-container { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); /* ปรับ minmax ให้เล็กลงเพื่อให้แสดงผลในมือถือได้ 2 คอลัมน์ */
            gap: 15px; 
            margin-bottom: 25px; 
        }
        
        .vital-card {
            background: var(--card-bg); 
            border-radius: 10px; 
            padding: 15px; 
            display: flex; 
            align-items: center; 
            gap: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05); 
            border: 1px solid var(--border-color); 
            color: var(--text-color);
        }
        
        .vital-icon-box { 
            width: 40px; height: 40px; 
            display: flex; align-items: center; justify-content: center; 
            flex-shrink: 0;
        }
        .vital-icon-box svg { width: 28px; height: 28px; }
        
        .color-blue { color: #2196F3; } .color-green { color: #4CAF50; } .color-red { color: #F44336; } .color-orange { color: #FF9800; }
        
        .vital-content { flex: 1; min-width: 0; /* ป้องกัน content ดันกล่องขยาย */ }
        .vital-label { font-size: 0.8rem; opacity: 0.7; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .vital-value { font-size: 1.2rem; font-weight: 700; line-height: 1.2; }
        .unit { font-size: 0.8rem; opacity: 0.6; font-weight: 400; }
        .vital-sub { font-size: 0.75rem; opacity: 0.6; margin-top: 2px; }
        
        .badge { display: inline-block; padding: 2px 6px; border-radius: 10px; font-size: 0.7rem; font-weight: 600; }
        .badge-bmi { background-color: var(--header-bg); }

        /* Recommendation Box */
        .recommendation-container {
            background-color: var(--card-bg); 
            border-radius: 12px; 
            padding: 20px; 
            border-left: 6px solid var(--primary);
            box-shadow: 0 2px 5px rgba(0,0,0,0.05); 
            color: var(--text-color);
        }
        
        .custom-advice-box { 
            padding: 15px; 
            border-radius: 8px; 
            margin-top: 15px; 
            border: 1px solid transparent; 
            font-weight: 500; 
            display: flex; 
            align-items: flex-start; /* จัดชิดบนเพื่อให้ไอคอนไม่ลอยถ้าข้อความยาว */
            gap: 10px; 
        }
        .custom-advice-box::before { content: "💡"; font-size: 1.2rem; line-height: 1; }
        
        .immune-box { background-color: var(--success-bg); color: var(--success-text); border-color: rgba(76, 175, 80, 0.2); }
        .no-immune-box { background-color: var(--danger-bg); color: var(--danger-text); border-color: rgba(255, 82, 82, 0.2); }
        .warning-box { background-color: var(--warning-bg); color: var(--warning-text); border-color: rgba(255, 152, 0, 0.2); }

        /* Vision Result Pills */
        .vision-result { padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; white-space: nowrap; }
        .vision-normal { background-color: var(--success-bg); color: var(--success-text); }
        .vision-abnormal { background-color: var(--danger-bg); color: var(--danger-text); }
        .vision-warning { background-color: var(--warning-bg); color: var(--warning-text); }
        .vision-not-tested { background-color: var(--header-bg); opacity: 0.6; }

        /* Mobile Adjustments (Responsive) */
        @media (max-width: 768px) {
            .header-main { flex-direction: column; align-items: flex-start; gap: 15px; }
            .report-meta { text-align: left; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border-color); width: 100%; }
            
            .vitals-grid-container { grid-template-columns: 1fr 1fr; gap: 10px; } /* มือถือแสดง 2 คอลัมน์ */
            .vital-value { font-size: 1.1rem; }
            
            .table-responsive { overflow-x: auto; }
            
            /* ลดขนาด Font บนมือถือเล็กน้อย */
            .section-header-styled { font-size: 1.1rem; padding-left: 10px; margin-top: 20px; }
            .patient-name { font-size: 1.2rem; }
            
            /* ปรับตารางให้เลื่อนได้ */
            .lab-table th, .lab-table td { padding: 8px; font-size: 0.85rem; }
        }
        
        @media (max-width: 480px) {
            .vitals-grid-container { grid-template-columns: 1fr; } /* จอเล็กมากแสดง 1 คอลัมน์ */
            .profile-icon { width: 40px; height: 40px; }
            .profile-icon svg { width: 24px; height: 24px; }
        }
    </style>""")
    st.markdown(css_content, unsafe_allow_html=True)

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
    html_content = clean_html_string(f"""<div class="card-container">{header_html}<div class='table-responsive'><table class='{table_class}'><colgroup><col style='width:40%;'><col style='width:20%;'><col style='width:40%;'></colgroup>{thead}{tbody}</table></div></div>""")
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
            <div class="vital-icon-box color-blue">{icon_body}</div>
            <div class="vital-content">
                <div class="vital-label">สัดส่วนร่างกาย</div>
                <div class="vital-value">{weight_val} <span class="unit">kg</span> / {height_val} <span class="unit">cm</span></div>
                <div class="vital-sub">BMI: {bmi_val_str} <br><span class="badge badge-bmi">{bmi_desc}</span></div>
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon-box color-green">{icon_waist}</div>
            <div class="vital-content"><div class="vital-label">รอบเอว</div><div class="vital-value">{waist_val} <span class="unit">cm</span></div></div>
        </div>
        <div class="vital-card">
            <div class="vital-icon-box color-red">{icon_heart}</div>
            <div class="vital-content">
                <div class="vital-label">ความดันโลหิต</div>
                <div class="vital-value">{bp_val} <span class="unit">mmHg</span></div>
                <div class="vital-sub">{bp_desc}</div>
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon-box color-orange">{icon_pulse}</div>
            <div class="vital-content"><div class="vital-label">ชีพจร</div><div class="vital-value">{pulse_val} <span class="unit">bpm</span></div></div>
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
        if is_empty(val): return "-", "vision-not-tested"
        val_str = str(val).strip().lower()
        normal_keywords = ['normal', 'ปกติ', 'pass', 'ผ่าน', 'within normal', 'no', 'none', 'ortho', 'orthophoria', 'clear', 'ok', 'good', 'binocular', '6/6', '20/20']
        warning_keywords = ['mild', 'slight', 'เล็กน้อย', 'trace', 'low', 'ต่ำ', 'below', 'drop']
        abnormal_keywords = ['abnormal', 'ผิดปกติ', 'fail', 'ไม่ผ่าน', 'detect', 'found', 'พบ', 'deficiency', 'color blind', 'blind', 'eso', 'exo', 'hyper', 'hypo']
        if val_str in normal_keywords: return "ปกติ", "vision-normal"
        if any(kw in val_str for kw in abnormal_keywords):
            if any(kw in val_str for kw in warning_keywords): return "ต่ำกว่าเกณฑ์", "vision-warning"
            return "ผิดปกติ", "vision-abnormal"
        if any(kw in val_str for kw in warning_keywords): return "ต่ำกว่าเกณฑ์", "vision-warning"
        if re.match(r'^\d+/\d+$', val_str): return str(val), "vision-normal"
        if len(val_str) > 20: return "ผิดปกติ", "vision-abnormal"
        return str(val), "vision-normal"

    html_rows = ""
    any_data_found = False
    for item in vision_config:
        val = None
        for key in item['keys']:
            if not is_empty(person_data.get(key)):
                val = person_data.get(key)
                any_data_found = True
                break
        res_text, res_class = check_vision(val, item['id'])
        html_rows += f"<tr><td>{item['label']}</td><td class='result-cell' style='text-align:center;'><span class='vision-result {res_class}'>{res_text}</span></td></tr>"
    
    doctor_advice = person_data.get('แนะนำABN EYE', '')
    summary_advice = person_data.get('สรุปเหมาะสมกับงาน', '')
    footer_html = ""
    if not is_empty(summary_advice) or not is_empty(doctor_advice):
        footer_html = "<div class='card-container' style='margin-top: 10px; background-color: var(--warning-bg); border-color: rgba(255, 152, 0, 0.3);'>"
        if not is_empty(summary_advice): footer_html += f"<b>สรุปความเหมาะสมกับงาน:</b> {summary_advice}<br>"
        if not is_empty(doctor_advice): footer_html += f"<b>คำแนะนำแพทย์:</b> {doctor_advice}"
        footer_html += "</div>"
    html_content = clean_html_string(f"""<div class='card-container'><div class='table-title'>ผลการตรวจสมรรถภาพการมองเห็น (Vision Test)</div><table class='vision-table'><thead><tr><th>รายการทดสอบ</th><th style='text-align: center; width: 150px;'>ผลการตรวจ</th></tr></thead><tbody>{html_rows}</tbody></table></div>{footer_html}""")
    if any_data_found: st.markdown(html_content, unsafe_allow_html=True)
    else: st.info("ไม่พบข้อมูลการตรวจสายตา")

def display_performance_report_vision(person_data):
    """Wrapper function to match calling convention"""
    render_vision_details_table(person_data)

def display_performance_report_hearing(person_data, all_person_history_df):
    # ย้าย import มาไว้ในฟังก์ชันเพื่อแก้ Circular Import
    from performance_tests import interpret_audiogram
    results = interpret_audiogram(person_data, all_person_history_df)
    
    # -------------------------------------------------------------
    # สร้างกราฟ Audiogram ด้วย Altair
    # -------------------------------------------------------------
    
    freq_map = {
        '250 Hz': 250, '500 Hz': 500, '1000 Hz': 1000, 
        '2000 Hz': 2000, '3000 Hz': 3000, '4000 Hz': 4000, 
        '6000 Hz': 6000, '8000 Hz': 8000
    }
    
    # เตรียมข้อมูลสำหรับกราฟ
    chart_data = []
    
    # วนลูปข้อมูล raw_values ที่ได้จาก interpret_audiogram
    # results['raw_values'] จะมีโครงสร้าง { '500 Hz': {'right': 20, 'left': 25}, ... }
    # ต้องเพิ่ม 250 Hz ถ้ามีใน person_data เพราะ interpret_audiogram อาจไม่ได้ส่งมาทุกความถี่
    
    # สร้าง list ความถี่ทั้งหมดที่ต้องการแสดง
    all_freqs = ['250 Hz', '500 Hz', '1000 Hz', '2000 Hz', '3000 Hz', '4000 Hz', '6000 Hz', '8000 Hz']
    
    for freq_str in all_freqs:
        freq_num = freq_map[freq_str]
        
        # พยายามดึงค่าจาก results ก่อน
        r_val = None
        l_val = None
        
        if freq_str in results['raw_values']:
            r_val = results['raw_values'][freq_str]['right']
            l_val = results['raw_values'][freq_str]['left']
        else:
            # ถ้าไม่มีใน results (เช่น 250 Hz) ให้ลองดึงตรงๆ จาก person_data
            # สร้าง key ที่เป็นไปได้ เช่น R250, L250
            suffix = str(freq_num)
            if freq_num >= 1000: suffix = f"{freq_num//1000}k"
            
            # ลองหาหลายแบบ
            r_keys = [f"R{suffix}", f"R_{suffix}", f"R{suffix}Hz"]
            l_keys = [f"L{suffix}", f"L_{suffix}", f"L{suffix}Hz"]
            
            for k in r_keys:
                if not is_empty(person_data.get(k)): 
                    try: r_val = int(float(person_data.get(k)))
                    except: pass
                    break
            
            for k in l_keys:
                if not is_empty(person_data.get(k)): 
                    try: l_val = int(float(person_data.get(k)))
                    except: pass
                    break

        if r_val is not None:
            chart_data.append({'Frequency': freq_num, 'dB': r_val, 'Ear': 'Right (หูขวา)'})
        if l_val is not None:
            chart_data.append({'Frequency': freq_num, 'dB': l_val, 'Ear': 'Left (หูซ้าย)'})

    if not chart_data:
        st.info("ไม่พบข้อมูลกราฟการได้ยิน")
    else:
        df_chart = pd.DataFrame(chart_data)
        
        # สร้างกราฟ Altair
        # แกน X: Frequency (Log Scale เพื่อความสวยงามแบบ Audiogram มาตรฐาน หรือ Linear ก็ได้ตามชอบ แต่มาตรฐานคือ Log)
        # แกน Y: dB (Reverse Scale เพราะค่ายิ่งน้อยยิ่งดี)
        
        # ปรับแต่ง Domain แกน X และ Y
        x_domain = [125, 8500] 
        y_domain = [-10, 100] # dB range
        
        base = alt.Chart(df_chart).encode(
            x=alt.X('Frequency:Q', scale=alt.Scale(type='log', domain=x_domain), title='ความถี่ (Hz)'),
            y=alt.Y('dB:Q', scale=alt.Scale(domain=y_domain, reverse=True), title='ระดับการได้ยิน (dB)'),
            color=alt.Color('Ear:N', scale=alt.Scale(domain=['Right (หูขวา)', 'Left (หูซ้าย)'], range=['#ef5350', '#42a5f5']), legend=alt.Legend(title="ข้างที่ตรวจ")),
            tooltip=['Ear', 'Frequency', 'dB']
        )

        lines = base.mark_line(point=True).encode(
            shape=alt.Shape('Ear:N', scale=alt.Scale(domain=['Right (หูขวา)', 'Left (หูซ้าย)'], range=['circle', 'cross']))
        )
        
        # เพิ่มเส้นประที่ระดับ 25 dB (ค่าปกติ)
        rule = alt.Chart(pd.DataFrame({'y': [25]})).mark_rule(color='green', strokeDash=[5, 5]).encode(y='y')
        
        final_chart = (lines + rule).properties(
            title="กราฟแสดงผลการตรวจการได้ยิน (Audiogram)",
            height=350
        ).interactive()

        st.altair_chart(final_chart, use_container_width=True)

    # -------------------------------------------------------------
    # ส่วนแสดงข้อมูลสรุปด้านล่างกราฟ
    # -------------------------------------------------------------
    
    col1, col2 = st.columns(2)
    with col1: st.markdown(f"<div class='card-container'><b>สรุปผลหูขวา:</b><br>{results['summary']['right']}</div>", unsafe_allow_html=True)
    with col2: st.markdown(f"<div class='card-container'><b>สรุปผลหูซ้าย:</b><br>{results['summary']['left']}</div>", unsafe_allow_html=True)
    if results['advice']: st.warning(f"คำแนะนำ: {results['advice']}")

def display_performance_report_lung(person_data):
    # ย้าย import มาไว้ในฟังก์ชันเพื่อแก้ Circular Import
    from performance_tests import interpret_lung_capacity
    summary, advice, raw_data = interpret_lung_capacity(person_data)
    st.markdown(clean_html_string("""<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 20px;"><div class="card-container" style="margin: 0; border-left: 4px solid #2196F3;"><div style="font-weight: bold; color: var(--main-text-color); margin-bottom: 5px;">🫁 FVC (ความจุปอด)</div><div style="font-size: 0.85rem; opacity: 0.8;">ปริมาตรอากาศทั้งหมดที่เป่าออกมาได้เต็มที่ (บอกขนาดปอด)</div></div><div class="card-container" style="margin: 0; border-left: 4px solid #00BCD4;"><div style="font-weight: bold; color: var(--main-text-color); margin-bottom: 5px;">💨 FEV1 (ปริมาตรลมเป่าเร็ว)</div><div style="font-size: 0.85rem; opacity: 0.8;">ปริมาตรอากาศที่เป่าออกได้ในวินาทีแรก (บอกความโล่งของหลอดลม)</div></div></div>"""), unsafe_allow_html=True)
    lung_items = [("FVC (ความจุปอด)", raw_data['FVC predic'], raw_data['FVC'], raw_data['FVC %']), ("FEV1 (ปริมาตรลมเป่าเร็ว)", raw_data['FEV1 predic'], raw_data['FEV1'], raw_data['FEV1 %']), ("FEV1/FVC Ratio (สัดส่วน)", "-", raw_data['FEV1/FVC %'], "-")]
    def make_bar(val):
        try:
            v = float(str(val).replace('%','').strip())
            color = "var(--success-text)" if v >= 80 else "var(--warning-text)" if v >= 60 else "var(--danger-text)"
            return f"<div style='background:rgba(128,128,128,0.2);height:6px;border-radius:3px;width:100px;display:inline-block;vertical-align:middle;margin-right:8px;'><div style='width:{min(v,100)}%;background:{color};height:100%;border-radius:3px;'></div></div> {v}%"
        except: return str(val)
    html_content = clean_html_string("""<div class='card-container'><div class='table-title'>ผลการตรวจสมรรถภาพปอด (Spirometry)</div><table class='lab-table'><thead><tr><th style='width: 30%;'>รายการ</th><th style='text-align: center;'>ค่ามาตรฐาน</th><th style='text-align: center;'>ค่าที่วัดได้</th><th style='width: 35%;'>ผลเทียบมาตรฐาน (%)</th></tr></thead><tbody>""")
    for label, pred, act, per in lung_items:
        display_per = make_bar(per) if per != "-" else "-"
        html_content += f"<tr><td>{label}</td><td style='text-align:center;'>{pred}</td><td style='text-align:center;'>{act}</td><td>{display_per}</td></tr>"
    html_content += "</tbody></table></div>"
    st.markdown(html_content, unsafe_allow_html=True)
    st.markdown(f"<div class='card-container'><b>สรุปผล:</b> {summary}<br><br><b>คำแนะนำ:</b> {advice}</div>", unsafe_allow_html=True)

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
    # Config for Urine Tests
    urine_config = [
        ("สี (Colour)", "Color", "Yellow"),
        ("น้ำตาล (Sugar)", "sugar", "Negative"),
        ("โปรตีน (Albumin)", "Alb", "Negative"),
        ("กรด-ด่าง (pH)", "pH", "5.0 - 8.0"),
        ("ความถ่วงจำเพาะ (Sp.gr)", "Spgr", "1.003 - 1.030"),
        ("เม็ดเลือดแดง (RBC)", "RBC1", "0 - 2"),
        ("เม็ดเลือดขาว (WBC)", "WBC1", "0 - 5"),
        ("เซลล์เยื่อบุผิว (Epit)", "SQ-epi", "0 - 10"),
        ("อื่นๆ", "ORTER", "-")
    ]
    
    rows = []
    for label, col, norm in urine_config:
        val = person_data.get(col)
        # Check abnormality
        is_abn = is_urine_abnormal(label, val, norm)
        
        # Format for table: (Text, Is_Abnormal)
        label_tuple = (label, is_abn)
        val_tuple = (safe_value(val), is_abn)
        norm_tuple = (norm, is_abn)
        
        rows.append([label_tuple, val_tuple, norm_tuple])
    
    # Render table
    st.markdown(render_lab_table_html("ผลการตรวจปัสสาวะ (Urinalysis)", ["รายการ", "ผลตรวจ", "ค่าปกติ"], rows), unsafe_allow_html=True)

def render_stool_html_table(exam_result, cs_result):
    html = f"""
    <div class="card-container">
        <div class='table-title'>ผลการตรวจอุจจาระ (Stool Examination)</div>
        <table class="lab-table">
            <thead><tr><th>รายการ</th><th>ผลตรวจ</th></tr></thead>
            <tbody>
                <tr><td>Stool Examination</td><td>{exam_result}</td></tr>
                <tr><td>Stool Culture</td><td>{cs_result}</td></tr>
            </tbody>
        </table>
    </div>
    """
    return clean_html_string(html)

def display_main_report(person_data, all_person_history_df):
    person = person_data
    sex = str(person.get("เพศ", "")).strip()
    if sex not in ["ชาย", "หญิง"]: sex = "ไม่ระบุ"
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_config = [("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None), ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None), ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000), ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70), ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44), ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9), ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9), ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3), ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000)]
    cbc_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high in cbc_config for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high)]]

    blood_config = [("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106), ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2), ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120), ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37), ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41), ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200), ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150), ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True), ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160), ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20), ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17), ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True)]
    blood_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high, *opt in blood_config for higher in [opt[0] if opt else False] for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high, higher)]]

    with st.container(border=True):
        render_section_header("ผลการตรวจทางห้องปฏิบัติการ (Laboratory Results)")
        col1, col2 = st.columns(2)
        with col1: st.markdown(render_lab_table_html("ผลตรวจความสมบูรณ์ของเม็ดเลือด (CBC)", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
        with col2: st.markdown(render_lab_table_html("ผลตรวจเลือด (Blood Chemistry)", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

    selected_year = person.get("Year", datetime.now().year + 543)

    with st.container(border=True):
        render_section_header("ผลการตรวจอื่นๆ (Other Examinations)")
        col_ua_left, col_ua_right = st.columns(2)
        with col_ua_left:
            render_urine_section(person, sex, selected_year)
            # st.markdown("<h5 class='section-subtitle'>ผลตรวจอุจจาระ (Stool Examination)</h5>", unsafe_allow_html=True)
            # Use new function
            st.markdown(render_stool_html_table(interpret_stool_exam(person.get("Stool exam", "")), interpret_stool_cs(person.get("Stool C/S", ""))), unsafe_allow_html=True)

        with col_ua_right:
            st.markdown("<h5 class='section-subtitle'>ผลตรวจพิเศษ</h5>", unsafe_allow_html=True)
            
            # --- CXR Logic: Check "CXR" column first ---
            cxr_val = person.get("CXR")
            if is_empty(cxr_val):
                # Fallback logic: Try to find year-specific column e.g. CXR66
                cxr_col = f"CXR{str(selected_year)[-2:]}"
                cxr_val = person.get(cxr_col)
            # ------------------------------------------

            # --- EKG Logic: Check "EKG" column first ---
            ekg_val = person.get("EKG")
            if is_empty(ekg_val):
                ekg_col = f"EKG{str(selected_year)[-2:]}"
                ekg_val = person.get(ekg_col)
            # ------------------------------------------

            # --- Hepatitis A Logic: Check "Hepatitis A" column first ---
            # NOTE: Assuming year specific columns might exist like Hepatitis A66
            # If not, this logic will just fallback to None and display "ไม่ได้ตรวจ"
            hep_a_val = person.get("Hepatitis A")
            if is_empty(hep_a_val):
                hep_a_col = f"Hepatitis A{str(selected_year)[-2:]}"
                hep_a_val = person.get(hep_a_col)
            
            hep_a_display_text = "ไม่ได้ตรวจ" if is_empty(hep_a_val) else safe_text(hep_a_val)
            # -----------------------------------------------------------

            st.markdown(clean_html_string(f"""
            <div class="table-container">
                <table class="info-detail-table">
                    <tbody>
                        <tr><th>ผลเอกซเรย์ (Chest X-ray)</th><td>{interpret_cxr(cxr_val)}</td></tr>
                        <tr><th>ผลคลื่นไฟฟ้าหัวใจ (EKG)</th><td>{interpret_ekg(ekg_val)}</td></tr>
                        <tr><th>ไวรัสตับอักเสบเอ (Hepatitis A)</th><td>{hep_a_display_text}</td></tr>
                    </tbody>
                </table>
            </div>
            """), unsafe_allow_html=True)

            # --- Logic to get correct Hepatitis B columns based on year ---
            hbsag_col = "HbsAg"
            hbsab_col = "HbsAb"
            hbcab_col = "HBcAB"
            current_thai_year = datetime.now().year + 543
            if selected_year != current_thai_year:
                suffix = str(selected_year)[-2:]
                if f"HbsAg{suffix}" in person: hbsag_col = f"HbsAg{suffix}"
                if f"HbsAb{suffix}" in person: hbsab_col = f"HbsAb{suffix}"
                if f"HBcAB{suffix}" in person: hbcab_col = f"HBcAB{suffix}"

            hep_year_rec = str(person.get("ปีตรวจHEP", "")).strip()
            header_suffix = ""
            if not is_empty(hep_year_rec):
                 header_suffix = f" (ตรวจเมื่อ: {hep_year_rec})"
            elif selected_year and selected_year != current_thai_year:
                 header_suffix = f" (พ.ศ. {selected_year})"

            st.markdown(f"<h5 class='section-subtitle'>ผลการตรวจไวรัสตับอักเสบบี (Viral hepatitis B){header_suffix}</h5>", unsafe_allow_html=True)

            hbsag = safe_text(person.get(hbsag_col))
            hbsab = safe_text(person.get(hbsab_col))
            hbcab = safe_text(person.get(hbcab_col))
            
            # แก้ไข: ตรงนี้หัวตารางจะแสดง HBsAg, HBsAb, HBcAb ตามที่ต้องการได้แล้ว เพราะลบ uppercase ออกจาก CSS
            st.markdown(clean_html_string(f"""
            <div class="table-container">
                <table class='lab-table'>
                    <thead><tr><th style='text-align: center;'>HBsAg</th><th style='text-align: center;'>HBsAb</th><th style='text-align: center;'>HBcAb</th></tr></thead>
                    <tbody><tr><td style='text-align: center;'>{hbsag}</td><td style='text-align: center;'>{hbsab}</td><td style='text-align: center;'>{hbcab}</td></tr></tbody>
                </table>
            </div>
            """), unsafe_allow_html=True)

            if not (is_empty(hbsag) and is_empty(hbsab) and is_empty(hbcab)):
                advice, status = hepatitis_b_advice(hbsag, hbsab, hbcab)
                status_class = ""
                if status == 'immune':
                    status_class = 'immune-box'
                elif status == 'no-immune':
                    status_class = 'no-immune-box'
                else:
                    status_class = 'warning-box'
                
                st.markdown(clean_html_string(f"""<div class='custom-advice-box {status_class}'>{advice}</div>"""), unsafe_allow_html=True)

    with st.container(border=True):
        # ย้าย import มาไว้ในฟังก์ชันเพื่อแก้ Circular Import
        from performance_tests import generate_comprehensive_recommendations
        render_section_header("สรุปและคำแนะนำการปฏิบัติตัว (Summary & Recommendations)")
        recommendations_html = generate_comprehensive_recommendations(person_data)
        st.markdown(f"<div class='recommendation-container'>{recommendations_html}</div>", unsafe_allow_html=True)
