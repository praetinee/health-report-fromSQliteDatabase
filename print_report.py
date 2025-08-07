import pandas as pd
from datetime import datetime
import re
import html
from collections import OrderedDict
import json

# --- แก้ไข: import ฟังก์ชัน generate_holistic_advice และฟังก์ชันสำหรับรายงานสมรรถภาพ ---
from performance_tests import generate_holistic_advice
from print_performance_report import generate_performance_report_html_for_main_report

# ==============================================================================
# หมายเหตุ: ไฟล์นี้มีฟังก์ชันที่จำเป็นสำหรับการสร้างรายงานในรูปแบบ HTML
# ฟังก์ชันส่วนใหญ่ถูกคัดลอกมาจาก app.py และปรับเปลี่ยนเพื่อสร้างผลลัพธ์เป็นสตริง HTML
# แทนการแสดงผลบน Streamlit โดยตรง
# ==============================================================================


# --- Helper Functions (คัดลอกมาจาก app.py) ---

def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]


THAI_MONTHS_GLOBAL = {
    1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน",
    5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม",
    9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"
}

def get_float(col, person_data):
    """Safely gets a float value from person_data dictionary."""
    try:
        val = person_data.get(col, "")
        if is_empty(val):
            return None
        return float(str(val).replace(",", "").strip())
    except:
        return None

def flag(val, low=None, high=None, higher_is_better=False):
    """
    ตรวจสอบค่าและจัดรูปแบบตัวเลขสำหรับตารางผลตรวจ
    - ตัวเลขจำนวนเต็มจะใส่ comma แต่ไม่มีทศนิยม
    - ตัวเลขทศนิยมจะใส่ comma และมีทศนิยม 1 ตำแหน่ง
    """
    try:
        val_float = float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return "-", False

    # Smart formatting
    if val_float == int(val_float):
        # เป็นจำนวนเต็ม, จัดรูปแบบด้วย comma
        formatted_val = f"{int(val_float):,}"
    else:
        # เป็นทศนิยม, จัดรูปแบบด้วย comma และทศนิยม 1 ตำแหน่ง
        formatted_val = f"{val_float:,.1f}"

    is_abn = False
    if higher_is_better:
        if low is not None and val_float < low:
            is_abn = True
    else:
        if low is not None and val_float < low:
            is_abn = True
        if high is not None and val_float > high:
            is_abn = True

    return formatted_val, is_abn

def safe_text(val):
    return "-" if str(val).strip().lower() in ["", "none", "nan", "-"] else str(val).strip()

def safe_value(val):
    val = str(val or "").strip()
    if val.lower() in ["", "nan", "none", "-"]:
        return "-"
    return val

def interpret_bp(sbp, dbp):
    """Interprets blood pressure readings."""
    try:
        sbp = float(sbp)
        dbp = float(dbp)
        if sbp == 0 or dbp == 0:
            return "-"
        if sbp >= 160 or dbp >= 100:
            return "ความดันสูง"
        elif sbp >= 140 or dbp >= 90:
            return "ความดันสูงเล็กน้อย"
        elif sbp < 120 and dbp < 80:
            return "ความดันปกติ"
        else:
            return "ความดันค่อนข้างสูง"
    except:
        return "-"

def parse_range_or_number(val):
    val = val.replace("cell/hpf", "").replace("cells/hpf", "").replace("cell", "").strip().lower()
    try:
        if "-" in val:
            low, high = map(float, val.split("-"))
            return low, high
        else:
            num = float(val)
            return num, num
    except:
        return None, None
    
def interpret_rbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]:
        return "-"
    low, high = parse_range_or_number(val)
    if high is None:
        return value
    if high <= 2:
        return "ปกติ"
    elif high <= 5:
        return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
    else:
        return "พบเม็ดเลือดแดงในปัสสาวะ"
    
