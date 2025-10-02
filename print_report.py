import pandas as pd
from datetime import datetime
import html
from collections import OrderedDict
import json

# --- Import a key function from performance_tests ---
from performance_tests import generate_holistic_advice
from print_performance_report import generate_performance_report_html_for_main_report

# ==============================================================================
# NOTE: This file generates the printable health report.
# The header is compact, while the body retains the original layout.
# ==============================================================================


# --- Helper Functions (adapted from app.py for printing) ---

def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def get_float(col, person_data):
    """Safely gets a float value from person_data dictionary."""
    try:
        val = person_data.get(col, "")
        if is_empty(val): return None
        return float(str(val).replace(",", "").strip())
    except: return None

def flag(val, low=None, high=None, higher_is_better=False):
    """Formats a lab value and flags it if it's abnormal for styling."""
    try:
        val_float = float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return "-", False
    
    formatted_val = f"{int(val_float):,}" if val_float == int(val_float) else f"{val_float:,.1f}"
    
    is_abn = False
    if higher_is_better:
        if low is not None and val_float < low: is_abn = True
    else:
        if low is not None and val_float < low: is_abn = True
        if high is not None and val_float > high: is_abn = True
        
    return formatted_val, is_abn

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

def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def get_ekg_col_name(year):
    current_thai_year = datetime.now().year + 543
    return "EKG" if year == current_thai_year else f"EKG{str(year)[-2:]}"

