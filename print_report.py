import pandas as pd
from datetime import datetime
import html

# --- Import a key function from performance_tests ---
from performance_tests import generate_comprehensive_recommendations

# ==============================================================================
# NOTE: This file has been completely redesigned to generate a printable
# health report that matches the modern UI of the web application.
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

def interpret_bp(sbp, dbp):
    """Interprets blood pressure readings."""
    try:
        sbp, dbp = float(sbp), float(dbp)
        if sbp == 0 or dbp == 0: return "-"
        if sbp >= 160 or dbp >= 100: return "ความดันสูง"
        if sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
        if sbp < 120 and dbp < 80: return "ความดันปกติ"
        return "ความดันค่อนข้างสูง"
    except: return "-"

def interpret_bmi(bmi):
    """Interprets BMI value."""
    if bmi is None: return ""
    if bmi < 18.5: return "น้ำหนักน้อยกว่าเกณฑ์"
    if 18.5 <= bmi < 23: return "น้ำหนักปกติ"
    if 23 <= bmi < 25: return "น้ำหนักเกิน (ท้วม)"
    if 25 <= bmi < 30: return "เข้าเกณฑ์โรคอ้วน"
    if bmi >= 30: return "เข้าเกณฑ์โรคอ้วนอันตราย"
    return ""

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

def is_urine_abnormal(test_name, value):
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


# --- HTML Component Rendering Functions ---