def interpret_wbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]:
        return "-"
    low, high = parse_range_or_number(val)
    if high is None:
        return value
    if high <= 5:
        return "ปกติ"
    elif high <= 10:
        return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    else:
        return "พบเม็ดเลือดขาวในปัสสาวะ"

def is_urine_abnormal(test_name, value, normal_range):
    val = str(value or "").strip().lower()
    if val in ["", "-", "none", "nan", "null"]:
        return False
    
    if test_name == "กรด-ด่าง (pH)":
        try:
            return not (5.0 <= float(val) <= 8.0)
        except:
            return True
    
    if test_name == "ความถ่วงจำเพาะ (Sp.gr)":
        try:
            return not (1.003 <= float(val) <= 1.030)
        except:
            return True
    
    if test_name == "เม็ดเลือดแดง (RBC)":
        return "พบ" in interpret_rbc(val).lower()
    
    if test_name == "เม็ดเลือดขาว (WBC)":
        return "พบ" in interpret_wbc(val).lower()
    
    if test_name == "น้ำตาล (Sugar)":
        return val.lower() not in ["negative"]
    
    if test_name == "โปรตีน (Albumin)":
        return val.lower() not in ["negative", "trace"]
    
    if test_name == "สี (Colour)":
        return val not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"]
    
    return False

def interpret_stool_exam(val):
    if is_empty(val):
        return "ไม่ได้เข้ารับการตรวจ"
    val_lower = str(val).strip().lower()
    if val_lower == "normal":
        return "ไม่พบเม็ดเลือดขาวในอุจจาระ ถือว่าปกติ"
    elif "wbc" in val_lower or "เม็ดเลือดขาว" in val_lower:
        return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
    return val

def interpret_stool_cs(value):
    if is_empty(value):
        return "ไม่ได้เข้ารับการตรวจ"
    val_strip = str(value).strip()
    if "ไม่พบ" in val_strip or "ปกติ" in val_strip:
        return "ไม่พบการติดเชื้อ"
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"

def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val):
        return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def get_ekg_col_name(year):
    current_thai_year = datetime.now().year + 543
    return "EKG" if year == current_thai_year else f"EKG{str(year)[-2:]}"

def interpret_ekg(val):
    val = str(val or "").strip()
    if is_empty(val):
        return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def hepatitis_b_advice(hbsag, hbsab, hbcab):
    """
    ให้คำแนะนำเกี่ยวกับไวรัสตับอักเสบบี และคืนค่าสถานะเพื่อใช้ในการไฮไลต์
    Returns: (advice_string, status_flag)
    status_flag: 'infection', 'no_immunity', 'normal'
    """
    hbsag = hbsag.lower()
    hbsab = hbsab.lower()
    hbcab = hbcab.lower()
    
    if "positive" in hbsag:
        return "ติดเชื้อไวรัสตับอักเสบบี", "infection"
    elif all(x == "negative" for x in [hbsag, hbsab, hbcab]):
        return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน", "no_immunity"
    elif "positive" in hbsab and "positive" not in hbsag:
        return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี", "normal"
    elif "positive" in hbcab and "positive" not in hbsab:
        return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน", "normal"
    
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ", "normal"

# --- HTML Rendering Functions ---

def render_section_header(title, subtitle=None):
    if subtitle:
        full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>"
    else:
        full_title = title

    return f"""
    <div style='
        background-color: #f0f2f6;
        color: #333;
        text-align: center;
        padding: 0.2rem 0.4rem;
        font-weight: bold;
        border-radius: 6px;
        margin-top: 1rem;
        margin-bottom: 0.4rem;
        font-size: 11px;
        border: 1px solid #ddd;
    '>
        {full_title}
    </div>
    """

