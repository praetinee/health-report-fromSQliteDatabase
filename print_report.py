import pandas as pd
from datetime import datetime
import html
import json

# --- Helper Functions for Data Interpretation ---

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

def safe_value(val):
    val = str(val or "").strip()
    return "-" if val.lower() in ["", "nan", "none", "-", "null"] else val

def flag_abnormal(val, low=None, high=None, inverse=False):
    """
    Returns (formatted_value, is_abnormal_boolean)
    """
    try:
        val_float = float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return safe_value(val), False
    
    formatted = f"{int(val_float):,}" if val_float.is_integer() else f"{val_float:,.1f}"
    is_abn = False
    
    if low is not None and val_float < low: is_abn = True
    if high is not None and val_float > high: is_abn = True
    
    return formatted, is_abn

def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val): return "-"
    # คำค้นหาสำหรับผลผิดปกติ
    abnormal_keywords = ["ผิดปกติ", "abnormal", "infiltrate", "lesion", "nodule", "opacity", "mass", "tb", "tuberculosis"]
    if any(keyword in val.lower() for keyword in abnormal_keywords):
        return f"<span style='color:#c0392b; font-weight:bold;'>{val} (ผิดปกติ)</span>"
    return val

def interpret_ekg(val):
    val = str(val or "").strip()
    if is_empty(val): return "-"
    abnormal_keywords = ["ผิดปกติ", "abnormal", "arrhythmia", "ischemia", "infarction", "bradycardia", "tachycardia", "fibrillation"]
    if any(keyword in val.lower() for keyword in abnormal_keywords):
        return f"<span style='color:#c0392b; font-weight:bold;'>{val} (ผิดปกติ)</span>"
    return val

# --- HTML Generation Parts ---

