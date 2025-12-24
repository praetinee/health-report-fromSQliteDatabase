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

# --- CSS Design 2.0 (Dashboard Style) ---
def get_single_page_style():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
        
        @page {
            size: A4;
            margin: 8mm 8mm; /* ขอบกระดาษพอประมาณ ไม่ชิดเกินไป */
        }
        
        body {
            font-family: 'Sarabun', sans-serif;
            font-size: 12px; /* ขยายขนาดตัวอักษรพื้นฐาน */
            line-height: 1.3;
            color: #222;
            background: #fff;
            margin: 0;
            padding: 0;
            width: 210mm; /* A4 Width */
            box-sizing: border-box;
        }

        .container {
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        /* --- Header --- */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3px solid #00695c;
            padding-bottom: 8px;
            margin-bottom: 5px;
        }
        .header-left h1 { margin: 0; font-size: 20px; color: #00695c; line-height: 1.1; }
        .header-left p { margin: 2px 0 0 0; font-size: 12px; color: #555; }
        .header-right { text-align: right; }
        .header-right h2 { margin: 0; font-size: 18px; font-weight: bold; }
        .patient-meta { font-size: 12px; margin-top: 2px; }
        .patient-badge { 
            display: inline-block; background: #eee; padding: 2px 6px; 
            border-radius: 4px; font-weight: bold; margin-left: 5px;
        }

        /* --- Vitals --- */
        .vitals-bar {
            display: flex;
            justify-content: space-between;
            background-color: #f4f8f7;
            border-radius: 6px;
            padding: 8px 15px;
            border: 1px solid #daece8;
        }
        .vital-box { text-align: center; }
        .vital-label { font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
        .vital-value { font-size: 14px; font-weight: bold; color: #004d40; }
        .vital-unit { font-size: 10px; color: #888; font-weight: normal; }

        /* --- Lab Grid (3 Columns) --- */
        .lab-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr; /* แบ่ง 3 ส่วนเท่ากัน */
            gap: 12px;
            align-items: start;
        }
        .lab-col { display: flex; flex-direction: column; gap: 8px; }

        .card {
            border: 1px solid #ccc;
            border-radius: 6px;
            overflow: hidden;
        }
        .card-header {
            background-color: #00695c;
            color: #fff;
            padding: 4px 8px;
            font-size: 12px;
            font-weight: bold;
        }
        .card-body { padding: 0; }

        /* Table Styles */
        table { width: 100%; border-collapse: collapse; font-size: 11px; }
        th { background-color: #e0f2f1; padding: 3px 5px; text-align: left; font-weight: 600; color: #004d40; border-bottom: 1px solid #b2dfdb; }
        td { padding: 3px 5px; border-bottom: 1px solid #eee; vertical-align: middle; }
        tr:last-child td { border-bottom: none; }
        
        .result-val { font-weight: bold; text-align: center; }
        .result-norm { color: #666; font-size: 10px; text-align: center; }
        .abnormal { color: #d32f2f; }
        .bg-abnormal { background-color: #ffebee; }

        /* --- Special Tests Grid (2x3) --- */
        .special-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .special-item {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 6px 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #fff;
        }
        .sp-label { font-weight: bold; color: #333; font-size: 11px; }
        .sp-value { font-weight: bold; font-size: 12px; }
        .sp-abnormal { color: #d32f2f; }
        .sp-normal { color: #2e7d32; }
        
        /* --- Conclusion Area --- */
        .footer-section {
            display: flex;
            gap: 15px;
            border: 1px solid #ccc;
            border-radius: 6px;
            padding: 10px;
            background-color: #fafafa;
            flex-grow: 1; /* ยืดเต็มพื้นที่ที่เหลือ */
        }
        .doctor-opinion { flex: 1; border-right: 1px dashed #ccc; padding-right: 10px; }
        .recommendations { flex: 1.2; padding-left: 5px; }
        
        .footer-title { 
            font-size: 13px; font-weight: bold; color: #00695c; 
            margin-bottom: 5px; text-decoration: underline; text-decoration-color: #80cbc4;
        }
        .footer-text { font-size: 12px; }
        ul { margin: 0; padding-left: 20px; }
        li { margin-bottom: 2px; }

        /* --- Signature --- */
        .signature-row {
            display: flex;
            justify-content: flex-end;
            margin-top: 10px;
        }
        .signature-box { text-align: center; }
        .sig-line { border-bottom: 1px dotted #999; width: 200px; height: 30px; margin-bottom: 5px; }
        .sig-name { font-weight: bold; font-size: 12px; }
        .sig-role { font-size: 11px; color: #555; }

        /* Print Scale Fix */
        @media print {
            body { -webkit-print-color-adjust: exact; }
        }
    </style>
    <script>
        // Auto-Scale Logic: ย่อลงเล็กน้อยถ้าเนื้อหาล้น A4 จริงๆ
        window.onload = function() {
            const container = document.getElementById('report-container');
            const pageHeight = 1122; // A4 Height @ 96dpi (approx)
            // เช็คความสูงเนื้อหา
            if (container.scrollHeight > pageHeight) {
                const scale = pageHeight / container.scrollHeight;
                // ย่อไม่ต่ำกว่า 90% (เพราะเราจัด Layout ดีแล้ว ไม่ควรล้นมาก)
                const finalScale = Math.max(scale, 0.90); 
                container.style.transform = `scale(${finalScale})`;
                container.style.transformOrigin = 'top left';
                container.style.width = `${100/finalScale}%`;
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
        <div class="vital-box"><div class="vital-label">น้ำหนัก (Weight)</div><div class="vital-value">{get_v('น้ำหนัก', 'kg')}</div></div>
        <div class="vital-box"><div class="vital-label">ส่วนสูง (Height)</div><div class="vital-value">{get_v('ส่วนสูง', 'cm')}</div></div>
        <div class="vital-box"><div class="vital-label">ดัชนีมวลกาย (BMI)</div><div class="vital-value">{bmi:.1f} <span class="vital-unit">kg/m²</span></div></div>
        <div class="vital-box"><div class="vital-label">รอบเอว (Waist)</div><div class="vital-value">{person.get('รอบเอว', '-') or '-'} <span class="vital-unit">cm</span></div></div>
        <div class="vital-box"><div class="vital-label">ความดัน (BP)</div><div class="vital-value">{bp} <span class="vital-unit">mmHg</span></div></div>
        <div class="vital-box"><div class="vital-label">ชีพจร (Pulse)</div><div class="vital-value">{get_v('pulse', 'bpm')}</div></div>
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
        # row: [(text, is_abn), (text, is_abn), ...]
        is_row_abn = any(item[1] for item in row)
        tr_class = "bg-abnormal" if is_row_abn else ""
        html += f"<tr class='{tr_class}'>"
        for i, (text, is_abn) in enumerate(row):
            td_class = "abnormal" if is_abn else ""
            align = 'center' if i > 0 else 'left'
            # คอลัมน์แรก (ชื่อรายการ) ชิดซ้าย, ผลตรวจกึ่งกลาง
            html += f"<td style='text-align:{align};' class='{td_class}'>{text}</td>"
        html += "</tr>"
    html += "</tbody></table></div></div>"
    return html

def render_special_item(label, value, is_abn=False):
    val_class = "sp-abnormal" if is_abn else "sp-normal"
    # ถ้าค่าเป็น "ปกติ" ให้สีเขียว ถ้าอย่างอื่นสีแดง
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
    # --- Prepare Data ---
    sex = person_data.get("เพศ", "ชาย")
    year = person_data.get("Year", datetime.now().year + 543)
    
    # 1. CBC Data
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_data = [
        ("Hb", "Hb(%)", "ช>13,ญ>12", hb_low, None),
        ("Hct", "HCT", "ช>39,ญ>36", hct_low, None),
        ("WBC", "WBC", "4k-10k", 4000, 10000),
        ("Plt", "Plt", "150k-500k", 150000, 500000)
    ]
    # Format: [ (Name, False), (Value, IsAbn), (Norm, False) ]
    cbc_rows = [[(l, False), flag(get_float(k, person_data), low, high), (n, False)] for l, k, n, low, high in cbc_data]

    # 2. Chemistry Data (แยกกลุ่มเพื่อความสวยงาม)
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
        ("Cr", "Cr", "0.5-1.17", 0.5, 1.17),
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
    # ย่อผล stool เพื่อประหยัดที่
    stool_short = "ปกติ" if "ปกติ" in stool_exam else ("ผิดปกติ" if "พบ" in stool_exam else "-")
    urine_rows.append([("Stool", False), (stool_short, stool_short=="ผิดปกติ"), ("Normal", False)])

    # 4. Special Tests Data
    cxr_val, _ = interpret_cxr(person_data.get(f"CXR{str(year)[-2:]}", person_data.get("CXR")))
    ekg_val, _ = interpret_ekg(person_data.get(f"EKG{str(year)[-2:]}", person_data.get("EKG")))
    
    vision_s, color_s, _ = interpret_vision(person_data.get('สรุปเหมาะสมกับงาน', ''), person_data.get('Color_Blind', ''))
    
    hear_res = interpret_audiogram(person_data, all_history_df)
    hear_short = f"R:{hear_res['summary']['right']} L:{hear_res['summary']['left']}"
    
    lung_s, _, lung_raw = interpret_lung_capacity(person_data)
    lung_short = lung_s.replace("สมรรถภาพปอด", "").strip()

    # --- Recommendations Logic ---
    cbc_rec = generate_cbc_recommendations(person_data, sex)
    urine_rec = generate_urine_recommendations(person_data, sex)
    doc_op = generate_doctor_opinion(person_data, sex, cbc_rec, urine_rec)
    rec_list = generate_fixed_recommendations(person_data)
    rec_html = "<ul>" + "".join([f"<li>{r}</li>" for r in rec_list]) + "</ul>" if rec_list else "<ul><li>ดูแลสุขภาพตามปกติ พักผ่อนให้เพียงพอ</li></ul>"

    return f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลสุขภาพ (Dashboard) - {person_data.get('ชื่อ-สกุล')}</title>
        {get_single_page_style()}
    </head>
    <body>
        <div class="container" id="report-container">
            <!-- Header -->
            <div class="header">
                <div class="header-left">
                    <h1>รายงานผลการตรวจสุขภาพ</h1>
                    <p>คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม โรงพยาบาลสันทราย</p>
                </div>
                <div class="header-right">
                    <h2>{person_data.get('ชื่อ-สกุล', '-')}</h2>
                    <div class="patient-meta">
                        HN: <b>{person_data.get('HN', '-')}</b> | 
                        อายุ: <b>{int(get_float('อายุ', person_data) or 0)} ปี</b>
                        <span class="patient-badge">{person_data.get('หน่วยงาน', 'ไม่ระบุ')}</span>
                    </div>
                    <div style="font-size: 11px; color: #777; margin-top: 2px;">วันที่ตรวจ: {person_data.get('วันที่ตรวจ', '-')}</div>
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
                        <div class="card-body" style="padding: 5px;">
                            {render_special_item("สายตา", vision_s)}
                            <div style="height:4px;"></div>
                            {render_special_item("ตาบอดสี", color_s)}
                            <div style="height:4px;"></div>
                            {render_special_item("การได้ยิน", hear_short)}
                        </div>
                    </div>
                </div>
                <div class="lab-col">
                    {render_table("การทำงานไต & ตับ (Kidney/Liver)", ["รายการ", "ผล", "ปกติ"], chem_rows_2)}
                    
                    <!-- Special Tests Box 2 -->
                    <div class="card">
                        <div class="card-header">เอกซเรย์ & อื่นๆ</div>
                        <div class="card-body" style="padding: 5px;">
                            {render_special_item("CXR (ปอด)", cxr_val)}
                            <div style="height:4px;"></div>
                            {render_special_item("EKG (หัวใจ)", ekg_val)}
                            <div style="height:4px;"></div>
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