def render_lab_table_html(title, subtitle, headers, rows, table_class="print-lab-table"):
    header_html = render_section_header(title, subtitle)
    
    html_content = f"{header_html}<table class='{table_class}'>"
    html_content += """
        <colgroup>
            <col style="width: 40%;">
            <col style="width: 20%;">
            <col style="width: 40%;">
        </colgroup>
    """
    html_content += "<thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i == 0 or i == 2 else "center"
        html_content += f"<th style='text-align: {align};'>{h}</th>"
    html_content += "</tr></thead><tbody>"
    
    for row in rows:
        is_abn = any(flag for _, flag in row)
        row_class = f"{table_class}-abn" if is_abn else ""
        
        html_content += f"<tr class='{row_class}'>"
        html_content += f"<td style='text-align: left;'>{row[0][0]}</td>"
        html_content += f"<td>{row[1][0]}</td>"
        html_content += f"<td style='text-align: left;'>{row[2][0]}</td>"
        html_content += f"</tr>"
    html_content += "</tbody></table>"
    return html_content


def render_html_header(person):
    check_date = person.get("วันที่ตรวจ", "-")
    return f"""
    <div class="report-header-container" style="text-align: center; margin-bottom: 0.5rem; margin-top: 0.5rem;">
        <h1 style="font-size: 1.2rem; margin:0;">รายงานผลการตรวจสุขภาพ</h1>
        <h2 style="font-size: 0.8rem; margin:0;">- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม -</h2>
        <p style="font-size: 0.7rem; margin:0;">ชั้น 2 อาคารผู้ป่วยนอก-อุบัติเหตุ โรงพยาบาลสันทราย 201 หมู่ 11 ถ.เชียงใหม่–พร้าว ต.หนองหาร อ.สันทราย จ.เชียงใหม่ 50290</p>
        <p style="font-size: 0.7rem; margin:0;">ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167 | <b>วันที่ตรวจ:</b> {check_date or "-"}</p>
    </div>
    """

def render_personal_info(person):
    sbp = person.get("SBP", "")
    dbp = person.get("DBP", "")
    
    try:
        sbp_int = int(float(sbp))
        dbp_int = int(float(dbp))
        bp_val = f"{sbp_int}/{dbp_int} ม.ม.ปรอท"
    except:
        sbp_int = dbp_int = None
        bp_val = "-"
    
    # จัดการค่าชีพจร (Pulse) ให้เป็นเลขจำนวนเต็ม
    pulse_raw = person.get("pulse", "-")
    pulse_val = "-"
    if not is_empty(pulse_raw):
        try:
            # แปลงเป็น float ก่อนเพื่อรองรับค่าเช่น "75.0" แล้วจึงแปลงเป็น int
            pulse_val = str(int(float(pulse_raw)))
        except (ValueError, TypeError):
            pulse_val = safe_text(pulse_raw) # ใช้ค่าเดิมหากแปลงไม่ได้

    bp_desc = interpret_bp(sbp, dbp)
    bp_full = f"{bp_val} ({bp_desc})" if bp_desc != "-" else bp_val
    
    return f"""
    <div class="personal-info-container">
        <hr style="margin-top: 0.5rem; margin-bottom: 0.5rem;">
        <table class="info-table">
            <tr>
                <td><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</td>
                <td><b>อายุ:</b> {str(int(float(person.get('อายุ')))) if str(person.get('อายุ')).replace('.', '', 1).isdigit() else person.get('อายุ', '-')} ปี</td>
                <td><b>เพศ:</b> {person.get('เพศ', '-')}</td>
                <td><b>HN:</b> {str(int(float(person.get('HN')))) if str(person.get('HN')).replace('.', '', 1).isdigit() else person.get('HN', '-')}</td>
            </tr>
            <tr>
                <td><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</td>
                <td><b>น้ำหนัก:</b> {person.get("น้ำหนัก", "-")} กก.</td>
                <td><b>ส่วนสูง:</b> {person.get("ส่วนสูง", "-")} ซม.</td>
                <td><b>รอบเอว:</b> {person.get("รอบเอว", "-")} ซม.</td>
            </tr>
             <tr>
                <td colspan="2"><b>ความดันโลหิต:</b> {bp_full}</td>
                <td colspan="2"><b>ชีพจร:</b> {pulse_val} ครั้ง/นาที</td>
            </tr>
        </table>
    </div>
    """

