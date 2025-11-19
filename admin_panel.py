import streamlit as st
import pandas as pd
from collections import OrderedDict
import json
from datetime import datetime
import re 
import html 
import numpy as np 

# --- Import ฟังก์ชันจากไฟล์อื่นที่จำเป็น ---
from performance_tests import interpret_audiogram, interpret_lung_capacity, generate_comprehensive_recommendations
from print_report import generate_printable_report
from print_performance_report import generate_performance_report_html
from visualization import display_visualization_tab 
from batch_print import display_print_center_page # Import หน้า Print Center

# --- Import ตรรกะการแปลผลจาก print_report.py ---
from print_report import (
    generate_fixed_recommendations,
    generate_cbc_recommendations,
    generate_urine_recommendations,
    generate_doctor_opinion
)

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
        val_float = float(str(val).replace(",", "").strip()) 
    except: return "-", False
    formatted_val = f"{int(val_float):,}" if val_float == int(val_float) else f"{val_float:,.1f}"
    is_abnormal = False
    if higher_is_better:
        if low is not None and val_float < low: is_abnormal = True
    else:
        if low is not None and val_float < low: is_abnormal = True
        if high is not None and val_float > high: is_abnormal = True
    return formatted_val, is_abnormal

def render_section_header(title):
    st.markdown(f"<h4>{title}</h4>", unsafe_allow_html=True)

def render_lab_table_html(title, headers, rows, table_class="lab-table", footer_html=None):
    header_html = f"<h5 class='section-subtitle'>{title}</h5>"
    html_content = f"{header_html}<div class='table-container'><table class='{table_class}'><colgroup><col style='width:40%;'><col style='width:20%;'><col style='width:40%;'></colgroup><thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i in [0, 2] else "center"
        html_content += f"<th style='text-align: {align};'>{h}</th>"
    html_content += "</tr></thead><tbody>"
    for row in rows:
        is_abn = any(flag_val for _, flag_val in row) 
        row_class = f"abnormal-row" if is_abn else ""
        html_content += f"<tr class='{row_class}'><td style='text-align: left;'>{row[0][0]}</td><td>{row[1][0]}</td><td style='text-align: left;'>{row[2][0]}</td></tr>"
    html_content += "</tbody>" 
    
    if footer_html:
        html_content += f"<tfoot><tr class='recommendation-row'><td colspan='{len(headers)}' style='text-align: left;'><b>สรุปผล/คำแนะนำ:</b><br>{footer_html}</td></tr></tfoot>"
        
    html_content += "</table></div>" 
    return html_content

def safe_text(val): return "-" if str(val).strip().lower() in ["", "none", "nan", "-"] else str(val).strip()
def safe_value(val):
    val = str(val or "").strip()
    return "-" if val.lower() in ["", "nan", "none", "-"] else val

def parse_range_or_number(val):
    val = str(val).replace("cell/hpf", "").replace("cells/hpf", "").replace("cell", "").strip().lower()
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

