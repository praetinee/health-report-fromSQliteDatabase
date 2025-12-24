import pandas as pd
import html
import json
from datetime import datetime
import numpy as np

# Import Logic การแปลผลจากไฟล์เดิมเพื่อความถูกต้องของข้อมูล
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
    # Fallback หาก Import ไม่ได้ (ป้องกัน Error เบื้องต้น)
    def is_empty(val): return pd.isna(val) or str(val).strip() == ""
    def get_float(col, d): return None
    def flag(v, l=None, h=None, hib=False): return str(v), False
    def safe_value(v): return "-"

# --- CSS & JS for Auto-Scaling Single Page ---
def get_single_page_style():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
        
        @page {
            size: A4;
            margin: 5mm; /* ขอบกระดาษน้อยที่สุดเพื่อให้มีพื้นที่มากที่สุด */
        }
        
        body {
            font-family: 'Sarabun', sans-serif;
            font-size: 11px; /* ขนาดตั้งต้น */
            line-height: 1.2;
            color: #000;
            background: #fff;
            margin: 0;
            padding: 0;
            width: 210mm;
            height: 296mm; /* A4 Height */
            box-sizing: border-box;
            overflow: hidden; /* ห้าม Scroll */
        }

        .page-container {
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
        }

        /* --- Header --- */
        .header-row {
            display: flex;
            justify-content: space-between;
            border-bottom: 2px solid #00796B;
            padding-bottom: 5px;
            margin-bottom: 5px;
        }
        .hospital-info h1 { margin: 0; font-size: 16px; color: #00796B; }
        .hospital-info p { margin: 0; font-size: 10px; color: #555; }
        .patient-info { text-align: right; }
        .patient-info h2 { margin: 0; font-size: 14px; }
        .patient-info p { margin: 0; font-size: 10px; }

        /* --- Section Styling --- */
        .section-box {
            margin-bottom: 4px;
        }
        .section-title {
            background-color: #eee;
            font-weight: bold;
            font-size: 10px;
            padding: 2px 5px;
            border-left: 3px solid #00796B;
            margin-bottom: 2px;
        }

        /* --- Grid Layouts --- */
        .grid-2-col { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
        .grid-3-col { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 5px; }
        .grid-vitals { display: grid; grid-template-columns: repeat(6, 1fr); gap: 2px; background: #f9f9f9; padding: 3px; border-radius: 4px; margin-bottom: 5px; }

        /* --- Tables --- */
        table { width: 100%; border-collapse: collapse; font-size: 9.5px; }
        th { background-color: #f0f0f0; font-weight: bold; text-align: center; padding: 1px 3px; border: 1px solid #ccc; }
        td { border: 1px solid #ccc; padding: 1px 3px; text-align: center; }
        td.text-left { text-align: left; }
        .abnormal { color: red; font-weight: bold; }
        .row-abnormal { background-color: #fff0f0; }

        /* --- Content Blocks --- */
        .vital-item { text-align: center; }
        .vital-label { font-size: 9px; color: #666; }
        .vital-val { font-size: 11px; font-weight: bold; color: #000; }

        .recommendation-box {
            border: 1px solid #ddd;
            padding: 5px;
            border-radius: 4px;
            background-color: #fcfcfc;
            font-size: 10px;
            height: 100%; /* Fill remaining space */
        }
        
        .footer-sig {
            margin-top: auto; /* Push to bottom */
            text-align: right;
            padding-top: 10px;
            font-size: 10px;
        }

        /* Print Adjustments */
        @media print {
            body { 
                -webkit-print-color-adjust: exact; 
                margin: 0;
            }
        }
    </style>
    
    <script>
        // ฟังก์ชัน Auto-Scale: ถ้าเนื้อหายาวเกินหน้า A4 ให้ย่อ Zoom ลงเรื่อยๆ จนกว่าจะพอดี
        window.onload = function() {
            var container = document.getElementById('main-container');
            var body = document.body;
            var targetHeight = 1115; // ประมาณความสูง A4 ใน pixel (96dpi ~1123px เผื่อขอบนิดหน่อย)
            
            // ถ้าเนื้อหาสูงกว่าหน้ากระดาษ
            if (container.scrollHeight > targetHeight) {
                var scale = targetHeight / container.scrollHeight;
                // จำกัดไม่ให้เล็กเกินไป (เช่นไม่ต่ำกว่า 65%)
                if (scale < 0.65) scale = 0.65; 
                
                container.style.transform = "scale(" + scale + ")";
                container.style.transformOrigin = "top left";
                container.style.width = (100 / scale) + "%"; // ขยายความกว้างชดเชย
            }
        };
    </script>
    """

def render_vitals_strip(person):
    """สร้างแถบแสดงสัญญาณชีพแนวนอน"""
    try:
        w = get_float("น้ำหนัก", person)
        h = get_float("ส่วนสูง", person)
        bmi = w / ((h/100)**2) if w and h else 0
        sbp, dbp = get_float("SBP", person), get_float("DBP", person)
        bp = f"{int(sbp)}/{int(dbp)}" if sbp and dbp else "-"
        pulse = f"{int(get_float('pulse', person))}" if get_float('pulse', person) else "-"
        waist = person.get("รอบเอว", "-")
    except:
        w, h, bmi, bp, pulse, waist = "-", "-", 0, "-", "-", "-"
    
    bmi_fmt = f"{bmi:.1f}" if bmi > 0 else "-"
    
    return f"""
    <div class="grid-vitals">
        <div class="vital-item"><div class="vital-label">น้ำหนัก (kg)</div><div class="vital-val">{w}</div></div>
        <div class="vital-item"><div class="vital-label">ส่วนสูง (cm)</div><div class="vital-val">{h}</div></div>
        <div class="vital-item"><div class="vital-label">BMI (kg/m²)</div><div class="vital-val">{bmi_fmt}</div></div>
        <div class="vital-item"><div class="vital-label">รอบเอว (cm)</div><div class="vital-val">{waist}</div></div>
        <div class="vital-item"><div class="vital-label">ความดัน (BP)</div><div class="vital-val">{bp}</div></div>
        <div class="vital-item"><div class="vital-label">ชีพจร (Pulse)</div><div class="vital-val">{pulse}</div></div>
    </div>
    """

def render_lab_table_compact(title, headers, rows):
    """สร้างตารางผลแล็บแบบ Compact"""
    html = f"""
    <div class="section-box">
        <div class="section-title">{title}</div>
        <table>
            <thead><tr>""" + "".join([f"<th>{h}</th>" for h in headers]) + """</tr></thead>
            <tbody>
    """
    for row in rows:
        # row structure: [(text, is_abn), (text, is_abn), ...]
        tr_class = "row-abnormal" if any(item[1] for item in row) else ""
        html += f"<tr class='{tr_class}'>"
        for i, (text, is_abn) in enumerate(row):
            td_class = "abnormal" if is_abn else ""
            align_class = "text-left" if i == 0 else ""
            html += f"<td class='{td_class} {align_class}'>{text}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    return html

def generate_single_page_report(person_data, all_history_df=None):
    """ฟังก์ชันหลักสำหรับสร้าง HTML หน้าเดียว"""
    
    # 1. เตรียมข้อมูลพื้นฐาน
    sex = person_data.get("เพศ", "ชาย")
    year = person_data.get("Year", datetime.now().year + 543)
    
    # --- แปลผล CBC & Blood Chem (ใช้ Logic เดิม) ---
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    
    cbc_data = [
        ("Hb", "Hb(%)", "ช>13,ญ>12", hb_low, None),
        ("Hct", "HCT", "ช>39,ญ>36", hct_low, None),
        ("WBC", "WBC (cumm)", "4-10k", 4000, 10000),
        ("Plt", "Plt (/mm)", "150-500k", 150000, 500000),
        ("Neu", "Ne (%)", "43-70", 43, 70),
        ("Lym", "Ly (%)", "20-44", 20, 44)
    ]
    cbc_rows = [[(l, False), flag(get_float(k, person_data), low, high), (n, False)] for l, k, n, low, high in cbc_data]

    chem_data = [
        ("FBS", "FBS", "74-106", 74, 106),
        ("Chol", "CHOL", "<200", None, 200),
        ("Trig", "TGL", "<150", None, 150),
        ("HDL", "HDL", ">40", 40, None, True),
        ("LDL", "LDL", "<130", None, 130),
        ("Uric", "Uric Acid", "<7.2", None, 7.2),
        ("Cr", "Cr", "0.5-1.17", 0.5, 1.17),
        ("GFR", "GFR", ">60", 60, None, True),
        ("SGOT", "SGOT", "<37", None, 37),
        ("SGPT", "SGPT", "<41", None, 41)
    ]
    chem_rows = [[(l, False), flag(get_float(k, person_data), low, high, hib if 'hib' in locals() else False), (n, False)] for l, k, n, low, high, *hib in chem_data]

    # --- แปลผล Urine (ย่อ) ---
    urine_items = [
        ("Sugar", person_data.get("sugar", "-"), "Neg"),
        ("Protein", person_data.get("Alb", "-"), "Neg"),
        ("RBC", person_data.get("RBC1", "-"), "0-2"),
        ("WBC", person_data.get("WBC1", "-"), "0-5")
    ]
    urine_rows = [[(l, False), (v, is_urine_abnormal(l, v, n)), (n, False)] for l, v, n in urine_items]
    
    # --- แปลผล Special (CXR, EKG, etc) ---
    cxr = interpret_cxr(person_data.get(f"CXR{str(year)[-2:]}", person_data.get("CXR")))[0]
    ekg = interpret_ekg(person_data.get(f"EKG{str(year)[-2:]}", person_data.get("EKG")))[0]
    
    # --- แปลผล Performance (แบบย่อสุดๆ เพื่อประหยัดที่) ---
    # Vision
    vision_sum, color_sum, _ = interpret_vision(person_data.get('สรุปเหมาะสมกับงาน', ''), person_data.get('Color_Blind', ''))
    vision_text = f"การมองเห็น: {vision_sum} | ตาบอดสี: {color_sum}"
    
    # Hearing
    hear_res = interpret_audiogram(person_data, all_history_df)
    hear_text = f"ขวา: {hear_res['summary']['right']} | ซ้าย: {hear_res['summary']['left']}"
    
    # Lung
    lung_sum, _, lung_raw = interpret_lung_capacity(person_data)
    lung_text = f"ผล: {lung_sum} (FVC: {lung_raw.get('FVC %', '-')}%, FEV1: {lung_raw.get('FEV1 %', '-')}%)"

    # --- Recommendations ---
    cbc_res = generate_cbc_recommendations(person_data, sex)
    urine_res = generate_urine_recommendations(person_data, sex)
    doc_opinion = generate_doctor_opinion(person_data, sex, cbc_res, urine_res)
    
    rec_list = generate_fixed_recommendations(person_data)
    rec_html = "<ul>" + "".join([f"<li>{r}</li>" for r in rec_list]) + "</ul>" if rec_list else "ดูแลสุขภาพตามปกติ"

    # ==========================
    # HTML CONSTRUCTION
    # ==========================
    return f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานสุขภาพ (Single Page) - {person_data.get('ชื่อ-สกุล')}</title>
        {get_single_page_style()}
    </head>
    <body>
        <div class="page-container" id="main-container">
            <!-- Header -->
            <div class="header-row">
                <div class="hospital-info">
                    <h1>คลินิกตรวจสุขภาพ โรงพยาบาลสันทราย</h1>
                    <p>กลุ่มงานอาชีวเวชกรรม โทร. 053-xxx-xxx</p>
                </div>
                <div class="patient-info">
                    <h2>{person_data.get('ชื่อ-สกุล', '-')}</h2>
                    <p>HN: {person_data.get('HN', '-')} | อายุ: {int(get_float('อายุ', person_data) or 0)} ปี | เพศ: {sex}</p>
                    <p>หน่วยงาน: {person_data.get('หน่วยงาน', '-')} | วันที่: {person_data.get('วันที่ตรวจ', '-')}</p>
                </div>
            </div>

            <!-- Vitals -->
            {render_vitals_strip(person_data)}

            <!-- Lab Results (2 Cols) -->
            <div class="grid-2-col">
                <div>
                    {render_lab_table_compact("ความสมบูรณ์ของเลือด (CBC)", ["รายการ", "ผล", "ปกติ"], cbc_rows)}
                    {render_lab_table_compact("ปัสสาวะ (Urine)", ["รายการ", "ผล", "ปกติ"], urine_rows)}
                </div>
                <div>
                    {render_lab_table_compact("เคมีคลินิก (Blood Chemistry)", ["รายการ", "ผล", "ปกติ"], chem_rows)}
                </div>
            </div>

            <!-- Special Tests (3 Cols) -->
            <div class="section-box">
                 <div class="section-title">การตรวจพิเศษ & สมรรถภาพ (Special & Performance Tests)</div>
                 <div class="grid-3-col" style="font-size: 10px; border: 1px solid #ddd; padding: 5px;">
                    <div>
                        <b>เอกซเรย์ (CXR):</b> {cxr}<br>
                        <b>คลื่นหัวใจ (EKG):</b> {ekg}
                    </div>
                    <div>
                        <b>การมองเห็น:</b> {vision_text}<br>
                        <b>การได้ยิน:</b> {hear_text}
                    </div>
                    <div>
                        <b>ปอด:</b> {lung_text}<br>
                        <b>อุจจาระ:</b> {interpret_stool_exam(person_data.get('Stool exam'))}
                    </div>
                 </div>
            </div>

            <!-- Conclusion & Recs -->
            <div class="section-box" style="flex-grow: 1; display: flex; flex-direction: column;">
                <div class="section-title">สรุปผลและคำแนะนำแพทย์ (Doctor's Opinion & Recommendations)</div>
                <div class="recommendation-box">
                    <div style="font-weight: bold; margin-bottom: 2px;">ความเห็นแพทย์:</div>
                    <div style="margin-bottom: 5px; color: #000;">{doc_opinion}</div>
                    
                    <div style="font-weight: bold; margin-bottom: 2px; border-top: 1px dashed #ccc; padding-top: 4px;">คำแนะนำการปฏิบัติตัว:</div>
                    <div style="margin-bottom: 0;">{rec_html}</div>
                </div>
            </div>

            <!-- Footer Signature -->
            <div class="footer-sig">
                <div style="display: inline-block; text-align: center; width: 200px;">
                    <div style="border-bottom: 1px dotted #000; height: 30px;"></div>
                    <div>นายแพทย์นพรัตน์ รัชฎาพร</div>
                    <div>แพทย์อาชีวเวชศาสตร์ (ว.26674)</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