def render_lab_section(person, sex):
    # CBC Data
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)

    cbc_config = [
        ("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None),
        ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None),
        ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000),
        ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70),
        ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44),
        ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9),
        ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9),
        ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3),
        ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000),
    ]
    cbc_rows = []
    for label, col, norm, low, high in cbc_config:
        val = get_float(col, person)
        result, is_abn = flag(val, low, high)
        cbc_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])
    
    # Blood Chemistry Data
    blood_config = [
        ("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106),
        ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2),
        ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120),
        ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37),
        ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41),
        ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200),
        ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150),
        ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True),
        ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160),
        ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20),
        ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17),
        ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True)
    ]
    blood_rows = []
    for label, col, norm, low, high, *opt in blood_config:
        higher = opt[0] if opt else False
        val = get_float(col, person)
        result, is_abn = flag(val, low, high, higher)
        blood_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])

    cbc_html = render_lab_table_html("ผลตรวจ CBC (Complete Blood Count)", None, ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows, "print-lab-table")
    blood_html = render_lab_table_html("ผลตรวจเลือด (Blood Chemistry)", None, ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows, "print-lab-table")
    
    return f"""
    <table style="width: 100%; border-collapse: collapse; page-break-inside: avoid;">
        <tr>
            <td style="width: 50%; vertical-align: top; padding-right: 5px;">{cbc_html}</td>
            <td style="width: 50%; vertical-align: top; padding-left: 5px;">{blood_html}</td>
        </tr>
    </table>
    """