def get_main_report_css():
    """
    Returns the CSS string for the main health report.
    """
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');
        
        :root {
            --primary-color: #2c3e50;
            --secondary-color: #34495e;
            --accent-color: #16a085;
            --danger-color: #c0392b;
            --light-bg: #f8f9fa;
            --border-color: #bdc3c7;
            /* New colors for the recommendation box */
            --rec-box-bg: #fdfefe;
            --rec-box-border: #e0f2f1;
            --rec-title-color: #00695c;
            --rec-text-color: #455a64;
        }

        /* RESET ALL MARGINS */
        * {
            box-sizing: border-box;
            font-family: 'Sarabun', sans-serif !important;
        }

        @page {
            size: A4;
            margin: 0.5cm !important; /* Force margin on page level */
        }

        html, body {
            width: 210mm;
            min-height: 297mm; /* Changed from fixed height to min-height */
            margin: 0 !important;
            padding: 0 !important;
            background-color: #fff;
            font-size: 14px;
            line-height: 1.3;
            color: #333;
            -webkit-print-color-adjust: exact;
        }

        /* Container - Reverted to Block layout but added padding-bottom for footer */
        .container { 
            width: 100%;
            min-height: 297mm; /* Full A4 height minimum */
            padding: 0.5cm !important;
            /* เพิ่ม Padding ด้านล่าง 3cm เพื่อกันที่ให้ Footer ไม่ให้เนื้อหาทับ */
            padding-bottom: 3.5cm !important; 
            position: relative;
            display: block; /* กลับมาใช้ Block ตามเดิม */
        }
        
        /* Grid System */
        .row { 
            display: flex; 
            flex-wrap: wrap; 
            margin: 0 -5px; 
            /* เอา flex: 1 ออก เพื่อไม่ให้ยืดขยายช่องว่าง */
        }
        .col-50 { width: 50%; flex: 0 0 50%; padding: 0 5px; }

        /* Header */
        .header {
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 5px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }
        .header h1 { font-size: 22px; font-weight: 700; color: var(--primary-color); margin: 0; }
        .header p { margin: 0; font-size: 12px; color: var(--secondary-color); }
        .patient-info { font-size: 13px; text-align: right; }
        .patient-info b { color: var(--primary-color); }

        /* Vitals Bar */
        .vitals-bar {
            background-color: var(--light-bg);
            border-radius: 4px;
            padding: 6px 10px;
            margin-bottom: 10px;
            border: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            flex-wrap: wrap;
        }
        .vital-item b { color: var(--primary-color); font-weight: 700; margin-right: 3px; }

        /* Section Styling */
        .section-title {
            font-size: 14px;
            font-weight: 700;
            color: #fff;
            background-color: var(--primary-color);
            padding: 3px 8px;
            border-radius: 3px;
            margin-bottom: 5px;
            margin-top: 10px;
        }
        .col-50 .section-title:first-child { margin-top: 0; }
        
        /* Tables */
        table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 5px; }
        th, td { padding: 2px 4px; border-bottom: 1px solid #eee; text-align: left; vertical-align: middle; }
        th { background-color: #f1f2f6; font-weight: 600; color: var(--secondary-color); text-align: center; border-bottom: 2px solid #ddd; }
        td.val-col { text-align: center; font-weight: 500; }
        td.range-col { text-align: center; color: #7f8c8d; font-size: 11px; }
        
        .abnormal { color: var(--danger-color); font-weight: 700; }
        
        /* Premium Summary Box Styling */
        .summary-box {
            position: relative;
            background-color: var(--rec-box-bg);
            border: 1px solid var(--rec-box-border);
            border-left: 5px solid var(--rec-title-color); /* Premium left accent */
            border-radius: 4px; /* Slightly sharper corners for professional look */
            padding: 12px 15px;
            margin-top: 15px;
            page-break-inside: avoid;
            box-shadow: 0 2px 4px rgba(0,0,0,0.03); /* Subtle shadow */
        }
        
        .summary-title {
            font-weight: 700;
            color: var(--rec-title-color);
            margin-bottom: 8px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
        }
        
        /* Removed Icon */
        .summary-title::before {
            content: "";
            margin-right: 0;
        }

        .summary-content {
            font-size: 13px;
            line-height: 1.6;
            color: var(--rec-text-color);
            padding-left: 5px;
        }

        /* Specific Recommendation Box (Under Tables) - Warning Style */
        .rec-box {
            background-color: #fef9e7;
            border-left: 3px solid #b7950b;
            color: #7d6608;
            padding: 4px 8px;
            font-size: 11px;
            margin-bottom: 8px;
            border-radius: 0 3px 3px 0;
            font-style: italic;
        }
        
        /* Footer - Positioned absolute bottom right, text-align center within right half */
        .footer-container {
            position: absolute;
            bottom: 0.5cm;
            right: 0;
            width: 50%; /* Covers the right half of the page */
            height: 2.5cm;
            display: flex;
            justify-content: center; /* Center horizontally within the 50% width */
            align-items: flex-end; /* Align bottom */
            page-break-inside: avoid;
        }

        .doctor-signature {
            text-align: center; /* Center text within its box */
        }

        /* Screen Preview Adjustments */
        @media screen {
            body { background-color: #555; padding: 20px; display: flex; justify-content: center; }
            .container { box-shadow: 0 0 15px rgba(0,0,0,0.3); background-color: white; }
        }
        
        @media print {
            body { background-color: white; padding: 0; }
            .container { box-shadow: none; margin: 0; }
        }
    </style>
    """

# Alias for backward compatibility
get_report_css = get_main_report_css

def render_lab_row(name, value, unit, normal_range, is_abnormal):
    cls = "abnormal" if is_abnormal else ""
    val_display = value if value != "-" else "-"
    
    range_display = normal_range
    if unit:
        range_display = f"{normal_range} <span style='font-size:10px; color:#999;'>({unit})</span>"

    return f"""
    <tr>
        <td>{name}</td>
        <td class="val-col {cls}">{val_display}</td>
        <td class="range-col">{range_display}</td>
    </tr>
    """

def render_rec_box(suggestions):
    """
    Renders a small recommendation box if there are suggestions.
    """
    if not suggestions:
        return ""
    content = "<br>".join([f"• {s}" for s in suggestions])
    return f'<div class="rec-box">{content}</div>'

def render_printable_report_body(person_data, all_person_history_df=None):
    """
    Generates the HTML body content for the main health report.
    Separated from generate_printable_report to allow batch printing.
    """
    # --- 1. Prepare Data ---
    name = person_data.get('ชื่อ-สกุล', '-')
    age = str(int(float(person_data.get('อายุ')))) if str(person_data.get('อายุ')).replace('.', '', 1).isdigit() else person_data.get('อายุ', '-')
    hn = str(int(float(person_data.get('HN')))) if str(person_data.get('HN')).replace('.', '', 1).isdigit() else person_data.get('HN', '-')
    date = person_data.get("วันที่ตรวจ", datetime.now().strftime("%d/%m/%Y"))
    dept = person_data.get('หน่วยงาน', '-')
    sex = person_data.get('เพศ', '-')

    # Vitals
    weight = get_float('น้ำหนัก', person_data)
    height = get_float('ส่วนสูง', person_data)
    bmi = "-"
    if weight and height:
        bmi_val = weight / ((height/100)**2)
        bmi = f"{bmi_val:.1f}"
    
    sbp, dbp = get_float("SBP", person_data), get_float("DBP", person_data)
    bp = f"{int(sbp)}/{int(dbp)}" if sbp and dbp else "-"
    pulse = f"{int(get_float('pulse', person_data))}" if get_float('pulse', person_data) else "-"
    waist = person_data.get('รอบเอว', '-')

    # --- 2. Calculate Specific Recommendations ---
    
    # 2.1 CBC Recommendations
    rec_cbc = []
    hb = get_float("Hb(%)", person_data)
    hb_low = 12 if sex == "หญิง" else 13
    if hb and hb < hb_low: 
        rec_cbc.append("ภาวะโลหิตจาง ควรทานอาหารที่มีธาตุเหล็กสูง")
    
    wbc = get_float("WBC (cumm)", person_data)
    if wbc and wbc > 10000:
        rec_cbc.append("เม็ดเลือดขาวสูง อาจมีการติดเชื้อหรืออักเสบ")
    
    # 2.2 Kidney Recommendations
    rec_kidney = []
    uric = get_float("Uric Acid", person_data)
    if uric and uric > 7: 
        rec_kidney.append("กรดยูริกสูง ควรลดการทานเครื่องในสัตว์ ยอดผัก และสัตว์ปีก")
    
    # 2.3 Urine Recommendations
    rec_urine = []
    ua_sugar = str(person_data.get("sugar", "")).strip().lower()
    if ua_sugar not in ['negative', '-', '']: rec_urine.append("พบน้ำตาลในปัสสาวะ")
    
    ua_alb = str(person_data.get("Alb", "")).strip().lower()
    if ua_alb not in ['negative', '-', '']: rec_urine.append("พบโปรตีนในปัสสาวะ")
    
    ua_rbc = str(person_data.get("RBC1", "")).strip()
    if ua_rbc not in ['0-1', '0-2', 'negative', '-', '']: rec_urine.append("พบเม็ดเลือดแดงในปัสสาวะ")
    
    ua_wbc = str(person_data.get("WBC1", "")).strip()
    if ua_wbc not in ['0-1', '0-2', '0-3', '0-5', 'negative', '-', '']: rec_urine.append("พบเม็ดเลือดขาวในปัสสาวะ")

    # 2.4 Sugar & Lipid Recommendations
    rec_sugar_lipid = []
    fbs = get_float("FBS", person_data)
    if fbs and fbs >= 100: rec_sugar_lipid.append("ระดับน้ำตาลสูง ควรควบคุมอาหารประเภทแป้ง/น้ำตาล")
    chol = get_float("CHOL", person_data)
    ldl = get_float("LDL", person_data)
    tgl = get_float("TGL", person_data)
    if (chol and chol > 200) or (ldl and ldl > 130) or (tgl and tgl > 150): rec_sugar_lipid.append("ไขมันในเลือดสูง เลี่ยงของทอด/มัน/กะทิ")
    
    # 2.5 Liver Recommendations
    rec_liver = []
    sgot = get_float("SGOT", person_data)
    sgpt = get_float("SGPT", person_data)
    alp = get_float("ALP", person_data)
    if (sgot and sgot > 40) or (sgpt and sgpt > 40) or (alp and (alp > 105 or alp < 35)): rec_liver.append("ค่าตับสูงกว่าปกติ งดแอลกอฮอล์/ยาไม่จำเป็น")

    # 2.6 Hepatitis Recommendations
    rec_hep = []
    def hepatitis_b_advice(hbsag, hbsab, hbcab):
        hbsag, hbsab, hbcab = str(hbsag).lower(), str(hbsab).lower(), str(hbcab).lower()
        if "positive" in hbsag: return "ติดเชื้อไวรัสตับอักเสบบี ควรพบแพทย์เพื่อรับการรักษา"
        if "positive" in hbsab and "positive" not in hbsag: return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี"
        if "positive" in hbcab and "positive" not in hbsab: return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน"
        if all(x == "negative" for x in [hbsag, hbsab, hbcab]): return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน"
        return ""

    # Hepatitis column names might vary, try to get current year's
    selected_year = person_data.get("Year", datetime.now().year + 543)
    current_thai_year = datetime.now().year + 543
    
    hbsag_col = "HbsAg"
    hbsab_col = "HbsAb"
    hbcab_col = "HBcAB"

    # Try to find specific year column first
    suffix = str(selected_year)[-2:]
    if f"HbsAg{suffix}" in person_data and not is_empty(person_data.get(f"HbsAg{suffix}")): hbsag_col = f"HbsAg{suffix}"
    if f"HbsAb{suffix}" in person_data and not is_empty(person_data.get(f"HbsAb{suffix}")): hbsab_col = f"HbsAb{suffix}"
    if f"HBcAB{suffix}" in person_data and not is_empty(person_data.get(f"HBcAB{suffix}")): hbcab_col = f"HBcAB{suffix}"
    
    hbsag_val = person_data.get(hbsag_col)
    hbsab_val = person_data.get(hbsab_col)
    hbcab_val = person_data.get(hbcab_col)

    if not (is_empty(hbsag_val) and is_empty(hbsab_val) and is_empty(hbcab_val)):
        hep_advice = hepatitis_b_advice(hbsag_val, hbsab_val, hbcab_val)
        if hep_advice:
            rec_hep.append(hep_advice)

    # Hepatitis Date
    hep_check_date = str(person_data.get("ปีตรวจHEP", "")).strip()
    if is_empty(hep_check_date):
        hep_check_date = str(selected_year)

    # --- 3. Build Lab Blocks ---
    
    # Hematology
    hct_low = 36 if sex == "หญิง" else 39
    
    cbc_data = [
        ("Hemoglobin", "Hb(%)", None, hb_low, None, "g/dL", f"> {hb_low}"),
        ("Hematocrit", "HCT", None, hct_low, None, "%", f"> {hct_low}"),
        ("WBC Count", "WBC (cumm)", None, 4000, 10000, "cells/mm³", "4,000-10,000"),
        ("Neutrophil", "Ne (%)", None, 40, 70, "%", "40-70"),
        ("Lymphocyte", "Ly (%)", None, 20, 45, "%", "20-45"),
        ("Monocyte", "M", None, 2, 10, "%", "2-10"),
        ("Eosinophil", "Eo", None, 1, 6, "%", "1-6"),
        ("Basophil", "BA", None, 0, 1, "%", "0-1"),
        ("Platelet", "Plt (/mm)", None, 150000, 450000, "cells/mm³", "150,000-450,000")
    ]
    cbc_rows = ""
    for label, key, _, low, high, unit, norm_text in cbc_data:
        val, is_abn = flag_abnormal(person_data.get(key), low, high)
        cbc_rows += render_lab_row(label, val, unit, norm_text, is_abn)

    # Urinalysis
    urine_color = safe_value(person_data.get("Color"))
    urine_ph = safe_value(person_data.get("pH"))
    urine_spgr = safe_value(person_data.get("Spgr"))
    urine_alb = safe_value(person_data.get("Alb"))
    urine_sugar = safe_value(person_data.get("sugar"))
    urine_rbc = safe_value(person_data.get("RBC1"))
    urine_wbc = safe_value(person_data.get("WBC1"))
    urine_epi = safe_value(person_data.get("SQ-epi"))
    
    u_rows = ""
    u_rows += render_lab_row("Color", urine_color, "", "Yellow", urine_color.lower() not in ['yellow', 'pale yellow', '-'])
    u_rows += render_lab_row("pH", urine_ph, "", "4.6-8.0", False)
    u_rows += render_lab_row("Sp. Gravity", urine_spgr, "", "1.005-1.030", False)
    u_rows += render_lab_row("Albumin", urine_alb, "", "Negative", urine_alb.lower() not in ['negative', '-'])
    u_rows += render_lab_row("Sugar", urine_sugar, "", "Negative", urine_sugar.lower() not in ['negative', '-'])
    u_rows += render_lab_row("RBC", urine_rbc, "cells", "0-2", urine_rbc not in ['0-1', '0-2', 'negative', '-'])
    u_rows += render_lab_row("WBC", urine_wbc, "cells", "0-5", urine_wbc not in ['0-1', '0-2', '0-3', '0-5', 'negative', '-'])
    u_rows += render_lab_row("Epithelial", urine_epi, "cells", "0-5", False)

    # Other Tests (Use Interpret Functions)
    
    # --- CXR Logic: Check "CXR" column first ---
    cxr_val = person_data.get("CXR")
    if is_empty(cxr_val):
        # Fallback logic: Try to find year-specific column e.g. CXR66
        data_year = person_data.get("Year")
        if data_year:
            suffix = str(data_year)[-2:]
            cxr_val = person_data.get(f"CXR{suffix}")
            
    cxr_display = interpret_cxr(cxr_val)
    
    # --- EKG Logic: Check "EKG" column first ---
    ekg_val = person_data.get("EKG")
    if is_empty(ekg_val):
        data_year = person_data.get("Year")
        if data_year:
            suffix = str(data_year)[-2:]
            ekg_val = person_data.get(f"EKG{suffix}")
    ekg_display = interpret_ekg(ekg_val)

    # --- Hepatitis A Logic ---
    hep_a_val = person_data.get("Hepatitis A")
    if is_empty(hep_a_val):
        data_year = person_data.get("Year")
        if data_year:
            suffix = str(data_year)[-2:]
            hep_a_val = person_data.get(f"Hepatitis A{suffix}")
    hep_a_display = safe_value(hep_a_val)

    # Hepatitis B columns logic (already present, keeping it consistent)
    hbsag = safe_value(person_data.get(hbsag_col))
    hbsab = safe_value(person_data.get(hbsab_col))
    hbcab = safe_value(person_data.get(hbcab_col))
    
    # Custom Logic: ถ้า HBcAb เป็น "-" แต่ HBsAg และ HBsAb มีผลตรวจ ให้แสดงเป็น Negative
    if hbcab == "-" and hbsag != "-" and hbsab != "-":
        hbcab = "Negative"
    
    # --- 4. Main Doctor's Suggestion (Only Doc Note) ---
    doc_note = str(person_data.get("DOCTER suggest", "")).strip()
    if doc_note and doc_note != "-":
        suggestion_html = doc_note
    else:
        suggestion_html = "สุขภาพโดยรวมอยู่ในเกณฑ์ดี โปรดรักษาสุขภาพให้แข็งแรงอยู่เสมอ"

    # --- 5. Assemble Final HTML Body ---
    return f"""
        <div class="container">
            
            <!-- Header -->
            <div class="header">
                <div>
                    <h1>ใบรายงานผลการตรวจสุขภาพ</h1>
                    <p>โรงพยาบาลสันทราย (San Sai Hospital)</p>
                    <p>คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม</p>
                </div>
                <div class="patient-info">
                    <p><b>ชื่อ-สกุล:</b> {name} &nbsp;|&nbsp; <b>อายุ:</b> {age} ปี &nbsp;|&nbsp; <b>เพศ:</b> {sex}</p>
                    <p><b>HN:</b> {hn} &nbsp;|&nbsp; <b>หน่วยงาน:</b> {dept}</p>
                    <p><b>วันที่ตรวจ:</b> {date}</p>
                </div>
            </div>

            <!-- Vitals -->
            <div class="vitals-bar">
                <span class="vital-item"><b>น้ำหนัก:</b> {weight} กก.</span>
                <span class="vital-item"><b>ส่วนสูง:</b> {height} ซม.</span>
                <span class="vital-item"><b>BMI:</b> {bmi}</span>
                <span class="vital-item"><b>ความดัน:</b> {bp} mmHg</span>
                <span class="vital-item"><b>ชีพจร:</b> {pulse} /นาที</span>
                <span class="vital-item"><b>รอบเอว:</b> {waist} ซม.</span>
            </div>

            <!-- Main Content Grid -->
            <div class="row">
                <!-- Left Column -->
                <div class="col-50">
                    <div class="section-title">ความสมบูรณ์ของเลือด (CBC)</div>
                    <table>
                        <thead><tr><th>รายการตรวจ</th><th>ผลตรวจ</th><th>ค่าปกติ</th></tr></thead>
                        <tbody>{cbc_rows}</tbody>
                    </table>
                    {render_rec_box(rec_cbc)}

                    <div class="section-title">ไตและกรดยูริก (Kidney Function & Uric Acid)</div>
                    <table>
                        <thead><tr><th>รายการตรวจ</th><th>ผลตรวจ</th><th>ค่าปกติ</th></tr></thead>
                        <tbody>
                            {render_lab_row("BUN", safe_value(person_data.get("BUN")), "mg/dL", "6-20", False)}
                            {render_lab_row("Creatinine", safe_value(person_data.get("Cr")), "mg/dL", "0.5-1.2", False)}
                            {render_lab_row("eGFR", safe_value(person_data.get("GFR")), "mL/min", ">90", False)}
                            {render_lab_row("Uric Acid", safe_value(person_data.get("Uric Acid")), "mg/dL", "2.4-7.0", get_float("Uric Acid", person_data) and get_float("Uric Acid", person_data) > 7)}
                        </tbody>
                    </table>
                    {render_rec_box(rec_kidney)}

                    <div class="section-title">การตรวจปัสสาวะ (Urinalysis)</div>
                    <table>
                        <thead><tr><th>รายการตรวจ</th><th>ผลตรวจ</th><th>ค่าปกติ</th></tr></thead>
                        <tbody>{u_rows}</tbody>
                    </table>
                    {render_rec_box(rec_urine)}
                    
                    <div class="section-title">อุจจาระ (Stool)</div>
                    <table>
                        <tbody>
                            <tr><td>Stool Exam</td><td class="val-col">{safe_value(person_data.get("Stool exam"))}</td><td class="range-col"></td></tr>
                            <tr><td>Stool Culture</td><td class="val-col">{safe_value(person_data.get("Stool C/S"))}</td><td class="range-col"></td></tr>
                        </tbody>
                    </table>
                </div>

                <!-- Right Column -->
                <div class="col-50">
                    <div class="section-title">น้ำตาลและไขมันในเลือด (Blood Sugar & Lipid Profile)</div>
                    <table>
                        <thead><tr><th>รายการตรวจ</th><th>ผลตรวจ</th><th>ค่าปกติ</th></tr></thead>
                        <tbody>
                            {render_lab_row("Fasting Blood Sugar", safe_value(person_data.get("FBS")), "mg/dL", "70-100", get_float("FBS", person_data) and get_float("FBS", person_data) > 100)}
                            {render_lab_row("Cholesterol", safe_value(person_data.get("CHOL")), "mg/dL", "< 200", get_float("CHOL", person_data) and get_float("CHOL", person_data) > 200)}
                            {render_lab_row("Triglyceride", safe_value(person_data.get("TGL")), "mg/dL", "< 150", get_float("TGL", person_data) and get_float("TGL", person_data) > 150)}
                            {render_lab_row("HDL-C", safe_value(person_data.get("HDL")), "mg/dL", "> 40", get_float("HDL", person_data) and get_float("HDL", person_data) < 40)}
                            {render_lab_row("LDL-C", safe_value(person_data.get("LDL")), "mg/dL", "< 130", get_float("LDL", person_data) and get_float("LDL", person_data) > 130)}
                        </tbody>
                    </table>
                    {render_rec_box(rec_sugar_lipid)}
                    
                    <div class="section-title">การทำงานของตับ (Liver Function)</div>
                    <table>
                        <thead><tr><th>รายการตรวจ</th><th>ผลตรวจ</th><th>ค่าปกติ</th></tr></thead>
                        <tbody>
                            {render_lab_row("SGOT (AST)", safe_value(person_data.get("SGOT")), "U/L", "< 40", get_float("SGOT", person_data) and get_float("SGOT", person_data) > 40)}
                            {render_lab_row("SGPT (ALT)", safe_value(person_data.get("SGPT")), "U/L", "< 40", get_float("SGPT", person_data) and get_float("SGPT", person_data) > 40)}
                            {render_lab_row("Alkaline Phos.", safe_value(person_data.get("ALP")), "U/L", "35-105", get_float("ALP", person_data) and (get_float("ALP", person_data) > 105 or get_float("ALP", person_data) < 35))}
                        </tbody>
                    </table>
                    {render_rec_box(rec_liver)}

                    <div class="section-title">ไวรัสตับอักเสบ (Hepatitis) ตรวจเมื่อ {hep_check_date}</div>
                    <table>
                        <tbody>
                            <tr><td>Hepatitis A</td><td class="val-col">{hep_a_display}</td><td class="range-col">Neg</td></tr>
                            <tr><td>HBsAg (เชื้อ)</td><td class="val-col">{hbsag}</td><td class="range-col">Neg</td></tr>
                            <tr><td>HBsAb (ภูมิ)</td><td class="val-col">{hbsab}</td><td class="range-col">Pos</td></tr>
                            <tr><td>HBcAb</td><td class="val-col">{hbcab}</td><td class="range-col">Neg</td></tr>
                        </tbody>
                    </table>
                    {render_rec_box(rec_hep)}

                    <div class="section-title">เอกซเรย์ปอดและคลื่นไฟฟ้าหัวใจ (Chest X-ray & EKG)</div>
                    <table>
                        <tbody>
                            <tr>
                                <td><b>Chest X-Ray</b></td>
                                <td class="val-col" style="text-align:left; font-size:11px;" colspan="2">{cxr_display}</td>
                            </tr>
                            <tr>
                                <td><b>EKG</b></td>
                                <td class="val-col" style="text-align:left; font-size:11px;" colspan="2">{ekg_display}</td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <!-- New Premium Summary Box (Only Doctor's Recommendation) -->
                    <div class="summary-box">
                        <div class="summary-title">สรุปผลการตรวจและคำแนะนำแพทย์ (Doctor's Recommendation)</div>
                        <div class="summary-content">
                            {suggestion_html}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <div class="footer-container">
                <div class="doctor-signature">
                    <b>นายแพทย์นพรัตน์ รัชฎาพร</b><br>
                    แพทย์อาชีวเวชศาสตร์ (ว.26674)
                </div>
            </div>

        </div>
    """

def generate_printable_report(person_data, all_person_history_df=None):
    """
    Generates the complete HTML file for the report (Single Person Print).
    """
    css_content = get_main_report_css()
    body_content = render_printable_report_body(person_data, all_person_history_df)
    
    return f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลตรวจสุขภาพ - {person_data.get('ชื่อ-สกุล', 'Report')}</title>
        {css_content}
    </head>
    <body onload="window.print()">
        {body_content}
    </body>
    </html>
    """
