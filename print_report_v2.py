import pandas as pd
import html
import json
from datetime import datetime
import numpy as np

# --- Import Logic การแปลผล (คงเดิม) ---
try:
    from performance_tests import (
        interpret_audiogram, interpret_lung_capacity, 
        interpret_cxr, interpret_ekg, interpret_urine, 
        interpret_stool, interpret_hepatitis, interpret_vision
    )
    from print_report import (
        interpret_rbc, interpret_wbc, is_urine_abnormal, 
        interpret_stool_exam, interpret_stool_cs, hepatitis_b_advice,
        generate_fixed_recommendations, generate_cbc_recommendations,
        generate_urine_recommendations, generate_doctor_opinion,
        is_empty, get_float, flag, safe_value
    )
except ImportError:
    # Fallback กรณี Import ไม่ได้
    def is_empty(val): return pd.isna(val) or str(val).strip() == ""
    def get_float(col, d): return None
    def flag(v, l=None, h=None, hib=False): return str(v), False
    def safe_value(v): return "-"
    def generate_fixed_recommendations(p): return []
    def generate_doctor_opinion(p, s, c, u): return "-"
    def generate_cbc_recommendations(p, s): return {}
    def generate_urine_recommendations(p, s): return {}

# --- CSS Design 9.1 (Force Dark Green Matte Header & Thick Border) ---
def get_single_page_style():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
        
        @page {
            size: A4;
            margin: 0; /* ตัด Margin ของ Browser ออก เพื่อคุมเองใน Body */
        }
        
        body {
            font-family: 'Sarabun', sans-serif;
            font-size: 14px;
            line-height: 1.35;
            color: #333;
            background: #fff;
            margin: 0;
            padding: 10mm;
            width: 210mm;
            height: 296mm;
            box-sizing: border-box;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .content-wrapper {
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 12px;
            transform-origin: top center;
        }

        /* --- Header --- */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            border-bottom: 4px solid #004d40 !important; /* เส้นใต้เข้มหนา */
            padding-bottom: 10px;
            margin-bottom: 5px;
        }
        .header-left h1 { margin: 0; font-size: 26px; color: #004d40 !important; line-height: 1.1; font-weight: 700; }
        .header-left p { margin: 4px 0 0 0; font-size: 15px; color: #555; font-weight: 500; }
        .header-right { text-align: right; }
        .header-right h2 { margin: 0; font-size: 20px; font-weight: 700; color: #000; }
        .patient-meta { font-size: 14px; margin-top: 5px; color: #444; }
        .patient-badge { 
            display: inline-block; background: #f0f0f0; padding: 2px 8px; 
            border-radius: 4px; font-weight: 600; margin-left: 5px; border: 1px solid #ccc;
        }

        /* --- Vitals --- */
        .vitals-bar {
            display: flex;
            justify-content: space-between;
            background-color: #fff;
            border-radius: 8px;
            padding: 10px 15px;
            border: 2px solid #004d40 !important; /* กรอบสัญญาณชีพสีเขียวเข้ม */
            box-shadow: none; /* เอาเงาออกให้ดู Matte (ด้าน) */
        }
        .vital-box { text-align: center; position: relative; width: 16%; }
        .vital-box:not(:last-child)::after {
            content: ''; position: absolute; right: 0; top: 10%; height: 80%; width: 1px; background: #ddd;
        }
        .vital-label { font-size: 12px; color: #555; font-weight: 600; text-transform: uppercase; margin-bottom: 3px; }
        .vital-value { font-size: 18px; font-weight: 700; color: #004d40 !important; }
        .vital-unit { font-size: 12px; color: #888; font-weight: 400; margin-left: 2px; }

        /* --- Lab Grid --- */
        .lab-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 15px;
            align-items: start;
        }
        .lab-col { display: flex; flex-direction: column; gap: 12px; }

        .card {
            border: 2px solid #004d40 !important; /* บังคับขอบหนา 2px สีเขียวเข้ม */
            border-radius: 6px;
            overflow: hidden;
            box-shadow: none; /* เอาเงาออก */
            background: #fff;
        }
        .card-header {
            background-color: #004d40 !important; /* บังคับพื้นหลังสีเขียวเข้มด้าน */
            color: #fff !important; /* ตัวหนังสือสีขาว */
            padding: 8px 10px;
            font-size: 14px; 
            font-weight: 700;
            text-transform: uppercase;
        }
        .card-body { padding: 0; background: #fff; }

        /* Table */
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th { 
            background-color: #e0f2f1; /* สีพื้นหลังหัวตารางเขียวอ่อนๆ จางๆ */
            padding: 6px 8px; 
            text-align: left; 
            font-weight: 700; 
            color: #004d40 !important; /* หัวตารางสีเขียวเข้ม */
            border-bottom: 2px solid #004d40 !important; 
            font-size: 13px;
        }
        td { 
            padding: 6px 8px; 
            border-bottom: 1px solid #eee; 
            vertical-align: middle; 
            color: #222;
        }
        tr:last-child td { border-bottom: none; }
        tr:nth-child(even) { background-color: #fafafa; } 
        
        .result-val { font-weight: 600; text-align: center; }
        .abnormal { color: #d32f2f !important; font-weight: 800; } 
        .bg-abnormal { background-color: #ffebee !important; } 

        /* --- Special Item --- */
        .special-item {
            border-bottom: 1px solid #f0f0f0;
            padding: 8px 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #fff;
        }
        .special-item:last-child { border-bottom: none; }
        .sp-label { font-weight: 600; color: #444; font-size: 14px; }
        .sp-value { font-weight: 600; font-size: 14px; text-align: right;}
        .sp-abnormal { color: #d32f2f; }
        .sp-normal { color: #2e7d32; }
        
        /* --- Footer --- */
        .footer-section {
            display: flex;
            gap: 20px;
            border: 2px solid #004d40 !important; /* ขอบหนาสีเขียวเข้ม */
            border-radius: 6px;
            padding: 15px;
            background-color: #fff;
            flex-grow: 1; 
        }
        .doctor-opinion { flex: 1; border-right: 1px solid #eee; padding-right: 15px; }
        .recommendations { flex: 1.2; padding-left: 5px; }
        
        .footer-title { 
            font-size: 15px; font-weight: 700; color: #004d40 !important; 
            margin-bottom: 8px; text-transform: uppercase;
            display: flex; align-items: center; gap: 5px;
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }
        .footer-title::before { content: '■'; color: #004d40; font-size: 12px; line-height: 0; }
        
        .footer-text { font-size: 14px; color: #333; line-height: 1.5; margin-top: 5px; } 
        ul { margin: 0; padding-left: 20px; }
        li { margin-bottom: 4px; }

        /* --- Signature --- */
        .signature-row {
            display: flex;
            justify-content: flex-end;
            margin-top: 15px;
        }
        .signature-box { text-align: center; width: 250px; }
        .sig-line { border-bottom: 1px dashed #aaa; width: 100%; height: 30px; margin-bottom: 6px; }
        .sig-name { font-weight: 700; font-size: 15px; color: #222; }
        .sig-role { font-size: 13px; color: #666; }

        @media print {
            body { -webkit-print-color-adjust: exact; padding: 0; margin: 0; }
            .content-wrapper { padding: 10mm; width: 100%; box-sizing: border-box; }
        }
    </style>
    
    <script>
        window.onload = function() {
            var content = document.getElementById('content');
            var availableHeight = 1045; 
            var contentHeight = content.scrollHeight;

            if (contentHeight > availableHeight) {
                var scale = availableHeight / contentHeight;
                scale = scale * 0.99; 
                content.style.transform = "scale(" + scale + ")";
                content.style.width = (100 / scale) + "%";
                content.style.transformOrigin = "top left"; 
            }
        };
    </script>
    """

def render_vitals(person):
    def get_v(key, unit=""):
        val = get_float(key, person)
        return f"{val} <span class='vital-unit'>{unit}</span>" if val else "-"
    
    sbp, dbp = get_float("SBP", person), get_float("DBP", person)
    bp = f"{int(sbp)}/{int(dbp)}" if sbp and dbp else "-"
    
    w = get_float("น้ำหนัก", person)
    h = get_float("ส่วนสูง", person)
    bmi = w / ((h/100)**2) if w and h else 0
    
    return f"""
    <div class="vitals-bar">
        <div class="vital-box"><div class="vital-label">น้ำหนัก (Weight)</div><div class="vital-value">{get_v('น้ำหนัก')}</div></div>
        <div class="vital-box"><div class="vital-label">ส่วนสูง (Height)</div><div class="vital-value">{get_v('ส่วนสูง')}</div></div>
        <div class="vital-box"><div class="vital-label">BMI</div><div class="vital-value">{bmi:.1f}</div></div>
        <div class="vital-box"><div class="vital-label">รอบเอว (Waist)</div><div class="vital-value">{person.get('รอบเอว', '-') or '-'} <span class="vital-unit">cm</span></div></div>
        <div class="vital-box"><div class="vital-label">ความดัน (BP)</div><div class="vital-value">{bp} <span class="vital-unit">mmHg</span></div></div>
        <div class="vital-box"><div class="vital-label">ชีพจร (Pulse)</div><div class="vital-value">{get_v('pulse')} <span class="vital-unit">bpm</span></div></div>
    </div>
    """

def render_table(title, headers, rows):
    html = f"""
    <div class="card">
        <div class="card-header">{title}</div>
        <div class="card-body">
            <table>
                <thead><tr>""" + "".join([f"<th>{h}</th>" for h in headers]) + """</tr></thead>
                <tbody>
    """
    for row in rows:
        is_row_abn = any(item[1] for item in row)
        tr_class = "bg-abnormal" if is_row_abn else ""
        html += f"<tr class='{tr_class}'>"
        for i, (text, is_abn) in enumerate(row):
            td_class = "abnormal" if is_abn else ""
            align = 'center' if i > 0 else 'left'
            html += f"<td style='text-align:{align};' class='{td_class}'>{text}</td>"
        html += "</tr>"
    html += "</tbody></table></div></div>"
    return html

def render_special_item(label, value, is_abn=False):
    val_class = "sp-abnormal" if is_abn else "sp-normal"
    if "ปกติ" in str(value) or "Normal" in str(value) or "ไม่พบ" in str(value):
        val_class = "sp-normal"
    elif value == "-" or value == "":
        val_class = ""
    else:
        val_class = "sp-abnormal"
        
    return f"""
    <div class="special-item">
        <span class="sp-label">{label}</span>
        <span class="sp-value {val_class}">{value}</span>
    </div>
    """

def generate_single_page_report(person_data, all_history_df=None):
    sex = person_data.get("เพศ", "ชาย")
    year = person_data.get("Year", datetime.now().year + 543)
    
    # 1. CBC
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_data = [
        ("Hb", "Hb(%)", ">13,>12", hb_low, None),
        ("Hct", "HCT", ">39,>36", hct_low, None),
        ("WBC", "WBC", "4-10k", 4000, 10000),
        ("Plt", "Plt", "1.5-5แสน", 150000, 500000)
    ]
    cbc_rows = [[(l, False), flag(get_float(k, person_data), low, high), (n, False)] for l, k, n, low, high in cbc_data]

    # 2. Chemistry
    chem_sugar_lipid = [
        ("FBS", "FBS", "74-106", 74, 106),
        ("Chol", "CHOL", "<200", None, 200),
        ("Trig", "TGL", "<150", None, 150),
        ("HDL", "HDL", ">40", 40, None, True),
        ("LDL", "LDL", "<130", None, 130)
    ]
    chem_rows_1 = [[(l, False), flag(get_float(k, person_data), low, high, hib if 'hib' in locals() else False), (n, False)] for l, k, n, low, high, *hib in chem_sugar_lipid]

    chem_organ = [
        ("Uric", "Uric Acid", "<7.2", None, 7.2),
        ("Cr", "Cr", "0.5-1.2", 0.5, 1.17),
        ("GFR", "GFR", ">60", 60, None, True),
        ("SGOT", "SGOT", "<37", None, 37),
        ("SGPT", "SGPT", "<41", None, 41)
    ]
    chem_rows_2 = [[(l, False), flag(get_float(k, person_data), low, high, hib if 'hib' in locals() else False), (n, False)] for l, k, n, low, high, *hib in chem_organ]

    # 3. Urine & Stool
    urine_items = [
        ("Sugar", person_data.get("sugar", "-"), "Neg"),
        ("Prot.", person_data.get("Alb", "-"), "Neg"),
        ("RBC", person_data.get("RBC1", "-"), "0-2"),
        ("WBC", person_data.get("WBC1", "-"), "0-5")
    ]
    urine_rows = [[(l, False), (v, is_urine_abnormal(l, v, n)), (n, False)] for l, v, n in urine_items]
    
    stool_exam = interpret_stool_exam(person_data.get("Stool exam", ""))
    stool_short = "ปกติ" if "ปกติ" in stool_exam else ("ผิดปกติ" if "พบ" in stool_exam else "-")
    urine_rows.append([("Stool", False), (stool_short, stool_short=="ผิดปกติ"), ("Normal", False)])

    # 4. Special Tests
    cxr_val, _ = interpret_cxr(person_data.get(f"CXR{str(year)[-2:]}", person_data.get("CXR")))
    cxr_val = cxr_val.split('⚠️')[0].strip()
    
    ekg_val, _ = interpret_ekg(person_data.get(f"EKG{str(year)[-2:]}", person_data.get("EKG")))
    ekg_val = ekg_val.split('⚠️')[0].strip()
    
    vision_s, color_s, _ = interpret_vision(person_data.get('สรุปเหมาะสมกับงาน', ''), person_data.get('Color_Blind', ''))
    
    hear_res = interpret_audiogram(person_data, all_history_df)
    hear_short = f"R:{hear_res['summary']['right']} L:{hear_res['summary']['left']}"
    
    lung_s, _, lung_raw = interpret_lung_capacity(person_data)
    lung_short = lung_s.replace("สมรรถภาพปอด", "").strip()
    if "ปกติ" not in lung_short and "ไม่ได้" not in lung_short:
        lung_short = "ผิดปกติ"

    # --- Recommendations ---
    cbc_rec = generate_cbc_recommendations(person_data, sex)
    urine_rec = generate_urine_recommendations(person_data, sex)
    doc_op = generate_doctor_opinion(person_data, sex, cbc_rec, urine_rec)
    
    if len(doc_op) > 500: doc_op = doc_op[:500] + "..." # เพิ่ม Limit ตัวอักษรเผื่อไว้

    rec_list = generate_fixed_recommendations(person_data)
    rec_html = "<ul>" + "".join([f"<li>{r}</li>" for r in rec_list]) + "</ul>" if rec_list else "<ul><li>ดูแลสุขภาพตามปกติ พักผ่อนให้เพียงพอ</li></ul>"

    return f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลสุขภาพ (Matte Green 2.0) - {person_data.get('ชื่อ-สกุล')}</title>
        {get_single_page_style()}
    </head>
    <body>
        <div class="content-wrapper" id="content">
            <!-- Header -->
            <div class="header">
                <div class="header-left">
                    <h1>รายงานผลการตรวจสุขภาพ</h1>
                    <p>คลินิกตรวจสุขภาพ โรงพยาบาลสันทราย</p>
                </div>
                <div class="header-right">
                    <h2>{person_data.get('ชื่อ-สกุล', '-')}</h2>
                    <div class="patient-meta">
                        HN: <b>{person_data.get('HN', '-')}</b> | 
                        อายุ: <b>{int(get_float('อายุ', person_data) or 0)} ปี</b>
                        <span class="patient-badge">{person_data.get('หน่วยงาน', 'ไม่ระบุ')}</span>
                    </div>
                    <div style="font-size: 13px; color: #666; margin-top: 5px;">วันที่ตรวจ: <b>{person_data.get('วันที่ตรวจ', '-')}</b></div>
                </div>
            </div>

            <!-- Vitals -->
            {render_vitals(person_data)}

            <!-- Lab Results Grid (3 Columns) -->
            <div class="lab-grid">
                <div class="lab-col">
                    {render_table("ความสมบูรณ์เลือด (CBC)", ["รายการ", "ผล", "ปกติ"], cbc_rows)}
                    {render_table("ปัสสาวะ/อุจจาระ (Urine/Stool)", ["รายการ", "ผล", "ปกติ"], urine_rows)}
                </div>
                <div class="lab-col">
                    {render_table("ไขมัน & น้ำตาล (Lipid/Sugar)", ["รายการ", "ผล", "ปกติ"], chem_rows_1)}
                    
                    <!-- Special Tests Box 1 -->
                    <div class="card">
                        <div class="card-header">การมองเห็น & การได้ยิน</div>
                        <div class="card-body">
                            {render_special_item("สายตา", vision_s)}
                            {render_special_item("ตาบอดสี", color_s)}
                            {render_special_item("การได้ยิน", hear_short)}
                        </div>
                    </div>
                </div>
                <div class="lab-col">
                    {render_table("การทำงานไต & ตับ (Kidney/Liver)", ["รายการ", "ผล", "ปกติ"], chem_rows_2)}
                    
                    <!-- Special Tests Box 2 -->
                    <div class="card">
                        <div class="card-header">เอกซเรย์ & อื่นๆ</div>
                        <div class="card-body">
                            {render_special_item("CXR (ปอด)", cxr_val)}
                            {render_special_item("EKG (หัวใจ)", ekg_val)}
                            {render_special_item("สมรรถภาพปอด", lung_short)}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Footer: Conclusion & Recommendations -->
            <div class="footer-section">
                <div class="doctor-opinion">
                    <div class="footer-title">สรุปความเห็นแพทย์ (Doctor's Opinion)</div>
                    <div class="footer-text">{doc_op}</div>
                </div>
                <div class="recommendations">
                    <div class="footer-title">คำแนะนำ (Recommendations)</div>
                    <div class="footer-text">{rec_html}</div>
                </div>
            </div>

            <!-- Signature -->
            <div class="signature-row">
                <div class="signature-box">
                    <div class="sig-line"></div>
                    <div class="sig-name">นายแพทย์นพรัตน์ รัชฎาพร</div>
                    <div class="sig-role">แพทย์อาชีวเวชศาสตร์ (ว.26674)</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