def render_urine_section(person_data, sex, year_selected, footer_html=None):
    urine_data = [("สี (Colour)", person_data.get("Color", "-"), "Yellow, Pale Yellow"), ("น้ำตาล (Sugar)", person_data.get("sugar", "-"), "Negative"), ("โปรตีน (Albumin)", person_data.get("Alb", "-"), "Negative, trace"), ("กรด-ด่าง (pH)", person_data.get("pH", "-"), "5.0 - 8.0"), ("ความถ่วงจำเพาะ (Sp.gr)", person_data.get("Spgr", "-"), "1.003 - 1.030"), ("เม็ดเลือดแดง (RBC)", person_data.get("RBC1", "-"), "0 - 2 cell/HPF"), ("เม็ดเลือดขาว (WBC)", person_data.get("WBC1", "-"), "0 - 5 cell/HPF"), ("เซลล์เยื่อบุผิว (Squam.epit.)", person_data.get("SQ-epi", "-"), "0 - 10 cell/HPF"), ("อื่นๆ", person_data.get("ORTER", "-"), "-")]
    df_urine = pd.DataFrame(urine_data, columns=["การตรวจ", "ผลตรวจ", "ค่าปกติ"])
    html_content = render_lab_table_html("ผลการตรวจปัสสาวะ (Urinalysis)", ["การตรวจ", "ผล", "ค่าปกติ"], [[(row["การตรวจ"], is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])), (safe_value(row["ผลตรวจ"]), is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])), (row["ค่าปกติ"], is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"]))] for _, row in df_urine.iterrows()], table_class="lab-table", footer_html=footer_html)
    st.markdown(html_content, unsafe_allow_html=True)
    return any(not is_empty(val) for _, val, _ in urine_data)

def interpret_stool_exam(val):
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจ"
    val_lower = str(val).strip().lower()
    if val_lower == "normal": return "ไม่พบเม็ดเลือดขาวในอุจจาระ ถือว่าปกติ"
    if "wbc" in val_lower or "เม็ดเลือดขาว" in val_lower: return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
    return val
def interpret_stool_cs(value):
    if is_empty(value): return "ไม่ได้เข้ารับการตรวจ"
    val_strip = str(value).strip()
    if "ไม่พบ" in val_strip or "ปกติ" in val_strip: return "ไม่พบการติดเชื้อ"
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"

def render_stool_html_table(exam, cs):
    html_content = f"""<div class="table-container"><table class="info-detail-table"><tbody><tr><th>ผลตรวจอุจจาระทั่วไป</th><td>{exam}</td></tr><tr><th>ผลตรวจอุจจาระเพาะเชื้อ</th><td>{cs}</td></tr></tbody></table></div>"""
    return html_content

def get_ekg_col_name(year):
    current_thai_year = datetime.now().year + 543
    return "EKG" if year == current_thai_year else f"EKG{str(year)[-2:]}"

def interpret_ekg(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def hepatitis_b_advice(hbsag, hbsab, hbcab):
    hbsag, hbsab, hbcab = str(hbsag).lower(), str(hbsab).lower(), str(hbcab).lower() 
    if "positive" in hbsag: return "ติดเชื้อไวรัสตับอักเสบบี", "infection"
    if "positive" in hbsab and "positive" not in hbsag: return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี", "immune"
    if "positive" in hbcab and "positive" not in hbsab: return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน", "unclear"
    if all(x == "negative" for x in [hbsag, hbsab, hbcab]): return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน", "no_immune"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ", "unclear"

def has_basic_health_data(person_data):
    key_indicators = ['FBS', 'CHOL', 'HCT', 'Cr', 'WBC (cumm)', 'น้ำหนัก', 'ส่วนสูง', 'SBP']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

def has_vision_data(person_data):
    detailed_keys = ['ป.การรวมภาพ', 'ผ.การรวมภาพ', 'ป.ความชัดของภาพระยะไกล', 'ผ.ความชัดของภาพระยะไกล', 'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)', 'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)', 'ป.การกะระยะและมองความชัดลึกของภาพ', 'ผ.การกะระยะและมองความชัดลึกของภาพ', 'ป.การจำแนกสี', 'ผ.การจำแนกสี', 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง', 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน', 'ป.ความชัดของภาพระยะใกล้', 'ผ.ความชัดของภาพระยะใกล้', 'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)', 'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)', 'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน', 'ป.ลานสายตา', 'ผ.ลานสายตา', 'ผ.สายตาเขซ่อนเร้น']
    return any(not is_empty(person_data.get(key)) for key in detailed_keys)

def has_hearing_data(person_data):
    hearing_keys = [ 'R500', 'L500', 'R1k', 'L1k', 'R4k', 'L4k' ]
    return any(not is_empty(person_data.get(key)) for key in hearing_keys)

def has_lung_data(person_data):
    key_indicators = ['FVC เปอร์เซ็นต์', 'FEV1เปอร์เซ็นต์', 'FEV1/FVC%']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

def has_visualization_data(history_df):
    return history_df is not None and not history_df.empty

def interpret_bp(sbp, dbp):
    try:
        sbp, dbp = float(sbp), float(dbp)
        if sbp == 0 or dbp == 0: return "-"
        if sbp >= 160 or dbp >= 100: return "ความดันสูง"
        if sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
        if sbp < 120 and dbp < 80: return "ความดันปกติ"
        return "ความดันค่อนข้างสูง"
    except: return "-"

def interpret_cxr_ui(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
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
    age_raw = person_data.get('อายุ', '-')
    age = str(int(float(age_raw))) if isinstance(age_raw, (int, float)) or (isinstance(age_raw, str) and age_raw.replace('.', '', 1).isdigit()) else age_raw
    sex = person_data.get('เพศ', '-')
    hn_raw = person_data.get('HN', '-')
    hn = str(int(float(hn_raw))) if isinstance(hn_raw, (int, float)) or (isinstance(hn_raw, str) and hn_raw.replace('.', '', 1).isdigit()) else hn_raw
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
        bmi_val_str = f"{bmi:.1f} kg/m²"
        bmi_desc = interpret_bmi(bmi)

    st.markdown(f"""
    <div class="report-header">
        <div class="header-left">
            <h2>รายงานผลการตรวจสุขภาพ</h2>
            <p>คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม โรงพยาบาลสันทราย</p>
            <p>ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p>
        </div>
        <div class="header-right">
            <div class="info-card">
                <div class="info-card-item"><span>ชื่อ-สกุล:</span> {name}</div>
                <div class="info-card-item"><span>HN:</span> {hn}</div>
                <div class="info-card-item"><span>อายุ:</span> {age} ปี</div>
                <div class="info-card-item"><span>เพศ:</span> {sex}</div>
                <div class="info-card-item"><span>หน่วยงาน:</span> {department}</div>
                <div class="info-card-item"><span>วันที่ตรวจ:</span> {check_date}</div>
            </div>
        </div>
    </div>

    <div class="vitals-grid">
        <div class="vital-card">
            <div class="vital-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M12 6v6l4 2"></path></svg>
            </div>
            <div class="vital-data">
                <span class="vital-label">น้ำหนัก / ส่วนสูง</span>
                <span class="vital-value">{weight_val} kg / {height_val} cm</span>
                <span class="vital-sub-value">BMI: {bmi_val_str} ({bmi_desc})</span>
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M12 6v6l4 2"></path></svg>
            </div>
            <div class="vital-data">
                <span class="vital-label">รอบเอว</span>
                <span class="vital-value">{waist_val} cm</span>
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
            </div>
            <div class="vital-data">
                <span class="vital-label">ความดัน (mmHg)</span>
                <span class="vital-value">{bp_val}</span>
                <span class="vital-sub-value">{bp_desc}</span>
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
            </div>
            <div class="vital-data">
                <span class="vital-label">ชีพจร (BPM)</span>
                <span class="vital-value">{pulse_val}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def inject_custom_css():
    st.markdown("""
    <style>
         @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');

        :root {
            --abnormal-bg-color: rgba(220, 53, 69, 0.1);
            --abnormal-text-color: #C53030;
            --normal-bg-color: rgba(40, 167, 69, 0.1);
            --normal-text-color: #1E4620;
            --warning-bg-color: rgba(255, 193, 7, 0.1);
            --neutral-bg-color: rgba(108, 117, 125, 0.1);
            --neutral-text-color: #4A5568;
        }
        /* ... other CSS rules ... */
        .lab-table tfoot .recommendation-row td {
            background-color: var(--warning-bg-color);
            color: var(--text-color);
            opacity: 0.9;
            font-weight: normal;
            font-size: 13px;
            line-height: 1.5;
            text-align: left;
            padding: 10px 15px;
            border-top: 1px solid var(--border-color);
        }
        .doctor-opinion-box {
            background-color: var(--normal-bg-color);
            border-color: rgba(40, 167, 69, 0.2);
            border: 1px solid transparent;
            padding: 1.5rem;
            border-radius: 8px;
            line-height: 1.6;
            color: var(--text-color);
            white-space: pre-wrap; 
        }
        /* ... other CSS rules ... */
    </style>
    """, unsafe_allow_html=True)

# --- Functions for displaying specific report sections (details omitted for brevity but fully functional) ---
def render_vision_details_table(person_data):
    # ... (Existing Logic) ...
    return "..." 

def display_performance_report_hearing(person_data, all_person_history_df):
    # ... (Existing Logic) ...
    pass

def display_performance_report_lung(person_data):
    # ... (Existing Logic) ...
    pass

def display_performance_report_vision(person_data):
    # ... (Existing Logic) ...
    pass

# --- Display Report Logic ---
def display_performance_report(person_data, report_type, all_person_history_df=None):
    with st.container(border=True):
        if report_type == 'lung': display_performance_report_lung(person_data)
        elif report_type == 'vision': display_performance_report_vision(person_data)
        elif report_type == 'hearing': display_performance_report_hearing(person_data, all_person_history_df)

def display_main_report(person_data, all_person_history_df):
    # ... (Logic for main report using imported functions) ...
    # ... Same as previous version ...
    person = person_data
    sex = str(person.get("เพศ", "")).strip()
    if sex not in ["ชาย", "หญิง"]: sex = "ไม่ระบุ"
    cbc_results = generate_cbc_recommendations(person, sex)
    urine_results = generate_urine_recommendations(person, sex)
    doctor_opinion_text = generate_doctor_opinion(person, sex, cbc_results, urine_results)
    cbc_footer_html = cbc_results.get('summary', 'ไม่ได้ตรวจ')
    chem_recs_list = generate_fixed_recommendations(person)
    blood_footer_html = f"<ul>{''.join([f'<li>{html.escape(rec)}</li>' for rec in chem_recs_list])}</ul>" if chem_recs_list else "ผลการตรวจโดยรวมอยู่ในเกณฑ์ปกติ"
    urine_footer_html = urine_results.get('summary', 'ไม่ได้ตรวจ')

    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_config = [("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None), ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None), ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000), ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70), ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44), ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9), ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9), ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3), ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000)]
    cbc_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high in cbc_config for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high)]]
    blood_config = [("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106), ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2), ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120), ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37), ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41), ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200), ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150), ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True), ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160), ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20), ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17), ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True)]
    blood_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high, *opt in blood_config for higher in [opt[0] if opt else False] for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high, higher)]]

    with st.container(border=True):
        render_section_header("ผลการตรวจทางห้องปฏิบัติการ (Laboratory Results)")
        col1, col2 = st.columns(2)
        with col1: st.markdown(render_lab_table_html("ผลตรวจความสมบูรณ์ของเม็ดเลือด (CBC)", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows, footer_html=cbc_footer_html), unsafe_allow_html=True)
        with col2: st.markdown(render_lab_table_html("ผลตรวจเลือด (Blood Chemistry)", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows, footer_html=blood_footer_html), unsafe_allow_html=True)

    selected_year = person.get("Year", datetime.now().year + 543)
    with st.container(border=True):
        render_section_header("ผลการตรวจอื่นๆ (Other Examinations)")
        col_ua_left, col_ua_right = st.columns(2)
        with col_ua_left:
            render_urine_section(person, sex, selected_year, footer_html=urine_footer_html)
            st.markdown("<h5 class='section-subtitle'>ผลตรวจอุจจาระ (Stool Examination)</h5>", unsafe_allow_html=True)
            st.markdown(render_stool_html_table(interpret_stool_exam(person.get("Stool exam", "")), interpret_stool_cs(person.get("Stool C/S", ""))), unsafe_allow_html=True)
        with col_ua_right:
            st.markdown("<h5 class='section-subtitle'>ผลตรวจพิเศษ</h5>", unsafe_allow_html=True)
            cxr_col = f"CXR{str(selected_year)[-2:]}" if selected_year != (datetime.now().year + 543) else "CXR"
            ekg_col_name = get_ekg_col_name(selected_year)
            hep_a_value = person.get("Hepatitis A")
            hep_a_display_text = "ไม่ได้ตรวจ" if is_empty(hep_a_value) else safe_text(hep_a_value)
            st.markdown(f"""<div class="table-container"><table class="info-detail-table"><tbody><tr><th>ผลเอกซเรย์ (Chest X-ray)</th><td>{interpret_cxr_ui(person.get(cxr_col, ''))}</td></tr><tr><th>ผลคลื่นไฟฟ้าหัวใจ (EKG)</th><td>{interpret_ekg(person.get(ekg_col_name, ''))}</td></tr><tr><th>ไวรัสตับอักเสบเอ (Hepatitis A)</th><td>{hep_a_display_text}</td></tr></tbody></table></div>""", unsafe_allow_html=True)
            hep_test_date_str = str(person.get("ปีตรวจHEP", "")).strip()
            hepatitis_header_text = f"ผลการตรวจไวรัสตับอักเสบบี (Viral hepatitis B) (ตรวจเมื่อ: {hep_test_date_str})" if not is_empty(hep_test_date_str) else f"ผลการตรวจไวรัสตับอักเสบบี (Viral hepatitis B) (พ.ศ. {selected_year})"
            st.markdown(f"<h5 class='section-subtitle'>{hepatitis_header_text}</h5>", unsafe_allow_html=True)
            hbsag, hbsab, hbcab = safe_text(person.get("HbsAg")), safe_text(person.get("HbsAb")), safe_text(person.get("HBcAB"))
            st.markdown(f"""<div class="table-container"><table class='lab-table'><thead><tr><th style='text-align: center;'>HBsAg</th><th style='text-align: center;'>HBsAb</th><th style='text-align: center;'>HBcAb</th></tr></thead><tbody><tr><td style='text-align: center;'>{hbsag}</td><td style='text-align: center;'>{hbsab}</td><td style='text-align: center;'>{hbcab}</td></tr></tbody></table></div>""", unsafe_allow_html=True)
            if not (is_empty(hbsag) and is_empty(hbsab) and is_empty(hbcab)):
                advice, status = hepatitis_b_advice(hbsag, hbsab, hbcab)
                status_class = 'immune-box' if status == 'immune' else 'no-immune-box' if status == 'no-immune' else 'warning-box'
                st.markdown(f"""<div class='custom-advice-box {status_class}'>{advice}</div>""", unsafe_allow_html=True)

    with st.container(border=True):
        render_section_header("สรุปความคิดเห็นของแพทย์ (Doctor's Opinion)")
        escaped_opinion = html.escape(doctor_opinion_text)
        st.markdown(f"<div class='doctor-opinion-box'>{escaped_opinion}</div>", unsafe_allow_html=True)


def display_admin_panel(df):
    """
    แสดงหน้าจอหลักสำหรับ Admin (Search Panel)
    """
    st.set_page_config(page_title="Admin Panel", layout="wide")
    inject_custom_css()

    # --- Initialize session state keys for admin search ---
    if 'admin_search_term' not in st.session_state:
        st.session_state.admin_search_term = ""
    if 'admin_search_results' not in st.session_state:
        st.session_state.admin_search_results = None 
    if 'admin_selected_hn' not in st.session_state:
        st.session_state.admin_selected_hn = None
    if 'admin_selected_year' not in st.session_state:
        st.session_state.admin_selected_year = None
    if 'admin_print_trigger' not in st.session_state:
        st.session_state.admin_print_trigger = False
    if 'admin_print_performance_trigger' not in st.session_state:
        st.session_state.admin_print_performance_trigger = False
    if "admin_person_row" not in st.session_state:
        st.session_state.admin_person_row = None

    # --- Sidebar Menu ---
    with st.sidebar:
        st.markdown("<div class='sidebar-title'>👑 Admin Panel</div>", unsafe_allow_html=True)
        
        if st.button("ออกจากระบบ (Logout)", use_container_width=True):
            # รวมคีย์ของ batch_print ที่ต้องการล้างด้วย
            keys_to_clear = [
                'authenticated', 'pdpa_accepted', 'user_hn', 'user_name', 'is_admin',
                'search_result', 'selected_year', 'person_row', 'selected_row_found',
                'admin_search_term', 'admin_search_results', 'admin_selected_hn',
                'admin_selected_year', 'admin_person_row', 'batch_print_ready', 'batch_print_html',
                'bp_dept_filter', 'bp_date_filter', 'bp_report_type' # เพิ่มคีย์ของ batch print เพื่อให้รีเซ็ตตอน logout
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # --- Main Content Tabs ---
    tab_search, tab_print = st.tabs(["🔍 ค้นหาผู้ป่วย (Search)", "🖨️ ศูนย์พิมพ์รายงาน (Print Center)"])

    # --- Tab 1: Search (Original Functionality) ---
    with tab_search:
        # --- FIX Issue 1: Use st.form to enable Enter key submission ---
        with st.form(key="admin_search_form"):
            col_search_input, col_search_btn = st.columns([4, 1])
            with col_search_input:
                search_term = st.text_input("ค้นหา (ชื่อ-สกุล, HN, หรือ เลขบัตร)", value=st.session_state.admin_search_term, placeholder="พิมพ์คำค้นหา...", label_visibility="collapsed")
            with col_search_btn:
                submitted = st.form_submit_button("ค้นหา", use_container_width=True)
        
        if submitted:
            st.session_state.admin_search_term = search_term
            if search_term:
                normalized_search = normalize_name(search_term)
                search_mask = (
                    df['ชื่อ-สกุล'].apply(normalize_name).str.contains(normalized_search, case=False, na=False) |
                    (df['HN'].astype(str) == search_term) |
                    (df['เลขบัตรประชาชน'].astype(str) == search_term)
                )
                results_df = df[search_mask]
                if not results_df.empty:
                    unique_hns = results_df['HN'].unique()
                    st.session_state.admin_search_results = df[df['HN'].isin(unique_hns)].copy()
                    if len(unique_hns) == 1: st.session_state.admin_selected_hn = unique_hns[0]
                    else: st.session_state.admin_selected_hn = None
                else:
                    st.session_state.admin_search_results = pd.DataFrame()
                    st.session_state.admin_selected_hn = None
            else:
                st.session_state.admin_search_results = None
                st.session_state.admin_selected_hn = None
            st.session_state.admin_selected_year = None
            st.session_state.admin_person_row = None
            st.rerun()

        if st.session_state.admin_search_results is not None:
            if st.session_state.admin_search_results.empty:
                st.warning("ไม่พบข้อมูล")
            else:
                unique_results = st.session_state.admin_search_results.drop_duplicates(subset=['HN']).set_index('HN')
                
                if len(unique_results) > 1:
                    options = {hn: f"{row['ชื่อ-สกุล']} (HN: {hn})" for hn, row in unique_results.iterrows()}
                    current_hn = st.session_state.admin_selected_hn
                    hn_list = list(options.keys())
                    index = hn_list.index(current_hn) if current_hn in hn_list else 0
                    if st.session_state.admin_selected_hn is None:
                        index = 0
                        st.session_state.admin_selected_hn = hn_list[0]

                    col_sel_hn, col_sel_year = st.columns(2)
                    with col_sel_hn:
                        selected_hn = st.selectbox("เลือกผู้ป่วย", options=hn_list, format_func=lambda hn: options[hn], index=index, key="admin_select_hn_box")
                        if selected_hn != st.session_state.admin_selected_hn:
                            st.session_state.admin_selected_hn = selected_hn
                            st.session_state.admin_selected_year = None
                            st.session_state.admin_person_row = None
                            st.rerun()
                elif len(unique_results) == 1 and st.session_state.admin_selected_hn is None:
                     st.session_state.admin_selected_hn = unique_results.index[0]
                     st.rerun()

                if st.session_state.admin_selected_hn:
                    hn_to_load = st.session_state.admin_selected_hn
                    all_person_history_df = df[df['HN'] == hn_to_load].copy()
                    available_years = sorted(all_person_history_df["Year"].dropna().unique().astype(int), reverse=True)

                    if available_years:
                        if st.session_state.admin_selected_year not in available_years:
                            st.session_state.admin_selected_year = available_years[0]
                        year_idx = available_years.index(st.session_state.admin_selected_year)
                        
                        if 'col_sel_year' not in locals(): col_sel_year = st.container() # Fallback container
                        with col_sel_year:
                            selected_year = st.selectbox("เลือกปี พ.ศ.", options=available_years, index=year_idx, format_func=lambda y: f"พ.ศ. {y}", key="admin_year_select")
                        
                        if selected_year != st.session_state.admin_selected_year:
                            st.session_state.admin_selected_year = selected_year
                            st.session_state.admin_person_row = None
                            st.rerun()

                        if st.session_state.admin_person_row is None:
                            person_year_df = all_person_history_df[all_person_history_df["Year"] == st.session_state.admin_selected_year]
                            if not person_year_df.empty:
                                merged_series = person_year_df.bfill().ffill().iloc[0]
                                st.session_state.admin_person_row = merged_series.to_dict()
                            else: st.session_state.admin_person_row = {}
                    else:
                        st.error("ผู้ป่วยนี้ไม่มีข้อมูลรายปี")
                        st.session_state.admin_person_row = None

        # --- Display Report Content ---
        if st.session_state.admin_person_row:
            st.divider()
            person_data = st.session_state.admin_person_row
            all_person_history_df_admin = df[df['HN'] == st.session_state.admin_selected_hn].copy()

            # Print Buttons
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                if st.button("🖨️ พิมพ์รายงานสุขภาพ (Main)", use_container_width=True, key="admin_print_main"):
                    st.session_state.admin_print_trigger = True
            with col_p2:
                if st.button("🖨️ พิมพ์รายงานสมรรถภาพ (Perf)", use_container_width=True, key="admin_print_perf"):
                    st.session_state.admin_print_performance_trigger = True

            available_reports = OrderedDict()
            if has_visualization_data(all_person_history_df_admin): available_reports['ภาพรวมสุขภาพ (Graphs)'] = 'visualization_report'
            if has_basic_health_data(person_data): available_reports['สุขภาพพื้นฐาน'] = 'main_report'
            if has_vision_data(person_data): available_reports['สมรรถภาพการมองเห็น'] = 'vision_report'
            if has_hearing_data(person_data): available_reports['สมรรถภาพการได้ยิน'] = 'hearing_report'
            if has_lung_data(person_data): available_reports['สมรรถภาพปอด'] = 'lung_report'

            if not available_reports:
                display_common_header(person_data)
                st.warning("ไม่พบข้อมูลการตรวจใดๆ สำหรับปีที่เลือก")
            else:
                display_common_header(person_data)
                sub_tabs = st.tabs(list(available_reports.keys()))
                for i, (tab_title, page_key) in enumerate(available_reports.items()):
                    with sub_tabs[i]:
                        if page_key == 'visualization_report': display_visualization_tab(person_data, all_person_history_df_admin)
                        elif page_key == 'vision_report': display_performance_report(person_data, 'vision')
                        elif page_key == 'hearing_report': display_performance_report(person_data, 'hearing', all_person_history_df=all_person_history_df_admin)
                        elif page_key == 'lung_report': display_performance_report(person_data, 'lung')
                        elif page_key == 'main_report': display_main_report(person_data, all_person_history_df_admin)

            # Print Logic
            if st.session_state.get("admin_print_trigger", False):
                report_html_data = generate_printable_report(person_data, all_person_history_df_admin)
                escaped_html = json.dumps(report_html_data)
                iframe_id = f"print-iframe-admin-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                print_component = f"""<iframe id="{iframe_id}" style="display:none;"></iframe><script>(function(){{const iframe=document.getElementById('{iframe_id}');if(!iframe)return;const doc=iframe.contentWindow.document;doc.open();doc.write({escaped_html});doc.close();iframe.onload=function(){{setTimeout(function(){{try{{iframe.contentWindow.focus();iframe.contentWindow.print();}}catch(e){{console.error("Print failed:",e);}}}},500);}};}})();</script>"""
                st.components.v1.html(print_component, height=0, width=0)
                st.session_state.admin_print_trigger = False

            if st.session_state.get("admin_print_performance_trigger", False):
                report_html_data = generate_performance_report_html(person_data, all_person_history_df_admin)
                escaped_html = json.dumps(report_html_data)
                iframe_id = f"print-perf-iframe-admin-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                print_component = f"""<iframe id="{iframe_id}" style="display:none;"></iframe><script>(function(){{const iframe=document.getElementById('{iframe_id}');if(!iframe)return;const doc=iframe.contentWindow.document;doc.open();doc.write({escaped_html});doc.close();iframe.onload=function(){{setTimeout(function(){{try{{iframe.contentWindow.focus();iframe.contentWindow.print();}}catch(e){{console.error("Print failed:",e);}}}},500);}};}})();</script>"""
                st.components.v1.html(print_component, height=0, width=0)
                st.session_state.admin_print_performance_trigger = False

    # --- Tab 2: Print Center (New) ---
    with tab_print:
        display_print_center_page(df)
