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
    inverse=True means lower is better (e.g. LDL should be low) - *Wait, usually ranges handle this*
    Actually, let's stick to simple low/high logic.
    If only high is provided (e.g. < 100), low is None.
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

def interpret_urine_result(val, normal_list):
    val = str(val).strip().lower()
    if val in ["", "-", "none", "nan"]: return safe_value(val), False
    if val in normal_list: return str(val), False
    return str(val), True

# --- HTML Generation Parts ---

def get_report_css():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
        
        :root {
            --primary-color: #2c3e50;
            --secondary-color: #34495e;
            --accent-color: #16a085;
            --danger-color: #c0392b;
            --light-bg: #f8f9fa;
            --border-color: #bdc3c7;
        }

        body {
            font-family: 'Sarabun', sans-serif;
            font-size: 13px; /* Optimized for A4 single page */
            line-height: 1.3;
            color: #333;
            margin: 0;
            padding: 20px;
            background-color: #fff;
            -webkit-print-color-adjust: exact;
        }

        @page {
            size: A4;
            margin: 0.5cm; /* Small margins to fit everything */
        }

        /* Layout Utility */
        .container { width: 100%; max-width: 210mm; margin: 0 auto; }
        .row { display: flex; flex-wrap: wrap; margin: 0 -5px; }
        .col { flex: 1; padding: 0 5px; }
        .col-40 { width: 40%; flex: none; padding: 0 5px; }
        .col-60 { width: 60%; flex: none; padding: 0 5px; }
        .col-50 { width: 50%; flex: none; padding: 0 5px; }

        /* Header */
        .header {
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 10px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }
        .header h1 { font-size: 20px; font-weight: 700; color: var(--primary-color); margin: 0; }
        .header p { margin: 2px 0 0; font-size: 12px; color: var(--secondary-color); }
        .patient-info { font-size: 12px; text-align: right; }
        .patient-info b { color: var(--primary-color); }

        /* Vitals Bar */
        .vitals-bar {
            background-color: var(--light-bg);
            border-radius: 6px;
            padding: 8px 15px;
            margin-bottom: 15px;
            border: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            font-size: 13px;
        }
        .vital-item b { color: var(--accent-color); font-weight: 700; margin-right: 4px; }

        /* Section Styling */
        .section-title {
            font-size: 14px;
            font-weight: 700;
            color: #fff;
            background-color: var(--primary-color);
            padding: 4px 10px;
            border-radius: 4px;
            margin-bottom: 5px;
            margin-top: 10px;
        }
        
        /* Tables */
        table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 5px; }
        th, td { padding: 3px 6px; border-bottom: 1px solid #eee; text-align: left; }
        th { background-color: #f1f2f6; font-weight: 600; color: var(--secondary-color); text-align: center;}
        td.val-col { text-align: center; font-weight: 500; }
        td.range-col { text-align: center; color: #7f8c8d; font-size: 11px; }
        
        .abnormal { color: var(--danger-color); font-weight: 700; }
        
        /* Summary Box */
        .summary-box {
            border: 1px solid var(--accent-color);
            background-color: #e8f8f5;
            border-radius: 6px;
            padding: 10px;
            margin-top: 15px;
            page-break-inside: avoid;
        }
        .summary-title { font-weight: 700; color: var(--accent-color); margin-bottom: 5px; font-size: 14px; }
        .summary-content { font-size: 13px; }
        
        /* Footer */
        .footer {
            margin-top: 20px;
            text-align: right;
            font-size: 12px;
            page-break-inside: avoid;
        }
        .signature-line {
            display: inline-block;
            border-top: 1px dotted #999;
            width: 200px;
            margin-top: 30px;
            padding-top: 5px;
            text-align: center;
        }

        /* Print adjustments */
        @media print {
            body { margin: 0; padding: 0; }
            .no-print { display: none; }
        }
    </style>
    """

def render_lab_row(name, value, unit, normal_range, is_abnormal):
    cls = "abnormal" if is_abnormal else ""
    val_display = value if value != "-" else "-"
    return f"""
    <tr>
        <td>{name}</td>
        <td class="val-col {cls}">{val_display} <span style="font-size:10px; color:#999;">{unit}</span></td>
        <td class="range-col">{normal_range}</td>
    </tr>
    """

def generate_printable_report(person_data, all_person_history_df=None):
    """
    Generates a single-page, modern, auto-printing HTML report.
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

    # --- 2. Build Lab Blocks ---
    
    # Hematology
    hb_low = 12 if sex == "หญิง" else 13
    hct_low = 36 if sex == "หญิง" else 39
    
    cbc_data = [
        ("Hemoglobin", "Hb(%)", None, hb_low, None, "g/dL", f"> {hb_low}"),
        ("Hematocrit", "HCT", None, hct_low, None, "%", f"> {hct_low}"),
        ("WBC Count", "WBC (cumm)", None, 4000, 10000, "cells/mm³", "4,000-10,000"),
        ("Platelet", "Plt (/mm)", None, 150000, 450000, "cells/mm³", "150,000-450,000")
    ]
    cbc_rows = ""
    for label, key, _, low, high, unit, norm_text in cbc_data:
        val, is_abn = flag_abnormal(person_data.get(key), low, high)
        cbc_rows += render_lab_row(label, val, unit, norm_text, is_abn)

    # Biochemistry
    bio_data = [
        ("Fasting Blood Sugar", "FBS", None, 70, 100, "mg/dL", "70-100"),
        ("Cholesterol", "CHOL", None, 0, 200, "mg/dL", "< 200"),
        ("Triglyceride", "TGL", None, 0, 150, "mg/dL", "< 150"),
        ("HDL-C", "HDL", None, 40, None, "mg/dL", "> 40"), # High is good, so low is abn
        ("LDL-C", "LDL", None, 0, 130, "mg/dL", "< 130"),
        ("Uric Acid", "Uric Acid", None, 2.4, 7.0, "mg/dL", "2.4-7.0"),
        ("Creatinine", "Cr", None, 0.5, 1.2, "mg/dL", "0.5-1.2"),
        ("GFR", "GFR", None, 90, None, "mL/min", "> 90"),
        ("SGOT (AST)", "SGOT", None, 0, 40, "U/L", "< 40"),
        ("SGPT (ALT)", "SGPT", None, 0, 40, "U/L", "< 40"),
        ("Alkaline Phos.", "ALP", None, 35, 105, "U/L", "35-105"),
    ]
    bio_rows = ""
    for label, key, _, low, high, unit, norm_text in bio_data:
        # Special handling for GFR/HDL where higher is better (sort of)
        # Simplified: Just check limits
        val_raw = get_float(key, person_data)
        is_abn = False
        val_fmt = safe_value(person_data.get(key))
        
        if val_raw is not None:
            if key == "HDL" and val_raw < 40: is_abn = True
            elif key == "GFR" and val_raw < 60: is_abn = True # CKD stage 3+
            else:
                _, is_abn = flag_abnormal(val_raw, low, high)
            val_fmt = f"{val_raw:,.0f}" if val_raw.is_integer() else f"{val_raw:,.1f}"
            
        bio_rows += render_lab_row(label, val_fmt, unit, norm_text, is_abn)

    # Urinalysis (Compact)
    urine_color = safe_value(person_data.get("Color"))
    urine_ph = safe_value(person_data.get("pH"))
    urine_spgr = safe_value(person_data.get("Spgr"))
    urine_alb = safe_value(person_data.get("Alb"))
    urine_sugar = safe_value(person_data.get("sugar"))
    urine_rbc = safe_value(person_data.get("RBC1"))
    urine_wbc = safe_value(person_data.get("WBC1"))
    
    # Simple logic for urine abn
    u_rows = ""
    u_rows += render_lab_row("Color", urine_color, "", "Yellow", urine_color.lower() not in ['yellow', 'pale yellow'])
    u_rows += render_lab_row("pH", urine_ph, "", "4.6-8.0", False) # Skipping strict ph check
    u_rows += render_lab_row("Albumin", urine_alb, "", "Negative", urine_alb.lower() not in ['negative', '-'])
    u_rows += render_lab_row("Sugar", urine_sugar, "", "Negative", urine_sugar.lower() not in ['negative', '-'])
    u_rows += render_lab_row("RBC", urine_rbc, "cells", "0-2", urine_rbc not in ['0-1', '0-2', 'negative', '-'])
    u_rows += render_lab_row("WBC", urine_wbc, "cells", "0-5", urine_wbc not in ['0-1', '0-2', '0-3', '0-5', 'negative', '-'])

    # Other Tests
    cxr = safe_value(person_data.get("CXR", person_data.get(f"CXR{str(datetime.now().year+543)[-2:]}", "-")))
    cxr_abn = "pid" in cxr.lower() or "abnormal" in cxr.lower() or "พบ" in cxr # Rough check
    
    ekg = safe_value(person_data.get("EKG", person_data.get(f"EKG{str(datetime.now().year+543)[-2:]}", "-")))
    ekg_abn = "abnormal" in ekg.lower() or "ischemia" in ekg.lower()

    # Hepatitis
    hbsag = safe_value(person_data.get("HbsAg"))
    hbsab = safe_value(person_data.get("HbsAb"))
    
    # --- 3. Construct Doctor's Suggestion ---
    # Combine logic from previous helper
    suggestions = []
    
    # BP
    if sbp and sbp >= 140: suggestions.append("- ความดันโลหิตสูง ควรควบคุมอาหารเค็มและออกกำลังกาย")
    # Sugar
    fbs = get_float("FBS", person_data)
    if fbs and fbs >= 100: suggestions.append("- ระดับน้ำตาลในเลือดสูง ควรควบคุมอาหารประเภทแป้งและน้ำตาล")
    # Lipids
    chol = get_float("CHOL", person_data)
    ldl = get_float("LDL", person_data)
    if (chol and chol > 200) or (ldl and ldl > 130): suggestions.append("- ไขมันในเลือดสูง ควรหลีกเลี่ยงของทอด ของมัน และกะทิ")
    # Uric
    uric = get_float("Uric Acid", person_data)
    if uric and uric > 7: suggestions.append("- กรดยูริกสูง ควรลดการทานเครื่องในสัตว์ ยอดผัก และสัตว์ปีก")
    # Liver
    sgot = get_float("SGOT", person_data)
    sgpt = get_float("SGPT", person_data)
    if (sgot and sgot > 40) or (sgpt and sgpt > 40): suggestions.append("- ค่าเอนไซม์ตับสูงกว่าปกติ ควรลดแอลกอฮอล์และพักผ่อนให้เพียงพอ")
    
    # Manual Doctor Input
    doc_note = str(person_data.get("DOCTER suggest", "")).strip()
    if doc_note and doc_note != "-":
        suggestions.append(f"- {doc_note}")
        
    suggestion_html = "<br>".join(suggestions) if suggestions else "สุขภาพโดยรวมอยู่ในเกณฑ์ดี โปรดรักษาสุขภาพให้แข็งแรงอยู่เสมอ"

    # --- 4. Assemble Final HTML ---
    
    return f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>Health Report - {name}</title>
        {get_report_css()}
    </head>
    <body onload="setTimeout(function(){{window.print();}}, 500)">
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
                    <div class="section-title">🩸 ความสมบูรณ์ของเม็ดเลือด (CBC)</div>
                    <table>
                        <thead><tr><th>รายการตรวจ</th><th>ผลตรวจ</th><th>ค่าปกติ</th></tr></thead>
                        <tbody>{cbc_rows}</tbody>
                    </table>

                    <div class="section-title">🧪 การทำงานของไต (Kidney Function)</div>
                    <table>
                        <thead><tr><th>รายการตรวจ</th><th>ผลตรวจ</th><th>ค่าปกติ</th></tr></thead>
                        <tbody>
                            {render_lab_row("Creatinine", safe_value(person_data.get("Cr")), "mg/dL", "0.5-1.2", False)}
                            {render_lab_row("eGFR", safe_value(person_data.get("GFR")), "mL/min", ">90", False)}
                        </tbody>
                    </table>

                    <div class="section-title">🚽 ปัสสาวะ (Urinalysis)</div>
                    <table>
                        <thead><tr><th>รายการตรวจ</th><th>ผลตรวจ</th><th>ค่าปกติ</th></tr></thead>
                        <tbody>{u_rows}</tbody>
                    </table>
                    
                    <div class="section-title">💩 อุจจาระ (Stool)</div>
                    <table>
                        <tbody>
                            <tr><td>Stool Exam</td><td class="val-col">{safe_value(person_data.get("Stool exam"))}</td></tr>
                            <tr><td>Stool Culture</td><td class="val-col">{safe_value(person_data.get("Stool C/S"))}</td></tr>
                        </tbody>
                    </table>
                </div>

                <!-- Right Column -->
                <div class="col-50">
                    <div class="section-title">🍬 เบาหวาน & ไขมัน (Sugar & Lipid)</div>
                    <table>
                        <thead><tr><th>รายการตรวจ</th><th>ผลตรวจ</th><th>ค่าปกติ</th></tr></thead>
                        <tbody>{bio_rows}</tbody>
                    </table>

                    <div class="section-title">💉 ไวรัสตับอักเสบ (Hepatitis)</div>
                    <table>
                        <tbody>
                            <tr><td>HBsAg (เชื้อ)</td><td class="val-col">{hbsag}</td><td>Neg</td></tr>
                            <tr><td>HBsAb (ภูมิ)</td><td class="val-col">{hbsab}</td><td>Pos</td></tr>
                        </tbody>
                    </table>

                    <div class="section-title">🩻 เอกซเรย์ & คลื่นไฟฟ้าหัวใจ</div>
                    <table>
                        <tbody>
                            <tr>
                                <td><b>Chest X-Ray</b></td>
                                <td class="val-col" style="text-align:left; font-size:11px;">{cxr}</td>
                            </tr>
                            <tr>
                                <td><b>EKG</b></td>
                                <td class="val-col" style="text-align:left; font-size:11px;">{ekg}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Summary Box -->
            <div class="summary-box">
                <div class="summary-title">🩺 สรุปผลการตรวจและคำแนะนำแพทย์ (Doctor's Recommendation)</div>
                <div class="summary-content">
                    {suggestion_html}
                </div>
            </div>

            <!-- Footer -->
            <div class="footer">
                <div class="signature-line">
                    <b>นายแพทย์นพรัตน์ รัชฎาพร</b><br>
                    แพทย์อาชีวเวชศาสตร์ (ว.26674)<br>
                    ผู้ตรวจ (Attending Physician)
                </div>
            </div>

        </div>
    </body>
    </html>
    """
