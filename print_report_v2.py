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

# --- CSS Design: Modern Professional Medical Report ---
def get_single_page_style():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');
        
        @page {
            size: A4;
            margin: 0; 
        }
        
        body {
            font-family: 'Sarabun', sans-serif;
            font-size: 13px; /* ปรับขนาดฟอนต์ให้พอดีหน้า */
            line-height: 1.3;
            color: #2c3e50;
            background: #fff;
            margin: 0;
            padding: 10mm; /* ขอบกระดาษ */
            width: 210mm;
            height: 297mm; /* ความสูง A4 */
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
        }

        .report-container {
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
        }

        /* --- Header --- */
        .header-section {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #00695c; /* Medical Teal */
            padding-bottom: 12px;
            margin-bottom: 12px;
        }
        .header-left h1 {
            margin: 0;
            font-size: 22px;
            color: #00695c;
            font-weight: 700;
            text-transform: uppercase;
        }
        .header-left p {
            margin: 2px 0 0 0;
            font-size: 14px;
            color: #546e7a;
        }
        .header-right {
            text-align: right;
        }
        .header-right .patient-name {
            font-size: 18px;
            font-weight: 700;
            color: #000;
            margin: 0;
        }
        .header-right .patient-meta {
            font-size: 13px;
            color: #444;
            margin-top: 4px;
        }
        .meta-box {
            display: inline-block;
            background: #e0f2f1;
            color: #00695c;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
            margin-left: 5px;
        }

        /* --- Vitals Section --- */
        .vitals-section {
            display: flex;
            background-color: #f8f9fa;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 8px 0;
            margin-bottom: 15px;
        }
        .vital-item {
            flex: 1;
            text-align: center;
            border-right: 1px solid #e0e0e0;
        }
        .vital-item:last-child { border-right: none; }
        .vital-label {
            font-size: 11px;
            color: #78909c;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 2px;
        }
        .vital-value {
            font-size: 16px;
            font-weight: 700;
            color: #004d40;
        }
        .vital-unit {
            font-size: 11px;
            font-weight: 400;
            color: #90a4ae;
            margin-left: 2px;
        }

        /* --- Main Content Grid (2 Columns) --- */
        .content-grid {
            display: flex;
            gap: 20px;
            flex-grow: 1; /* ขยายให้เต็มพื้นที่ที่เหลือ */
        }
        .column-left { flex: 1; display: flex; flex-direction: column; gap: 15px; }
        .column-right { flex: 1; display: flex; flex-direction: column; gap: 15px; }

        /* --- Table Styling --- */
        .table-card {
            border: 1px solid #cfd8dc;
            border-radius: 4px;
            overflow: hidden;
            background: #fff;
        }
        .table-header {
            background-color: #00695c;
            color: #fff;
            padding: 6px 10px;
            font-size: 13px;
            font-weight: 700;
            text-transform: uppercase;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }
        .data-table th {
            background-color: #f5f5f5;
            color: #555;
            font-weight: 600;
            text-align: left;
            padding: 5px 8px;
            border-bottom: 1px solid #eee;
        }
        .data-table td {
            padding: 4px 8px;
            border-bottom: 1px solid #f0f0f0;
            vertical-align: middle;
        }
        .data-table tr:last-child td { border-bottom: none; }
        .data-table tr:nth-child(even) { background-color: #fafafa; } /* Zebra Striping */

        /* --- Status Colors --- */
        .val-normal { color: #2e7d32; } /* Green */
        .val-abnormal { color: #c62828; font-weight: 700; } /* Red Bold */
        .val-text { color: #333; }

        /* --- Special Tests List --- */
        .special-list {
            list-style: none;
            margin: 0;
            padding: 0;
        }
        .special-item {
            display: flex;
            justify-content: space-between;
            padding: 6px 10px;
            border-bottom: 1px solid #f0f0f0;
            font-size: 12px;
        }
        .special-item:last-child { border-bottom: none; }
        .sp-label { font-weight: 600; color: #455a64; }
        .sp-value { font-weight: 500; text-align: right; }

        /* --- Footer Section --- */
        .footer-section {
            margin-top: auto; /* ดันลงล่างสุด */
            border-top: 2px solid #00695c;
            padding-top: 15px;
            display: flex;
            gap: 20px;
        }
        .footer-box {
            flex: 1;
            background-color: #fbfbfb;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 10px;
            position: relative;
        }
        .footer-title {
            font-size: 12px;
            font-weight: 700;
            color: #00695c;
            text-transform: uppercase;
            margin-bottom: 5px;
            border-bottom: 1px dashed #ccc;
            padding-bottom: 3px;
        }
        .footer-content {
            font-size: 12px;
            color: #333;
            line-height: 1.4;
        }
        .footer-content ul { margin: 0; padding-left: 18px; }

        /* --- Signature --- */
        .signature-area {
            width: 200px;
            text-align: center;
            margin-left: auto; /* ชิดขวา */
            margin-top: 10px;
        }
        .sig-line {
            border-bottom: 1px dotted #999;
            margin-bottom: 5px;
            height: 30px;
        }
        .sig-text { font-size: 12px; color: #555; }
        .sig-bold { font-weight: 700; color: #000; font-size: 13px; }

        @media print {
            body { -webkit-print-color-adjust: exact; padding: 0; margin: 0; }
            .report-container { width: 100%; height: 100%; padding: 10mm; box-sizing: border-box; }
        }
    </style>
    
    <script>
        // Auto-scale to fit A4 if content overflows slightly
        window.onload = function() {
            var content = document.querySelector('.report-container');
            if (content.scrollHeight > 1123) { // A4 height in px at 96dpi approx
                var scale = 1123 / content.scrollHeight;
                // content.style.transform = "scale(" + (scale * 0.98) + ")";
                // content.style.transformOrigin = "top center";
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
    <div class="vitals-section">
        <div class="vital-item">
            <div class="vital-label">น้ำหนัก (Weight)</div>
            <div class="vital-value">{get_v('น้ำหนัก', 'kg')}</div>
        </div>
        <div class="vital-item">
            <div class="vital-label">ส่วนสูง (Height)</div>
            <div class="vital-value">{get_v('ส่วนสูง', 'cm')}</div>
        </div>
        <div class="vital-item">
            <div class="vital-label">ดัชนีมวลกาย (BMI)</div>
            <div class="vital-value">{bmi:.1f} <span class="vital-unit">kg/m²</span></div>
        </div>
        <div class="vital-item">
            <div class="vital-label">รอบเอว (Waist)</div>
            <div class="vital-value">{person.get('รอบเอว', '-') or '-'} <span class="vital-unit">cm</span></div>
        </div>
        <div class="vital-item">
            <div class="vital-label">ความดันโลหิต (BP)</div>
            <div class="vital-value">{bp} <span class="vital-unit">mmHg</span></div>
        </div>
        <div class="vital-item">
            <div class="vital-label">ชีพจร (Pulse)</div>
            <div class="vital-value">{get_v('pulse', 'bpm')}</div>
        </div>
    </div>
    """

def render_data_table(title, headers, rows):
    html = f"""
    <div class="table-card">
        <div class="table-header">{title}</div>
        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 45%;">{headers[0]}</th>
                    <th style="width: 30%; text-align: center;">{headers[1]}</th>
                    <th style="width: 25%; text-align: center;">{headers[2]}</th>
                </tr>
            </thead>
            <tbody>
    """
    for row in rows:
        label_tuple, val_tuple, norm_tuple = row
        
        # label_tuple = (Text, unused_bool)
        # val_tuple = (ValueText, IsAbnormal)
        # norm_tuple = (NormalRange, unused_bool)

        label = label_tuple[0]
        val_text = val_tuple[0]
        is_abn = val_tuple[1]
        norm = norm_tuple[0]

        val_class = "val-abnormal" if is_abn else "val-text"
        
        html += f"""
        <tr>
            <td>{label}</td>
            <td style="text-align: center;" class="{val_class}">{val_text}</td>
            <td style="text-align: center; color: #777;">{norm}</td>
        </tr>
        """
    html += "</tbody></table></div>"
    return html

def render_special_card(title, items):
    html = f"""
    <div class="table-card">
        <div class="table-header">{title}</div>
        <div class="special-list">
    """
    for label, val, is_abn in items:
        val_class = "val-abnormal" if is_abn else "val-normal"
        if val in ["-", "", "ไม่ได้ตรวจ", "N/A"]: val_class = "val-text"
        
        html += f"""
        <div class="special-item">
            <span class="sp-label">{label}</span>
            <span class="sp-value {val_class}">{val}</span>
        </div>
        """
    html += "</div></div>"
    return html

def generate_single_page_report(person_data, all_history_df=None):
    # --- Prepare Data ---
    sex = person_data.get("เพศ", "ชาย")
    year = person_data.get("Year", datetime.now().year + 543)
    
    # 1. CBC
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_def = [
        ("Hemoglobin", "Hb(%)", ">13,>12", hb_low, None),
        ("Hematocrit", "HCT", ">39,>36", hct_low, None),
        ("WBC Count", "WBC (cumm)", "4k-10k", 4000, 10000),
        ("Platelet", "Plt (/mm)", "1.5-5แสน", 150000, 500000),
        ("Neutrophil", "Ne (%)", "43-70", 43, 70),
        ("Lymphocyte", "Ly (%)", "20-44", 20, 44)
    ]
    # Format: [(Label, False), (Value, IsAbn), (Norm, False)]
    cbc_rows = [[(l, False), flag(get_float(k, person_data), low, high), (n, False)] for l, k, n, low, high in cbc_def]

    # 2. Urine
    urine_items = [
        ("Sugar", person_data.get("sugar", "-"), "Neg"),
        ("Protein", person_data.get("Alb", "-"), "Neg"),
        ("RBC", person_data.get("RBC1", "-"), "0-2"),
        ("WBC", person_data.get("WBC1", "-"), "0-5")
    ]
    urine_rows = [[(l, False), (v, is_urine_abnormal(l, v, n)), (n, False)] for l, v, n in urine_items]
    
    # 3. Stool
    stool_exam = interpret_stool_exam(person_data.get("Stool exam", ""))
    stool_short = "ปกติ" if "ปกติ" in stool_exam else ("ผิดปกติ" if "พบ" in stool_exam else "-")
    is_stool_abn = stool_short == "ผิดปกติ"
    urine_rows.append([("Stool Exam", False), (stool_short, is_stool_abn), ("Normal", False)])

    # 4. Metabolic (Sugar/Lipid)
    metabolic_def = [
        ("FBS (Sugar)", "FBS", "74-106", 74, 106),
        ("Cholesterol", "CHOL", "<200", None, 200),
        ("Triglyceride", "TGL", "<150", None, 150),
        ("HDL (Good)", "HDL", ">40", 40, None, True),
        ("LDL (Bad)", "LDL", "<130", None, 130)
    ]
    meta_rows = [[(l, False), flag(get_float(k, person_data), low, high, hib if 'hib' in locals() else False), (n, False)] for l, k, n, low, high, *hib in metabolic_def]

    # 5. Kidney & Liver
    organ_def = [
        ("Uric Acid", "Uric Acid", "<7.2", None, 7.2),
        ("Creatinine", "Cr", "0.5-1.2", 0.5, 1.17),
        ("eGFR", "GFR", ">60", 60, None, True),
        ("SGOT (Liver)", "SGOT", "<37", None, 37),
        ("SGPT (Liver)", "SGPT", "<41", None, 41)
    ]
    organ_rows = [[(l, False), flag(get_float(k, person_data), low, high, hib if 'hib' in locals() else False), (n, False)] for l, k, n, low, high, *hib in organ_def]

    # 6. Special Tests Data
    cxr_val, _ = interpret_cxr(person_data.get(f"CXR{str(year)[-2:]}", person_data.get("CXR")))
    cxr_val = cxr_val.split('⚠️')[0].strip()
    is_cxr_abn = "ผิดปกติ" in cxr_val or "Abnormal" in cxr_val

    ekg_val, _ = interpret_ekg(person_data.get(f"EKG{str(year)[-2:]}", person_data.get("EKG")))
    ekg_val = ekg_val.split('⚠️')[0].strip()
    is_ekg_abn = "ผิดปกติ" in ekg_val or "Abnormal" in ekg_val

    vision_s, color_s, _ = interpret_vision(person_data.get('สรุปเหมาะสมกับงาน', ''), person_data.get('Color_Blind', ''))
    is_vis_abn = "ผิดปกติ" in vision_s
    is_col_abn = "ผิดปกติ" in color_s

    hear_res = interpret_audiogram(person_data, all_history_df)
    hear_short = f"R:{hear_res['summary']['right']} L:{hear_res['summary']['left']}"
    is_hear_abn = "ผิดปกติ" in hear_short or "เสื่อม" in hear_short

    lung_s, _, _ = interpret_lung_capacity(person_data)
    lung_short = lung_s.replace("สมรรถภาพปอด", "").strip()
    if not lung_short: lung_short = "-"
    is_lung_abn = "ผิดปกติ" in lung_short

    special_items = [
        ("Chest X-Ray", cxr_val, is_cxr_abn),
        ("EKG (Heart)", ekg_val, is_ekg_abn),
        ("Vision", vision_s, is_vis_abn),
        ("Color Blind", color_s, is_col_abn),
        ("Hearing", hear_short, is_hear_abn),
        ("Lung Func.", lung_short, is_lung_abn)
    ]

    # --- Recommendations Logic ---
    cbc_rec = generate_cbc_recommendations(person_data, sex)
    urine_rec = generate_urine_recommendations(person_data, sex)
    doc_op = generate_doctor_opinion(person_data, sex, cbc_rec, urine_rec)
    if is_empty(doc_op) or doc_op == "-": doc_op = "สุขภาพโดยรวมแข็งแรงสมบูรณ์ดี"

    rec_list = generate_fixed_recommendations(person_data)
    rec_html = ""
    if rec_list:
        rec_html = "<ul>" + "".join([f"<li>{r}</li>" for r in rec_list]) + "</ul>"
    else:
        rec_html = "<ul><li>ควรออกกำลังกายสม่ำเสมอ พักผ่อนให้เพียงพอ และทานอาหารที่มีประโยชน์</li></ul>"

    # --- HTML Assembly ---
    return f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>Medical Health Report - {person_data.get('ชื่อ-สกุล')}</title>
        {get_single_page_style()}
    </head>
    <body>
        <div class="report-container">
            <!-- Header -->
            <div class="header-section">
                <div class="header-left">
                    <h1>Medical Health Report</h1>
                    <p>รายงานผลการตรวจสุขภาพประจำปี {year}</p>
                </div>
                <div class="header-right">
                    <div class="patient-name">{person_data.get('ชื่อ-สกุล', '-')}</div>
                    <div class="patient-meta">
                        HN: <b>{person_data.get('HN', '-')}</b> 
                        <span class="meta-box">{int(get_float('อายุ', person_data) or 0)} ปี</span>
                        <span class="meta-box">{person_data.get('หน่วยงาน', 'General')}</span>
                    </div>
                </div>
            </div>

            <!-- Vitals -->
            {render_vitals(person_data)}

            <!-- Main Content Grid -->
            <div class="content-grid">
                <!-- Left Column -->
                <div class="column-left">
                    {render_data_table("HEMATOLOGY (ความสมบูรณ์เลือด)", ["Test Name", "Result", "Normal"], cbc_rows)}
                    {render_data_table("URINALYSIS & STOOL", ["Test Name", "Result", "Normal"], urine_rows)}
                </div>

                <!-- Right Column -->
                <div class="column-right">
                    {render_data_table("METABOLIC PROFILE (น้ำตาล/ไขมัน)", ["Test Name", "Result", "Normal"], meta_rows)}
                    {render_data_table("KIDNEY & LIVER FUNCTION", ["Test Name", "Result", "Normal"], organ_rows)}
                    {render_special_card("SPECIAL EXAMINATIONS (การตรวจพิเศษ)", special_items)}
                </div>
            </div>

            <!-- Footer -->
            <div class="footer-section">
                <div class="footer-box" style="flex: 1.2;">
                    <div class="footer-title">DOCTOR'S OPINION (ความเห็นแพทย์)</div>
                    <div class="footer-content">{doc_op}</div>
                </div>
                <div class="footer-box" style="flex: 1.5;">
                    <div class="footer-title">RECOMMENDATIONS (คำแนะนำ)</div>
                    <div class="footer-content">{rec_html}</div>
                </div>
            </div>

            <!-- Signature -->
            <div class="signature-area">
                <div class="sig-line"></div>
                <div class="sig-bold">นายแพทย์นพรัตน์ รัชฎาพร</div>
                <div class="sig-text">แพทย์อาชีวเวชศาสตร์ (ว.26674)</div>
                <div class="sig-text">โรงพยาบาลสันทราย</div>
            </div>
        </div>
    </body>
    </html>
    """
