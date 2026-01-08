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

def get_report_css():
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
            --warning-bg: #fef9e7;
            --warning-text: #b7950b;
        }

        /* RESET ALL MARGINS & FORCE SARABUN FONT */
        * {
            box-sizing: border-box;
            font-family: 'Sarabun', sans-serif !important;
        }

        @page {
            size: A4;
            margin: 0mm !important; /* Force 0 margin on page level */
        }

        html, body {
            width: 210mm;
            height: 297mm;
            margin: 0 !important;
            padding: 0 !important;
            background-color: #fff;
            font-family: 'Sarabun', sans-serif !important;
            font-size: 14px; /* Standard readable size */
            line-height: 1.3;
            color: #333;
            -webkit-print-color-adjust: exact;
        }

        /* Container acts as the printable area with Padding */
        .container { 
            width: 100%;
            height: 100%;
            padding: 5mm !important; /* EXACTLY 0.5cm PADDING */
            position: relative;
        }
        
        /* Grid System */
        .row { display: flex; flex-wrap: wrap; margin: 0 -5px; }
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
        .header h1 { font-family: 'Sarabun', sans-serif !important; font-size: 22px; font-weight: 700; color: var(--primary-color); margin: 0; }
        .header p { font-family: 'Sarabun', sans-serif !important; margin: 0; font-size: 12px; color: var(--secondary-color); }
        .patient-info { font-family: 'Sarabun', sans-serif !important; font-size: 13px; text-align: right; }
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
            font-family: 'Sarabun', sans-serif !important;
        }
        .vital-item b { color: var(--primary-color); font-weight: 700; margin-right: 3px; }

        /* Section Styling - UPDATED FOR SINGLE LINE */
        .section-title {
            background-color: var(--primary-color);
            padding: 5px 8px;
            border-radius: 3px;
            margin-bottom: 5px;
            margin-top: 10px;
            color: #fff;
            font-size: 14px;
            font-weight: 700;
            line-height: 1.4;
            font-family: 'Sarabun', sans-serif !important;
        }
        .col-50 .section-title:first-child { margin-top: 0; }
        
        /* Tables */
        table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 2px; font-family: 'Sarabun', sans-serif !important; }
        th, td { padding: 2px 4px; border-bottom: 1px solid #eee; text-align: left; vertical-align: middle; }
        th { background-color: #f1f2f6; font-weight: 600; color: var(--secondary-color); text-align: center; border-bottom: 2px solid #ddd; }
        td.val-col { text-align: center; font-weight: 500; }
        td.range-col { text-align: center; color: #7f8c8d; font-size: 11px; }
        
        .abnormal { color: var(--danger-color); font-weight: 700; }
        
        /* Summary Box - MOVED TO RIGHT COLUMN ONLY */
        .summary-box {
            border: 2px solid var(--accent-color);
            background-color: #e8f8f5; /* Lighter Green Tone */
            border-radius: 8px; /* Rounded corners */
            padding: 10px;
            margin-top: 15px;
            page-break-inside: avoid;
            font-family: 'Sarabun', sans-serif !important;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05); /* Soft shadow */
        }
        .summary-title { 
            font-weight: 700; 
            color: var(--accent-color); 
            margin-bottom: 5px; 
            font-size: 14px; 
            border-bottom: 1px dashed var(--accent-color); 
            padding-bottom: 3px; 
        }
        .summary-content { font-size: 13px; line-height: 1.5; color: #2c3e50; }

        /* Specific Recommendation Box (Under Tables) */
        .rec-box {
            background-color: var(--warning-bg);
            border-left: 3px solid var(--warning-text);
            color: #7d6608;
            padding: 4px 8px;
            font-size: 11px;
            margin-bottom: 8px;
            border-radius: 0 3px 3px 0;
            font-style: italic;
        }
        
        /* Footer */
        .footer {
            margin-top: 10px;
            text-align: right;
            font-size: 12px;
            page-break-inside: avoid;
            position: absolute;
            bottom: 5mm;
            right: 5mm;
            width: 100%;
            font-family: 'Sarabun', sans-serif !important;
        }
        .signature-line {
            display: inline-block;
            text-align: center;
            margin-left: auto;
        }
        .signature-dash {
            border-bottom: 1px dotted #333;
            width: 200px;
            margin-bottom: 5px;
            display: inline-block;
        }

        /* Screen Preview Adjustments */
        @media screen {
            body { background-color: #555; padding: 20px; display: flex; justify-content: center; }
            .container { box-shadow: 0 0 15px rgba(0,0,0,0.3); }
        }
        
        @media print {
            body { background-color: white; padding: 0; }
            .container { box-shadow: none; margin: 0; }
        }
    </style>
    """

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

def generate_printable_report(person_data, all_person_history_df=None):
    """
    Generates a single-page, modern, auto-printing HTML report with FULL data points.
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
    rec_kidney = []
    uric = get_float("Uric Acid", person_data)
    if uric and uric > 7: rec_kidney.append("กรดยูริกสูง ควรลดการทานเครื่องในสัตว์ ยอดผัก และสัตว์ปีก")
    
    rec_sugar_lipid = []
    fbs = get_float("FBS", person_data)
    if fbs and fbs >= 100: rec_sugar_lipid.append("ระดับน้ำตาลสูง ควรควบคุมอาหารประเภทแป้ง/น้ำตาล")
    chol = get_float("CHOL", person_data)
    ldl = get_float("LDL", person_data)
    tgl = get_float("TGL", person_data)
    if (chol and chol > 200) or (ldl and ldl > 130) or (tgl and tgl > 150): rec_sugar_lipid.append("ไขมันในเลือดสูง เลี่ยงของทอด/มัน/กะทิ")
    
    rec_liver = []
    sgot = get_float("SGOT", person_data)
    sgpt = get_float("SGPT", person_data)
    alp = get_float("ALP", person_data)
    if (sgot and sgot > 40) or (sgpt and sgpt > 40) or (alp and (alp > 105 or alp < 35)): rec_liver.append("ค่าตับสูงกว่าปกติ งดแอลกอฮอล์/ยาไม่จำเป็น")

    rec_vitals = [] # Use for BP
    if sbp and sbp >= 140: rec_vitals.append("ความดันโลหิตสูง ลดเค็ม/ออกกำลังกาย")

    # --- 3. Build Lab Blocks ---
    
    # Hematology
    hb_low = 12 if sex == "หญิง" else 13
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
    cxr_val = person_data.get("CXR", person_data.get(f"CXR{str(datetime.now().year+543)[-2:]}", "-"))
    cxr_display = interpret_cxr(cxr_val)
    
    ekg_val = person_data.get("EKG", person_data.get(f"EKG{str(datetime.now().year+543)[-2:]}", "-"))
    ekg_display = interpret_ekg(ekg_val)

    # Hepatitis
    hep_a = safe_value(person_data.get("Hepatitis A"))
    hbsag = safe_value(person_data.get("HbsAg"))
    hbsab = safe_value(person_data.get("HbsAb"))
    hbcab = safe_value(person_data.get("HBcAb"))
    
    # --- 4. Main Doctor's Suggestion (Generic + Doctor Note) ---
    main_suggestions = []
    
    # Insert Vitals Recommendation here if exists (since Vitals is top bar)
    if rec_vitals: main_suggestions.extend(rec_vitals)

    doc_note = str(person_data.get("DOCTER suggest", "")).strip()
    if doc_note and doc_note != "-":
        main_suggestions.append(f"{doc_note}")
        
    suggestion_html = "<br>".join([f"- {s}" for s in main_suggestions]) if main_suggestions else "สุขภาพโดยรวมอยู่ในเกณฑ์ดี โปรดรักษาสุขภาพให้แข็งแรงอยู่เสมอ"

    # --- 5. Assemble Final HTML ---
    
    # Create unique identifier to force re-render in Streamlit/Browser
    unique_id = datetime.now().strftime("%Y%m%d%H%M%S%f")

    return f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>Health Report - {name}</title>
        {get_report_css()}
    </head>
    <body onload="setTimeout(function(){{window.print();}}, 500)">
        <!-- Force Reload ID: {unique_id} -->
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
                    <div class="section-title">ความสมบูรณ์ของเม็ดเลือด (CBC)</div>
                    <table>
                        <thead><tr><th>รายการตรวจ</th><th>ผลตรวจ</th><th>ค่าปกติ</th></tr></thead>
                        <tbody>{cbc_rows}</tbody>
                    </table>

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

                    <div class="section-title">ปัสสาวะ (Urinalysis)</div>
                    <table>
                        <thead><tr><th>รายการตรวจ</th><th>ผลตรวจ</th><th>ค่าปกติ</th></tr></thead>
                        <tbody>{u_rows}</tbody>
                    </table>
                    
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

                    <div class="section-title">ไวรัสตับอักเสบ (Hepatitis)</div>
                    <table>
                        <tbody>
                            <tr><td>Hepatitis A</td><td class="val-col">{hep_a}</td><td class="range-col">Neg</td></tr>
                            <tr><td>HBsAg (เชื้อ)</td><td class="val-col">{hbsag}</td><td class="range-col">Neg</td></tr>
                            <tr><td>HBsAb (ภูมิ)</td><td class="val-col">{hbsab}</td><td class="range-col">Pos</td></tr>
                            <tr><td>HBcAb</td><td class="val-col">{hbcab}</td><td class="range-col">Neg</td></tr>
                        </tbody>
                    </table>

                    <div class="section-title">เอกซเรย์ปอด และ คลื่นไฟฟ้าหัวใจ (Chest X-ray & EKG)</div>
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
                    
                    <!-- Summary Box in Right Column -->
                    <div class="summary-box">
                        <div class="summary-title">สรุปผลการตรวจและคำแนะนำแพทย์ (Doctor's Recommendation)</div>
                        <div class="summary-content">
                            {suggestion_html}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <div class="footer">
                <div class="signature-line">
                    <div class="signature-dash"></div>
                    <b>นายแพทย์นพรัตน์ รัชฎาพร</b><br>
                    แพทย์อาชีวเวชศาสตร์ (ว.26674)<br>
                    ผู้ตรวจ (Attending Physician)
                </div>
            </div>

        </div>
    </body>
    </html>
    """