def render_other_results_html(person, sex):
    # Urinalysis
    urine_data = [
        ("สี (Colour)", "Color", "Yellow, Pale Yellow"),
        ("น้ำตาล (Sugar)", "sugar", "Negative"),
        ("โปรตีน (Albumin)", "Alb", "Negative, trace"),
        ("กรด-ด่าง (pH)", "pH", "5.0 - 8.0"),
        ("ความถ่วงจำเพาะ (Sp.gr)", "Spgr", "1.003 - 1.030"),
        ("เม็ดเลือดแดง (RBC)", "RBC1", "0 - 2 cell/HPF"),
        ("เม็ดเลือดขาว (WBC)", "WBC1", "0 - 5 cell/HPF"),
        ("เซลล์เยื่อบุผิว (Squam.epit.)", "SQ-epi", "0 - 10 cell/HPF"),
        ("อื่นๆ", "ORTER", "-"),
    ]
    urine_rows = []
    for label, key, norm in urine_data:
        val = person.get(key, "-")
        is_abn = is_urine_abnormal(label, val, norm)
        urine_rows.append([(label, is_abn), (safe_value(val), is_abn), (norm, is_abn)])
    urine_html = render_lab_table_html("ผลการตรวจปัสสาวะ", "Urinalysis", ["การตรวจ", "ผลตรวจ", "ค่าปกติ"], urine_rows, "print-lab-table")

    # Stool
    stool_exam_raw = person.get("Stool exam", "")
    stool_cs_raw = person.get("Stool C/S", "")
    stool_exam_text = interpret_stool_exam(stool_exam_raw)
    stool_cs_text = interpret_stool_cs(stool_cs_raw)
    stool_html = f"""
    {render_section_header("ผลตรวจอุจจาระ (Stool Examination)")}
    <table class="print-lab-table">
        <tr><td style="text-align: left; width: 40%;"><b>ผลตรวจอุจจาระทั่วไป</b></td><td style="text-align: left;">{stool_exam_text}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>ผลตรวจอุจจาระเพาะเชื้อ</b></td><td style="text-align: left;">{stool_cs_text}</td></tr>
    </table>
    """

    # Other tests
    year = person.get("Year", datetime.now().year + 543)
    cxr_result = interpret_cxr(person.get(f"CXR{str(year)[-2:]}" if year != (datetime.now().year+543) else "CXR", ""))
    ekg_result = interpret_ekg(person.get(get_ekg_col_name(year), ""))
    other_tests_html = f"""
    {render_section_header("ผลตรวจอื่นๆ")}
    <table class="print-lab-table">
        <tr><td style="text-align: left; width: 40%;"><b>ผลเอกซเรย์ (Chest X-ray)</b></td><td style="text-align: left;">{cxr_result}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>ผลคลื่นไฟฟ้าหัวใจ (EKG)</b></td><td style="text-align: left;">{ekg_result}</td></tr>
    </table>
    """

    # Hepatitis
    hep_a_value = person.get("Hepatitis A")
    hep_a_display_text = "ไม่ได้เข้ารับการตรวจไวรัสตับอักเสบเอ" if is_empty(hep_a_value) else safe_text(hep_a_value)
    hbsag_raw = safe_text(person.get("HbsAg"))
    hbsab_raw = safe_text(person.get("HbsAb"))
    hbcab_raw = safe_text(person.get("HBcAB"))
    hep_b_advice, hep_b_status = hepatitis_b_advice(hbsag_raw, hbsab_raw, hbcab_raw)

    advice_bg_color = "#f8f9fa"  # default gray
    if hep_b_status == 'infection':
        advice_bg_color = '#ffdddd'  # red highlight
    elif hep_b_status == 'no_immunity':
        advice_bg_color = '#fff8e1'  # yellow highlight

    hepatitis_html = f"""
    {render_section_header("ผลตรวจไวรัสตับอักเสบ (Viral Hepatitis)")}
    <table class="print-lab-table">
        <tr><td style="text-align: left; width: 40%;"><b>ไวรัสตับอักเสบ เอ</b></td><td style="text-align: left;">{hep_a_display_text}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>ไวรัสตับอักเสบ บี (HBsAg)</b></td><td style="text-align: left;">{hbsag_raw}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>ภูมิคุ้มกัน (HBsAb)</b></td><td style="text-align: left;">{hbsab_raw}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>การติดเชื้อ (HBcAb)</b></td><td style="text-align: left;">{hbcab_raw}</td></tr>
        <tr style="background-color: {advice_bg_color};"><td colspan="2" style="text-align: left;"><b>คำแนะนำ:</b> {hep_b_advice}</td></tr>
    </table>
    """

    # จัดเรียง Layout ใหม่
    return f"""
    <table style="width: 100%; border-collapse: collapse; page-break-inside: avoid;">
        <tr>
            <td style="width: 50%; vertical-align: top; padding-right: 5px;">
                {urine_html}
                {stool_html}
            </td>
            <td style="width: 50%; vertical-align: top; padding-left: 5px;">
                {other_tests_html}
                {hepatitis_html}
            </td>
        </tr>
    </table>
    """

