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

# --- CSS Design 10.0 (Hard Reset & Unique Classes) ---
def get_single_page_style():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
        
        @page {
            size: A4;
            margin: 0; 
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

        .v2-content-wrapper {
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 12px;
            transform-origin: top center;
        }

        /* --- Header --- */
        .v2-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            border-bottom: 4px solid #004d40 !important; /* เส้นเขียวเข้ม */
            padding-bottom: 10px;
            margin-bottom: 5px;
        }
        .v2-header-left h1 { margin: 0; font-size: 26px; color: #004d40 !important; line-height: 1.1; font-weight: 700; }
        .v2-header-left p { margin: 4px 0 0 0; font-size: 15px; color: #555; font-weight: 500; }
        .v2-header-right { text-align: right; }
        .v2-header-right h2 { margin: 0; font-size: 20px; font-weight: 700; color: #000; }
        .v2-patient-meta { font-size: 14px; margin-top: 5px; color: #444; }
        .v2-patient-badge { 
            display: inline-block; background: #f0f0f0; padding: 2px 8px; 
            border-radius: 4px; font-weight: 600; margin-left: 5px; border: 1px solid #ccc;
        }

        /* --- Vitals --- */
        .v2-vitals-bar {
            display: flex;
            justify-content: space-between;
            background-color: #fff;
            border-radius: 8px;
            padding: 10px 15px;
            border: 2px solid #004d40 !important; /* กรอบเขียวเข้ม */
            box-shadow: none;
        }
        .v2-vital-box { text-align: center; position: relative; width: 16%; }
        .v2-vital-box:not(:last-child)::after {
            content: ''; position: absolute; right: 0; top: 10%; height: 80%; width: 1px; background: #ddd;
        }
        .v2-vital-label { font-size: 12px; color: #555; font-weight: 600; text-transform: uppercase; margin-bottom: 3px; }
        .v2-vital-value { font-size: 18px; font-weight: 700; color: #004d40 !important; }
        .v2-vital-unit { font-size: 12px; color: #888; font-weight: 400; margin-left: 2px; }

        /* --- Lab Grid --- */
        .v2-lab-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 15px;
            align-items: start;
        }
        .v2-lab-col { display: flex; flex-direction: column; gap: 12px; }

        .v2-card {
            border: 2px solid #004d40 !important; /* กรอบ Card สีเขียวเข้ม */
            border-radius: 6px;
            overflow: hidden;
            box-shadow: none;
            background: #fff;
        }
        .v2-card-header {
            background-color: #004d40 !important; /* พื้นหลัง Header สีเขียวเข้ม */
            color: #fff !important; /* ตัวหนังสือขาว */
            padding: 8px 10px;
            font-size: 14px; 
            font-weight: 700;
            text-transform: uppercase;
        }
        .v2-card-body { padding: 0; background: #fff; }

        /* Table */
        .v2-table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .v2-table th { 
            background-color: #e0f2f1; 
            padding: 6px 8px; 
            text-align: left; 
            font-weight: 700; 
            color: #004d40 !important; /* หัวตารางเขียวเข้ม */
            border-bottom: 2px solid #004d40 !important; 
            font-size: 13px;
        }
        .v2-table td { 
            padding: 6px 8px; 
            border-bottom: 1px solid #eee; 
            vertical-align: middle; 
            color: #222;
        }
        .v2-table tr:last-child td { border-bottom: none; }
        .v2-table tr:nth-child(even) { background-color: #fafafa; } 
        
        .v2-abnormal { color: #d32f2f !important; font-weight: 800; } 
        .v2-bg-abnormal { background-color: #ffebee !important; } 

        /* --- Special Item --- */
        .v2-special-item {
            border-bottom: 1px solid #f0f0f0;
            padding: 8px 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #fff;
        }
        .v2-special-item:last-child { border-bottom: none; }
        .v2-sp-label { font-weight: 600; color: #444; font-size: 14px; }
        .v2-sp-value { font-weight: 600; font-size: 14px; text-align: right;}
        .v2-sp-abnormal { color: #d32f2f; }
        .v2-sp-normal { color: #2e7d32; }
        
        /* --- Footer --- */
        .v2-footer-section {
            display: flex;
            gap: 20px;
            border: 2px solid #004d40 !important; /* กรอบ Footer เขียวเข้ม */
            border-radius: 6px;
            padding: 15px;
            background-color: #fff;
            flex-grow: 1; 
        }
        .v2-doctor-opinion { flex: 1; border-right: 1px solid #eee; padding-right: 15px; }
        .v2-recommendations { flex: 1.2; padding-left: 5px; }
        
        .v2-footer-title { 
            font-size: 15px; font-weight: 700; color: #004d40 !important; 
            margin-bottom: 8px; text-transform: uppercase;
            display: flex; align-items: center; gap: 5px;
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }
        .v2-footer-title::before { content: '■'; color: #004d40; font-size: 12px; line-height: 0; }
        
        .v2-footer-text { font-size: 14px; color: #333; line-height: 1.5; margin-top: 5px; } 
        ul { margin: 0; padding-left: 20px; }
        li { margin-bottom: 4px; }

        /* --- Signature --- */
        .v2-signature-row {
            display: flex;
            justify-content: flex-end;
            margin-top: 15px;
        }
        .v2-signature-box { text-align: center; width: 250px; }
        .v2-sig-line { border-bottom: 1px dashed #aaa; width: 100%; height: 30px; margin-bottom: 6px; }
        .v2-sig-name { font-weight: 700; font-size: 15px; color: #222; }
        .v2-sig-role { font-size: 13px; color: #666; }

        @media print {
            body { -webkit-print-color-adjust: exact; padding: 0; margin: 0; }
            .v2-content-wrapper { padding: 10mm; width: 100%; box-sizing: border-box; }
        }
    </style>
    
    <script>
        window.onload = function() {
            var content = document.getElementById('v2-content');
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
        return f"{val} <span class='v2-vital-unit'>{unit}</span>" if val else "-"
    
    sbp, dbp = get_float("SBP", person), get_float("DBP", person)
    bp = f"{int(sbp)}/{int(dbp)}" if sbp and dbp else "-"
    
    w = get_float("น้ำหนัก", person)
    h = get_float("ส่วนสูง", person)
    bmi = w / ((h/100)**2) if w and h else 0
    
    return f"""
    <div class="v2-vitals-bar">
        <div class="v2-vital-box"><div class="v2-vital-label">น้ำหนัก (Weight)</div><div class="v2-vital-value">{get_v('น้ำหนัก')}</div></div>
        <div class="v2-vital-box"><div class="v2-vital-label">ส่วนสูง (Height)</div><div class="v2-vital-value">{get_v('ส่วนสูง')}</div></div>
        <div class="v2-vital-box"><div class="v2-vital-label">BMI</div><div class="v2-vital-value">{bmi:.1f}</div></div>
        <div class="v2-vital-box"><div class="v2-vital-label">รอบเอว (Waist)</div><div class="v2-vital-value">{person.get('รอบเอว', '-') or '-'} <span class="v2-vital-unit">cm</span></div></div>
        <div class="v2-vital-box"><div class="v2-vital-label">ความดัน (BP)</div><div class="v2-vital-value">{bp} <span class="v2-vital-unit">mmHg</span></div></div>
        <div class="v2-vital-box"><div class="v2-vital-label">ชีพจร (Pulse)</div><div class="v2-vital-value">{get_v('pulse')} <span class="v2-vital-unit">bpm</span></div></div>
    </div>
    """

def render_table(title, headers, rows):
    html = f"""
    <div class="v2-card">
        <div class="v2-card-header">{title}</div>
        <div class="v2-card-body">
            <table class="v2-table">
                <thead><tr>""" + "".join([f"<th>{h}</th>" for h in headers]) + """</tr></thead>
                <tbody>
    """
    for row in rows:
        is_row_abn = any(item[1] for item in row)
        tr_class = "v2-bg-abnormal" if is_row_abn else ""
        html += f"<tr class='{tr_class}'>"
        for i, (text, is_abn) in enumerate(row):
            td_class = "v2-abnormal" if is_abn else ""
            align = 'center' if i > 0 else 'left'
            html += f"<td style='text-align:{align};' class='{td_class}'>{text}</td>"
        html += "</tr>"
    html += "</tbody></table></div></div>"
    return html

def render_special_item(label, value, is_abn=False):
    val_class = "v2-sp-abnormal" if is_abn else "v2-sp-normal"
    if "ปกติ" in str(value) or "Normal" in str(value) or "ไม่พบ" in str(value):
        val_class = "v2-sp-normal"
    elif value == "-" or value == "":
        val_class = ""
    else:
        val_class = "v2-sp-abnormal"
        
    return f"""
    <div class="v2-special-item">
        <span class="v2-sp-label">{label}</span>
        <span class="v2-sp-value {val_class}">{value}</span>
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
        <title>รายงานผลสุขภาพ (Hard Reset) - {person_data.get('ชื่อ-สกุล')}</title>
        {get_single_page_style()}
    </head>
    <body>
        <div class="v2-content-wrapper" id="v2-content">
            <!-- Header -->
            <div class="v2-header">
                <div class="v2-header-left">
                    <h1>รายงานผลการตรวจสุขภาพ</h1>
                    <p>คลินิกตรวจสุขภาพ โรงพยาบาลสันทราย</p>
                </div>
                <div class="v2-header-right">
                    <h2>{person_data.get('ชื่อ-สกุล', '-')}</h2>
                    <div class="v2-patient-meta">
                        HN: <b>{person_data.get('HN', '-')}</b> | 
                        อายุ: <b>{int(get_float('อายุ', person_data) or 0)} ปี</b>
                        <span class="v2-patient-badge">{person_data.get('หน่วยงาน', 'ไม่ระบุ')}</span>
                    </div>
                    <div style="font-size: 13px; color: #666; margin-top: 5px;">วันที่ตรวจ: <b>{person_data.get('วันที่ตรวจ', '-')}</b></div>
                </div>
            </div>

            <!-- Vitals -->
            {render_vitals(person_data)}

            <!-- Lab Results Grid (3 Columns) -->
            <div class="v2-lab-grid">
                <div class="v2-lab-col">
                    {render_table("ความสมบูรณ์เลือด (CBC)", ["รายการ", "ผล", "ปกติ"], cbc_rows)}
                    {render_table("ปัสสาวะ/อุจจาระ (Urine/Stool)", ["รายการ", "ผล", "ปกติ"], urine_rows)}
                </div>
                <div class="v2-lab-col">
                    {render_table("ไขมัน & น้ำตาล (Lipid/Sugar)", ["รายการ", "ผล", "ปกติ"], chem_rows_1)}
                    
                    <!-- Special Tests Box 1 -->
                    <div class="v2-card">
                        <div class="v2-card-header">การมองเห็น & การได้ยิน</div>
                        <div class="v2-card-body">
                            {render_special_item("สายตา", vision_s)}
                            {render_special_item("ตาบอดสี", color_s)}
                            {render_special_item("การได้ยิน", hear_short)}
                        </div>
                    </div>
                </div>
                <div class="v2-lab-col">
                    {render_table("การทำงานไต & ตับ (Kidney/Liver)", ["รายการ", "ผล", "ปกติ"], chem_rows_2)}
                    
                    <!-- Special Tests Box 2 -->
                    <div class="v2-card">
                        <div class="v2-card-header">เอกซเรย์ & อื่นๆ</div>
                        <div class="v2-card-body">
                            {render_special_item("CXR (ปอด)", cxr_val)}
                            {render_special_item("EKG (หัวใจ)", ekg_val)}
                            {render_special_item("สมรรถภาพปอด", lung_short)}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Footer: Conclusion & Recommendations -->
            <div class="v2-footer-section">
                <div class="v2-doctor-opinion">
                    <div class="v2-footer-title">สรุปความเห็นแพทย์ (Doctor's Opinion)</div>
                    <div class="v2-footer-text">{doc_op}</div>
                </div>
                <div class="v2-recommendations">
                    <div class="v2-footer-title">คำแนะนำ (Recommendations)</div>
                    <div class="v2-footer-text">{rec_html}</div>
                </div>
            </div>

            <!-- Signature -->
            <div class="v2-signature-row">
                <div class="v2-signature-box">
                    <div class="v2-sig-line"></div>
                    <div class="v2-sig-name">นายแพทย์นพรัตน์ รัชฎาพร</div>
                    <div class="v2-sig-role">แพทย์อาชีวเวชศาสตร์ (ว.26674)</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