def render_css():
    """Returns the CSS block for the printable report."""
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
        
        body {
            font-family: 'Sarabun', sans-serif !important;
            font-size: 10px;
            margin: 0;
            color: #333;
            background-color: #fff;
        }
        .page {
            padding: 1cm;
            page-break-after: always;
        }
        h1, h2, h4, h5 { margin: 0; }
        .header-grid {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }
        .header-left { text-align: left; }
        .header-right { text-align: right; }
        .info-table {
            width: 100%;
            font-size: 9.5px;
            text-align: left;
            border-collapse: collapse;
        }
        .info-table td { padding: 1px 5px; }
        .section-container {
            border: 1px solid #dee2e6;
            border-radius: 12px;
            padding: 1rem;
            margin-top: 1rem;
            page-break-inside: avoid;
        }
        .section-header {
            font-size: 1.1rem;
            font-weight: 600;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
        }
        .section-subtitle {
            font-weight: 600;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
            opacity: 0.7;
        }
        .columns-container { display: flex; gap: 1.5rem; }
        .column { flex: 1; }
        .lab-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.8rem;
        }
        .lab-table th, .lab-table td {
            padding: 0.5rem;
            border-bottom: 1px solid #e9ecef;
        }
        .lab-table td:nth-child(2) { text-align: center; }
        .lab-table .abnormal-row {
            background-color: rgba(220, 53, 69, 0.1);
            color: #b22222;
            font-weight: 600;
        }
        .info-detail-table { width: 100%; font-size: 0.8rem; }
        .info-detail-table th { width: 40%; text-align: left; font-weight: 600; opacity: 0.7; padding: 0.5rem; border-bottom: 1px solid #e9ecef;}
        .info-detail-table td { padding: 0.5rem; border-bottom: 1px solid #e9ecef;}
        .custom-advice-box {
            padding: 0.75rem; border-radius: 8px; margin-top: 0.5rem; border: 1px solid transparent; font-weight: 600;
        }
        .immune-box { background-color: rgba(40, 167, 69, 0.1); color: #2E7D32; border-color: rgba(40, 167, 69, 0.2); }
        .no-immune-box { background-color: rgba(220, 53, 69, 0.1); color: #C62828; border-color: rgba(220, 53, 69, 0.2); }
        .warning-box { background-color: rgba(255, 193, 7, 0.1); color: #AF6C00; border-color: rgba(255, 193, 7, 0.2); }
        .recommendation-container { border-left: 4px solid #00796B; padding-left: 1rem; }
        .recommendation-container ul { padding-left: 20px; margin: 0; }
        .recommendation-container li { margin-bottom: 0.25rem; }
        .signature-section {
            margin-top: 2rem; text-align: right; padding-right: 1rem; page-break-inside: avoid;
        }
        .signature-line { display: inline-block; text-align: center; width: 250px; }
        .signature-line .line { border-bottom: 1px dotted #333; margin-bottom: 0.4rem; width: 100%; }
        
        @media print {
            body { -webkit-print-color-adjust: exact; }
            .page { page-break-after: always; }
        }
    </style>
    """

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

def render_lab_results(person_data, sex):
    """Renders the lab results section."""
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_config = [("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None), ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None), ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000), ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70), ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44), ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000)]
    blood_config = [("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106), ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17), ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True), ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2), ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200), ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150), ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True), ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160), ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37), ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41)]
    
    def build_table_rows(config):
        rows_html = ""
        for label, col, norm, low, high, *opt in config:
            higher = opt[0] if opt else False
            val = get_float(col, person_data)
            result, is_abn = flag(val, low, high, higher)
            row_class = "abnormal-row" if is_abn else ""
            rows_html += f'<tr class="{row_class}"><td>{label}</td><td>{result}</td><td>{norm}</td></tr>'
        return rows_html

    cbc_rows_html = build_table_rows(cbc_config)
    blood_rows_html = build_table_rows(blood_config)
    
    return f"""
    <div class="section-container">
        <div class="section-header">ผลการตรวจทางห้องปฏิบัติการ (Laboratory Results)</div>
        <div class="columns-container">
            <div class="column">
                <h5 class="section-subtitle">ผลตรวจความสมบูรณ์ของเม็ดเลือด (CBC)</h5>
                <table class="lab-table"><colgroup><col style="width:40%;"><col style="width:20%;"><col style="width:40%;"></colgroup><tbody>{cbc_rows_html}</tbody></table>
            </div>
            <div class="column">
                <h5 class="section-subtitle">ผลตรวจเลือด (Blood Chemistry)</h5>
                <table class="lab-table"><colgroup><col style="width:40%;"><col style="width:20%;"><col style="width:40%;"></colgroup><tbody>{blood_rows_html}</tbody></table>
            </div>
        </div>
    </div>
    """

def render_other_examinations(person_data):
    """Renders other tests like urinalysis, stool, CXR, EKG, Hepatitis."""
    urine_data = [("สี (Colour)", "Color"), ("น้ำตาล (Sugar)", "sugar"), ("โปรตีน (Albumin)", "Alb"), ("กรด-ด่าง (pH)", "pH"), ("ความถ่วงจำเพาะ (Sp.gr)", "Spgr"), ("เม็ดเลือดแดง (RBC)", "RBC1"), ("เม็ดเลือดขาว (WBC)", "WBC1")]
    urine_rows_html = ""
    for label, key in urine_data:
        val = person_data.get(key, "-")
        row_class = "abnormal-row" if is_urine_abnormal(label, val) else ""
        urine_rows_html += f'<tr class="{row_class}"><th>{label}</th><td>{safe_value(val)}</td></tr>'

    stool_exam = interpret_stool_exam(person_data.get("Stool exam", ""))
    stool_cs = interpret_stool_cs(person_data.get("Stool C/S", ""))
    
    year = person_data.get("Year")
    cxr_col = f"CXR{str(year)[-2:]}" if year and year != (datetime.now().year + 543) else "CXR"
    ekg_col = f"EKG{str(year)[-2:]}" if year and year != (datetime.now().year + 543) else "EKG"
    cxr_result = interpret_cxr(person_data.get(cxr_col, ''))
    ekg_result = interpret_ekg(person_data.get(ekg_col, ''))

    hbsag, hbsab, hbcab = safe_value(person_data.get("HbsAg")), safe_value(person_data.get("HbsAb")), safe_value(person_data.get("HBcAB"))
    advice, status = hepatitis_b_advice(hbsag, hbsab, hbcab)
    status_class = {'immune': 'immune-box', 'no_immune': 'no-immune-box'}.get(status, 'warning-box')
    hep_b_advice_html = f'<div class="custom-advice-box {status_class}">{advice}</div>' if not is_empty(hbsag) else ""

    return f"""
    <div class="section-container">
        <div class="section-header">ผลการตรวจอื่นๆ (Other Examinations)</div>
        <div class="columns-container">
            <div class="column">
                <h5 class="section-subtitle">ผลการตรวจปัสสาวะ (Urinalysis)</h5>
                <table class="info-detail-table"><tbody>{urine_rows_html}</tbody></table>
                <h5 class="section-subtitle">ผลตรวจอุจจาระ (Stool)</h5>
                <table class="info-detail-table"><tbody>
                    <tr><th>ผลตรวจอุจจาระทั่วไป</th><td>{stool_exam}</td></tr>
                    <tr><th>ผลตรวจอุจจาระเพาะเชื้อ</th><td>{stool_cs}</td></tr>
                </tbody></table>
            </div>
            <div class="column">
                <h5 class="section-subtitle">ผลตรวจพิเศษ</h5>
                <table class="info-detail-table"><tbody>
                    <tr><th>ผลเอกซเรย์ (Chest X-ray)</th><td>{cxr_result}</td></tr>
                    <tr><th>ผลคลื่นไฟฟ้าหัวใจ (EKG)</th><td>{ekg_result}</td></tr>
                </tbody></table>
                <h5 class="section-subtitle">ผลตรวจไวรัสตับอักเสบบี</h5>
                <table class="info-detail-table"><tbody>
                    <tr><th>HBsAg</th><td>{hbsag}</td></tr>
                    <tr><th>HBsAb</th><td>{hbsab}</td></tr>
                    <tr><th>HBcAb</th><td>{hbcab}</td></tr>
                </tbody></table>
                {hep_b_advice_html}
            </div>
        </div>
    </div>
    """

def render_summary_and_signature(person_data):
    """Renders the final summary and doctor's signature."""
    recommendations_html = generate_comprehensive_recommendations(person_data)
    return f"""
    <div class="section-container">
        <div class="section-header">สรุปและคำแนะนำจากแพทย์ (Doctor's Summary & Recommendations)</div>
        <div class="recommendation-container">{recommendations_html}</div>
    </div>
    <div class="signature-section">
        <div class="signature-line">
            <div class="line"></div>
            <div>นายแพทย์นพรัตน์ รัชฎาพร</div>
            <div>แพทย์อาชีวเวชศาสตร์</div>
            <div>เลขที่ใบอนุญาตฯ ว.26674</div>
        </div>
    </div>
    """

# --- Main Report Generation Function ---

def generate_printable_report(person_data, all_person_history_df=None):
    """
    Generates a full, self-contained HTML string for the modern health report.
    """
    sex = str(person_data.get("เพศ", "")).strip()
    if sex not in ["ชาย", "หญิง"]: sex = "ไม่ระบุ"
    
    # Assemble all HTML parts
    css_html = render_css()
    header_vitals_html = render_header_and_vitals(person_data)
    lab_html = render_lab_results(person_data, sex)
    other_exams_html = render_other_examinations(person_data)
    summary_signature_html = render_summary_and_signature(person_data)

    # Combine into a single HTML document
    final_html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลการตรวจสุขภาพ - {html.escape(person_data.get('ชื่อ-สกุล', ''))}</title>
        {css_html}
    </head>
    <body>
        <div class="page">
            {header_vitals_html}
            {lab_html}
            {other_exams_html}
            {summary_signature_html}
        </div>
    </body>
    </html>
    """
    return final_html