def generate_printable_report(person_data, all_person_history_df=None):
    """
    Generates a full, self-contained HTML string for the health report.
    """
    sex = str(person_data.get("เพศ", "")).strip()
    if sex not in ["ชาย", "หญิง"]: sex = "ไม่ระบุ"
    
    # --- Generate all HTML parts ---
    header_html = render_html_header(person_data)
    personal_info_html = render_personal_info(person_data)
    lab_section_html = render_lab_section(person_data, sex)
    other_results_html = render_other_results_html(person_data, sex)
    
    # --- แก้ไข: เรียกใช้ฟังก์ชัน generate_holistic_advice เพื่อให้ข้อมูลตรงกัน ---
    doctor_suggestion = generate_holistic_advice(person_data)
    doctor_suggestion_html = f"""
    <div class="advice-box" style="background-color: #e8f5e9; border-color: #a5d6a7;">
        <div class="advice-title" style="color: #1b5e20;">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 5px;"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="m9 12 2 2 4-4"></path></svg>
            สรุปและคำแนะนำจากแพทย์ (Doctor's Summary & Recommendations)
        </div>
        <div class="advice-content">{doctor_suggestion}</div>
    </div>
    """

    # --- ส่วนของรายงานสมรรถภาพ ---
    performance_report_html = generate_performance_report_html_for_main_report(person_data, all_person_history_df)


    # --- Signature ---
    signature_html = """
    <div style="margin-top: 2rem; text-align: right; padding-right: 1rem; page-break-inside: avoid;">
        <div style="display: inline-block; text-align: center; width: 280px;">
            <div style="border-bottom: 1px dotted #333; margin-bottom: 0.4rem; width: 100%;"></div>
            <div style="white-space: nowrap;">นายแพทย์นพรัตน์ รัชฎาพร</div>
            <div style="white-space: nowrap;">แพทย์อาชีวเวชศาสตร์</div>
            <div style="white-space: nowrap;">เลขที่ใบอนุญาตฯ ว.26674</div>
        </div>
    </div>
    """

    # --- Assemble the final HTML page ---
    final_html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลการตรวจสุขภาพ - {html.escape(person_data.get('ชื่อ-สกุล', ''))}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
            body {{
                font-family: 'Sarabun', sans-serif !important;
                font-size: 9.5px;
                margin: 10mm;
                color: #333;
                background-color: #fff;
            }}
            p, div, span, td, th {{ line-height: 1.4; }}
            table {{ border-collapse: collapse; width: 100%; }}
            .print-lab-table td, .print-lab-table th {{
                padding: 2px 4px;
                border: 1px solid #ccc;
                text-align: center;
                vertical-align: middle;
            }}
            .print-lab-table th {{ background-color: #f2f2f2; font-weight: bold; }}
            .print-lab-table-abn {{ background-color: #fff1f0 !important; }}
            .info-table {{ font-size: 10px; text-align: left; }}
            .info-table td {{ padding: 2px 5px; border: none; }}
            .advice-box {{
                padding: 0.5rem 1rem;
                border-radius: 8px;
                line-height: 1.5;
                margin-top: 0.5rem;
                border: 1px solid #ddd;
                page-break-inside: avoid;
            }}
            .advice-title {{ font-weight: bold; margin-bottom: 0.3rem; font-size: 11px; }}
            .advice-content ul {{ padding-left: 20px; margin: 0; }}
            .advice-content li {{ margin-bottom: 4px; }}

            /* Performance Report Styles */
            .perf-section {{
                margin-top: 0.5rem;
                page-break-inside: avoid;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 0.5rem;
            }}
            .perf-columns {{
                display: flex;
                gap: 10px;
                align-items: flex-start;
            }}
            .perf-col-summary {{ flex: 1; min-width: 150px; }}
            .perf-col-details {{ flex: 2; min-width: 250px; }}
            .summary-box {{
                background-color: #f8f9fa;
                border-radius: 4px;
                padding: 4px 8px;
                margin-top: 2px;
                font-size: 9px;
            }}
            .perf-table {{ width: 100%; font-size: 9px; }}
            .perf-table th, .perf-table td {{
                border: 1px solid #e0e0e0;
                padding: 2px 4px;
                text-align: center;
            }}
            .perf-table th {{ background-color: #f2f2f2; }}
            .status-ok {{ background-color: #e8f5e9; color: #1b5e20; }}
            .status-abn {{ background-color: #ffcdd2; color: #b71c1c; }}
            .status-nt {{ background-color: #f5f5f5; color: #616161; }}

            @media print {{
                body {{ -webkit-print-color-adjust: exact; margin: 0; }}
            }}
        </style>
    </head>
    <body>
        {header_html}
        {personal_info_html}
        {lab_section_html}
        {other_results_html}
        {performance_report_html}
        {doctor_suggestion_html}
        {signature_html}
    </body>
    </html>
    """
    return final_html