def interpret_ekg(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def hepatitis_b_advice(hbsag, hbsab, hbcab):
    hbsag, hbsab, hbcab = hbsag.lower(), hbsab.lower(), hbcab.lower()
    if "positive" in hbsag: return "ติดเชื้อไวรัสตับอักเสบบี", "infection"
    if "positive" in hbsab and "positive" not in hbsag: return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี", "immune"
    if "positive" in hbcab and "positive" not in hbsab: return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน", "unclear"
    if all(x == "negative" for x in [hbsag, hbsab, hbcab]): return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน", "no_immune"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ", "unclear"

# --- HTML Rendering Functions ---

def render_section_header(title, subtitle=None):
    full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
    return f"""
    <div style='background-color: #f0f2f6; color: #333; text-align: center; padding: 0.2rem 0.4rem; font-weight: bold; border-radius: 6px; margin-top: 1rem; margin-bottom: 0.4rem; font-size: 11px; border: 1px solid #ddd;'>
        {full_title}
    </div>
    """

def render_lab_table_html(title, subtitle, headers, rows, table_class="print-lab-table"):
    header_html = render_section_header(title, subtitle)
    html_content = f"{header_html}<table class='{table_class}'><colgroup><col style='width: 40%;'><col style='width: 20%;'><col style='width: 40%;'></colgroup><thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i == 0 or i == 2 else "center"
        html_content += f"<th style='text-align: {align};'>{h}</th>"
    html_content += "</tr></thead><tbody>"
    for row in rows:
        is_abn = any(flag for _, flag in row)
        row_class = f"{table_class}-abn" if is_abn else ""
        html_content += f"<tr class='{row_class}'><td style='text-align: left;'>{row[0][0]}</td><td>{row[1][0]}</td><td style='text-align: left;'>{row[2][0]}</td></tr>"
    html_content += "</tbody></table>"
    return html_content

def render_header_and_vitals(person_data):
    """Renders the compact header and personal info table for the print report."""
    name = person_data.get('ชื่อ-สกุล', '-')
    age = str(int(float(person_data.get('อายุ')))) if str(person_data.get('อายุ')).replace('.', '', 1).isdigit() else person_data.get('อายุ', '-')
    sex = person_data.get('เพศ', '-')
    hn = str(int(float(person_data.get('HN')))) if str(person_data.get('HN')).replace('.', '', 1).isdigit() else person_data.get('HN', '-')
    department = person_data.get('หน่วยงาน', '-')
    check_date = person_data.get("วันที่ตรวจ", "-")
    sbp, dbp = get_float("SBP", person_data), get_float("DBP", person_data)
    bp_val = f"{int(sbp)}/{int(dbp)} ม.ม.ปรอท" if sbp and dbp else "-"
    pulse_val = f"{int(get_float('pulse', person_data))} ครั้ง/นาที" if get_float('pulse', person_data) else "-"
    weight = get_float('น้ำหนัก', person_data)
    height = get_float('ส่วนสูง', person_data)
    weight_val = f"{weight} กก." if weight else "-"
    height_val = f"{height} ซม." if height else "-"
    waist_val = f"{person_data.get('รอบเอว', '-')} ซม." if not is_empty(person_data.get('รอบเอว')) else "-"
    return f"""
    <div class="header-grid">
        <div class="header-left">
            <h1 style="font-size: 1.5rem; margin:0;">รายงานผลการตรวจสุขภาพ</h1>
            <p style="font-size: 0.8rem; margin:0;">คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม โรงพยาบาลสันทราย</p>
            <p style="font-size: 0.8rem; margin:0;"><b>วันที่ตรวจ:</b> {check_date}</p>
        </div>
        <div class="header-right">
            <table class="info-table">
                <tr>
                    <td><b>ชื่อ-สกุล:</b> {name}</td>
                    <td><b>อายุ:</b> {age} ปี</td>
                    <td><b>เพศ:</b> {sex}</td>
                    <td><b>HN:</b> {hn}</td>
                </tr>
                <tr>
                    <td><b>หน่วยงาน:</b> {department}</td>
                    <td><b>น้ำหนัก:</b> {weight_val}</td>
                    <td><b>ส่วนสูง:</b> {height_val}</td>
                    <td><b>รอบเอว:</b> {waist_val}</td>
                </tr>
                 <tr>
                    <td colspan="2"><b>ความดันโลหิต:</b> {bp_val}</td>
                    <td colspan="2"><b>ชีพจร:</b> {pulse_val}</td>
                </tr>
            </table>
        </div>
    </div>
    <hr style="border: 0; border-top: 1px solid #e0e0e0; margin: 0.5rem 0;">
    """

def render_lab_section(person, sex):
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_config = [("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None), ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None), ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000), ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70), ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44), ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9), ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9), ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3), ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000)]
    cbc_rows = [[(label, is_abn), (result, is_abn), (norm, is_abn)] for label, col, norm, low, high in cbc_config for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high)]]
    blood_config = [("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106), ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2), ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120), ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37), ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41), ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200), ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150), ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True), ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160), ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20), ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17), ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True)]
    blood_rows = [[(label, is_abn), (result, is_abn), (norm, is_abn)] for label, col, norm, low, high, *opt in blood_config for higher in [opt[0] if opt else False] for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high, higher)]]
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
    urine_data = [("สี (Colour)", "Color", "Yellow, Pale Yellow"), ("น้ำตาล (Sugar)", "sugar", "Negative"), ("โปรตีน (Albumin)", "Alb", "Negative, trace"), ("กรด-ด่าง (pH)", "pH", "5.0 - 8.0"), ("ความถ่วงจำเพาะ (Sp.gr)", "Spgr", "1.003 - 1.030"), ("เม็ดเลือดแดง (RBC)", "RBC1", "0 - 2 cell/HPF"), ("เม็ดเลือดขาว (WBC)", "WBC1", "0 - 5 cell/HPF"), ("เซลล์เยื่อบุผิว (Squam.epit.)", "SQ-epi", "0 - 10 cell/HPF"), ("อื่นๆ", "ORTER", "-")]
    urine_rows = [[(label, is_abn), (safe_value(val), is_abn), (norm, is_abn)] for label, key, norm in urine_data for val in [person.get(key, "-")] for is_abn in [is_urine_abnormal(label, val, norm)]]
    urine_html = render_lab_table_html("ผลการตรวจปัสสาวะ", "Urinalysis", ["การตรวจ", "ผลตรวจ", "ค่าปกติ"], urine_rows, "print-lab-table")
    stool_exam_text = interpret_stool_exam(person.get("Stool exam", ""))
    stool_cs_text = interpret_stool_cs(person.get("Stool C/S", ""))
    stool_html = f"""
    {render_section_header("ผลตรวจอุจจาระ (Stool Examination)")}
    <table class="print-lab-table">
        <tr><td style="text-align: left; width: 40%;"><b>ผลตรวจอุจจาระทั่วไป</b></td><td style="text-align: left;">{stool_exam_text}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>ผลตรวจอุจจาระเพาะเชื้อ</b></td><td style="text-align: left;">{stool_cs_text}</td></tr>
    </table>
    """
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
    hep_a_value = person.get("Hepatitis A")
    hep_a_display_text = "ไม่ได้เข้ารับการตรวจไวรัสตับอักเสบเอ" if is_empty(hep_a_value) else safe_value(hep_a_value)
    hbsag_raw, hbsab_raw, hbcab_raw = safe_value(person.get("HbsAg")), safe_value(person.get("HbsAb")), safe_value(person.get("HBcAB"))
    hep_b_advice, hep_b_status = hepatitis_b_advice(hbsag_raw, hbsab_raw, hbcab_raw)
    advice_bg_color = {'infection': '#ffdddd', 'no_immunity': '#fff8e1'}.get(hep_b_status, '#f8f9fa')
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
    return f"""
    <table style="width: 100%; border-collapse: collapse; page-break-inside: avoid;">
        <tr>
            <td style="width: 50%; vertical-align: top; padding-right: 5px;">{urine_html}{stool_html}</td>
            <td style="width: 50%; vertical-align: top; padding-left: 5px;">{other_tests_html}{hepatitis_html}</td>
        </tr>
    </table>
    """

def generate_printable_report(person_data, all_person_history_df=None):
    """Generates a full, self-contained HTML string for the health report."""
    sex = str(person_data.get("เพศ", "")).strip()
    if sex not in ["ชาย", "หญิง"]: sex = "ไม่ระบุ"
    
    header_vitals_html = render_header_and_vitals(person_data)
    lab_section_html = render_lab_section(person_data, sex)
    other_results_html = render_other_results_html(person_data, sex)
    doctor_suggestion = generate_holistic_advice(person_data)
    
    # Adjust summary text for better layout
    doctor_suggestion = doctor_suggestion.replace(
        "ผลตรวจสุขภาพโดยรวมพบประเด็นที่ควรให้ความสำคัญดังนี้:",
        "ผลตรวจสุขภาพโดยรวมพบประเด็นที่ควรให้ความสำคัญดังนี้:<br>"
    )

    doctor_suggestion_html = f"""
    <div class="advice-box" style="background-color: #e8f5e9; border-color: #a5d6a7;">
        <div class="advice-title" style="color: #1b5e20;">สรุปและคำแนะนำจากแพทย์ (Doctor's Summary & Recommendations)</div>
        <div class="advice-content">{doctor_suggestion}</div>
    </div>
    """
    
    # Remove the performance report section
    # performance_report_html = generate_performance_report_html_for_main_report(person_data, all_person_history_df)

    signature_html = """
    <div style="margin-top: 2rem; text-align: right; padding-right: 1rem; page-break-inside: avoid;">
        <div style="display: inline-block; text-align: center; width: 280px;">
            <div style="border-bottom: 1px dotted #333; margin-bottom: 0.4rem; width: 100%;"></div>
            <div style="white-space: nowrap;">นายแพทย์นพรัตน์ รัชฎาพร</div>
            <div style="white-space: nowrap;">แพทย์อาชีวเวชศาสตร์</div>
            <div style="white-space: nowrap;">ว.26674</div>
        </div>
    </div>
    """
    css_html = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
        body { font-family: 'Sarabun', sans-serif !important; font-size: 9.5px; margin: 10mm; color: #333; background-color: #fff; }
        p, div, span, td, th { line-height: 1.4; }
        table { border-collapse: collapse; width: 100%; }
        .print-lab-table td, .print-lab-table th { padding: 2px 4px; border: 1px solid #ccc; text-align: center; vertical-align: middle; }
        .print-lab-table th { background-color: #f2f2f2; font-weight: bold; }
        .print-lab-table-abn { background-color: #fff1f0 !important; }
        .header-grid { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 0.5rem; }
        .header-left { text-align: left; }
        .header-right { text-align: right; }
        .info-table { font-size: 9.5px; text-align: left; }
        .info-table td { padding: 1px 5px; border: none; }
        .advice-box { padding: 0.5rem 1rem; border-radius: 8px; line-height: 1.5; margin-top: 0.5rem; border: 1px solid #ddd; page-break-inside: avoid; }
        .advice-title { font-weight: bold; margin-bottom: 0.3rem; font-size: 11px; }
        .advice-content ul { padding-left: 20px; margin: 0; }
        .advice-content li { margin-bottom: 4px; }
        .perf-section { margin-top: 0.5rem; page-break-inside: avoid; border: 1px solid #e0e0e0; border-radius: 8px; padding: 0.5rem; }
        .summary-box { background-color: #f8f9fa; border-radius: 4px; padding: 4px 8px; margin-top: 2px; font-size: 9px; }
        @media print { body { -webkit-print-color-adjust: exact; margin: 0; } }
    </style>
    """
    final_html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลการตรวจสุขภาพ - {html.escape(person_data.get('ชื่อ-สกุล', ''))}</title>
        {css_html}
    </head>
    <body>
        {header_vitals_html}
        {lab_section_html}
        {other_results_html}
        {doctor_suggestion_html}
        {signature_html}
    </body>
    </html>
    """
    return final_html
