import pandas as pd
import html
import json
from datetime import datetime
import numpy as np

# --- Import Logic การแปลผล ---
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

# --- CSS Design: Professional Medical Report (High Contrast) ---
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
            font-size: 12px;
            line-height: 1.3;
            color: #000; /* เปลี่ยนเป็นสีดำสนิทเพื่อความคมชัด */
            background: #fff;
            margin: 0;
            padding: 10mm;
            width: 210mm;
            height: 296mm;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            -webkit-print-color-adjust: exact; /* บังคับพิมพ์สีพื้นหลัง */
            print-color-adjust: exact;
        }

        .report-container {
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
        }

        /* --- Header: Clean & Bold --- */
        .header-section {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            border-bottom: 3px solid #004d40; /* เส้นเขียวเข้มหนา */
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        .header-left h1 {
            margin: 0;
            font-size: 24px;
            color: #004d40;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .header-left p {
            margin: 2px 0 0 0;
            font-size: 14px;
            color: #333;
            font-weight: 500;
        }
        .header-right { text-align: right; }
        .patient-name {
            font-size: 20px;
            font-weight: 700;
            color: #000;
            margin: 0;
        }
        .patient-info-row {
            font-size: 13px;
            margin-top: 4px;
            color: #333;
        }
        .info-pill {
            display: inline-block;
            background: #eee;
            border: 1px solid #ccc;
            padding: 1px 6px;
            border-radius: 4px;
            font-weight: 600;
            margin-left: 5px;
        }

        /* --- Vitals Grid --- */
        .vitals-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 10px;
            background-color: #f1f8e9; /* พื้นหลังเขียวอ่อน */
            border: 1px solid #8bc34a;
            border-radius: 6px;
            padding: 10px;
            margin-bottom: 15px;
        }
        .vital-box {
            text-align: center;
            border-right: 1px solid #c5e1a5;
        }
        .vital-box:last-child { border-right: none; }
        .vital-title { font-size: 10px; font-weight: 700; color: #558b2f; text-transform: uppercase; }
        .vital-data { font-size: 16px; font-weight: 700; color: #000; margin-top: 2px; }
        .vital-u { font-size: 10px; font-weight: 400; color: #555; }

        /* --- Layout Grid --- */
        .main-content {
            display: flex;
            gap: 15px;
            flex-grow: 1;
        }
        .col-left { width: 50%; display: flex; flex-direction: column; gap: 15px; }
        .col-right { width: 50%; display: flex; flex-direction: column; gap: 15px; }

        /* --- Table Styling (High Contrast) --- */
        .result-group {
            border: 1px solid #000; /* เส้นขอบดำบาง */
            border-radius: 0;
            overflow: hidden;
        }
        .group-head {
            background-color: #004d40;
            color: #fff;
            padding: 6px 10px;
            font-size: 13px;
            font-weight: 700;
            text-transform: uppercase;
            border-bottom: 1px solid #000;
        }
        .res-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
        }
        .res-table th {
            background-color: #cfd8dc; /* เทาเข้มขึ้น */
            color: #000;
            font-weight: 700;
            text-align: left;
            padding: 4px 8px;
            border-bottom: 1px solid #999;
        }
        .res-table td {
            padding: 3px 8px;
            border-bottom: 1px solid #ddd;
            vertical-align: middle;
            color: #000;
        }
        /* Zebra Striping */
        .res-table tr:nth-child(even) { background-color: #f5f5f5; }
        .res-table tr:last-child td { border-bottom: none; }

        /* Values Coloring */
        .v-norm { color: #2e7d32; }
        .v-abn { color: #d50000; font-weight: 800; } /* แดงเข้มและตัวหนา */
        .v-plain { color: #000; }

        /* --- Footer (Fixed Height for consistence) --- */
        .footer-wrap {
            margin-top: auto;
            border: 1px solid #000;
            display: flex;
            height: 120px;
        }
        .f-block {
            flex: 1;
            padding: 8px;
            border-right: 1px solid #000;
            display: flex;
            flex-direction: column;
        }
        .f-block:last-child { border-right: none; flex: 1.2; }
        .f-head {
            font-size: 12px; font-weight: 700; text-decoration: underline; margin-bottom: 5px; color: #000;
        }
        .f-body {
            font-size: 11px; line-height: 1.3; overflow: hidden;
        }
        .f-body ul { margin: 0; padding-left: 15px; }

        /* --- Signature --- */
        .signature-section {
            display: flex;
            justify-content: flex-end;
            margin-top: 10px;
        }
        .sig-block {
            text-align: center;
            width: 220px;
        }
        .sig-line {
            border-bottom: 1px solid #000;
            height: 30px;
            margin-bottom: 5px;
        }
        .sig-name { font-weight: 700; font-size: 13px; }
        .sig-pos { font-size: 12px; color: #444; }

    </style>
    """

def render_vitals_grid(person):
    def g(k, u=""):
        v = get_float(k, person)
        return f"{v} <span class='vital-u'>{u}</span>" if v else "-"
    
    sbp, dbp = get_float("SBP", person), get_float("DBP", person)
    bp = f"{int(sbp)}/{int(dbp)}" if sbp and dbp else "-"
    
    w, h = get_float("น้ำหนัก", person), get_float("ส่วนสูง", person)
    bmi = w / ((h/100)**2) if w and h else 0
    
    return f"""
    <div class="vitals-grid">
        <div class="vital-box"><div class="vital-title">Weight</div><div class="vital-data">{g('น้ำหนัก', 'kg')}</div></div>
        <div class="vital-box"><div class="vital-title">Height</div><div class="vital-data">{g('ส่วนสูง', 'cm')}</div></div>
        <div class="vital-box"><div class="vital-title">BMI</div><div class="vital-data">{bmi:.1f} <span class="vital-u">kg/m²</span></div></div>
        <div class="vital-box"><div class="vital-title">Waist</div><div class="vital-data">{person.get('รอบเอว', '-') or '-'} <span class="vital-u">cm</span></div></div>
        <div class="vital-box"><div class="vital-title">BP</div><div class="vital-data">{bp} <span class="vital-u">mmHg</span></div></div>
        <div class="vital-box"><div class="vital-title">Pulse</div><div class="vital-data">{g('pulse', 'bpm')}</div></div>
    </div>
    """

def render_table_group(title, headers, rows):
    html = f"""
    <div class="result-group">
        <div class="group-head">{title}</div>
        <table class="res-table">
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
        label_t, val_t, norm_t = row
        label = label_t[0]
        val = val_t[0]
        is_abn = val_t[1]
        norm = norm_t[0]
        
        css = "v-abn" if is_abn else "v-plain"
        
        html += f"""
        <tr>
            <td>{label}</td>
            <td style="text-align: center;" class="{css}">{val}</td>
            <td style="text-align: center;">{norm}</td>
        </tr>
        """
    html += "</tbody></table></div>"
    return html

def render_special_group(title, items):
    html = f"""
    <div class="result-group">
        <div class="group-head">{title}</div>
        <table class="res-table">
    """
    for label, val, is_abn in items:
        css = "v-abn" if is_abn else "v-norm"
        if val in ["-", "N/A", "ไม่ได้ตรวจ"]: css = "v-plain"
        
        html += f"""
        <tr>
            <td style="width: 40%; font-weight: 600;">{label}</td>
            <td style="width: 60%; text-align: right;" class="{css}">{val}</td>
        </tr>
        """
    html += "</table></div>"
    return html

def generate_single_page_report(person_data, all_history_df=None):
    # --- Data Prep ---
    sex = person_data.get("เพศ", "ชาย")
    year = person_data.get("Year", datetime.now().year + 543)
    
    # 1. CBC
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_rows = [
        [("Hemoglobin",0), flag(get_float("Hb(%)", person_data), hb_low, None), (f">{hb_low}",0)],
        [("Hematocrit",0), flag(get_float("HCT", person_data), hct_low, None), (f">{hct_low}",0)],
        [("WBC Count",0), flag(get_float("WBC (cumm)", person_data), 4000, 10000), ("4k-10k",0)],
        [("Platelet",0), flag(get_float("Plt (/mm)", person_data), 150000, 500000), ("1.5-5แสน",0)],
        [("Neutrophil %",0), flag(get_float("Ne (%)", person_data), 43, 70), ("43-70",0)],
        [("Lymphocyte %",0), flag(get_float("Ly (%)", person_data), 20, 44), ("20-44",0)],
    ]

    # 2. Urine/Stool
    urine_items = [
        ("Urine Sugar", "sugar", "Neg"),
        ("Urine Protein", "Alb", "Neg"),
        ("RBC", "RBC1", "0-2"),
        ("WBC", "WBC1", "0-5")
    ]
    u_rows = [[(l,0), (person_data.get(k,"-"), is_urine_abnormal(l, person_data.get(k), n)), (n,0)] for l,k,n in urine_items]
    
    stool_val = interpret_stool_exam(person_data.get("Stool exam", ""))
    stool_s = "Normal" if "ปกติ" in stool_val else ("Abnormal" if "พบ" in stool_val else "-")
    u_rows.append([("Stool Exam",0), (stool_s, stool_s=="Abnormal"), ("Normal",0)])

    # 3. Metabolic
    meta_rows = [
        [("FBS (Sugar)",0), flag(get_float("FBS", person_data), 74, 106), ("74-106",0)],
        [("Cholesterol",0), flag(get_float("CHOL", person_data), None, 200), ("<200",0)],
        [("Triglyceride",0), flag(get_float("TGL", person_data), None, 150), ("<150",0)],
        [("HDL (Good)",0), flag(get_float("HDL", person_data), 40, None, True), (">40",0)],
        [("LDL (Bad)",0), flag(get_float("LDL", person_data), None, 130), ("<130",0)],
    ]

    # 4. Organ
    organ_rows = [
        [("Uric Acid",0), flag(get_float("Uric Acid", person_data), None, 7.2), ("<7.2",0)],
        [("Creatinine",0), flag(get_float("Cr", person_data), 0.5, 1.17), ("0.5-1.2",0)],
        [("eGFR",0), flag(get_float("GFR", person_data), 60, None, True), (">60",0)],
        [("SGOT",0), flag(get_float("SGOT", person_data), None, 37), ("<37",0)],
        [("SGPT",0), flag(get_float("SGPT", person_data), None, 41), ("<41",0)],
    ]

    # 5. Special
    cxr = interpret_cxr(person_data.get(f"CXR{str(year)[-2:]}", person_data.get("CXR"))).split('⚠️')[0].strip()
    ekg = interpret_ekg(person_data.get(f"EKG{str(year)[-2:]}", person_data.get("EKG"))).split('⚠️')[0].strip()
    vis, col, _ = interpret_vision(person_data.get('สรุปเหมาะสมกับงาน',''), person_data.get('Color_Blind',''))
    hear = f"R:{interpret_audiogram(person_data, all_history_df)['summary']['right']}"
    lung, _, _ = interpret_lung_capacity(person_data)
    lung = lung.replace("สมรรถภาพปอด","").strip() or "-"

    sp_items = [
        ("Chest X-Ray", cxr, "ผิดปกติ" in cxr),
        ("EKG", ekg, "ผิดปกติ" in ekg),
        ("Vision", vis, "ผิดปกติ" in vis),
        ("Color Blind", col, "ผิดปกติ" in col),
        ("Hearing", hear, "ผิดปกติ" in hear),
        ("Lung Function", lung, "ผิดปกติ" in lung),
    ]

    # Recommendations
    rec_list = generate_fixed_recommendations(person_data)
    rec_html = "<ul>" + "".join([f"<li>{r}</li>" for r in rec_list]) + "</ul>" if rec_list else "<ul><li>ดูแลสุขภาพตามปกติ</li></ul>"
    
    cbc_rec = generate_cbc_recommendations(person_data, sex)
    urine_rec = generate_urine_recommendations(person_data, sex)
    op = generate_doctor_opinion(person_data, sex, cbc_rec, urine_rec)
    if is_empty(op) or op == "-": op = "สุขภาพโดยรวมปกติ"

    return f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>Health Report {person_data.get('HN')}</title>
        {get_single_page_style()}
    </head>
    <body>
        <div class="report-container">
            <div class="header-section">
                <div class="header-left">
                    <h1>MEDICAL REPORT</h1>
                    <p>รายงานผลการตรวจสุขภาพประจำปี {year}</p>
                </div>
                <div class="header-right">
                    <div class="patient-name">{person_data.get('ชื่อ-สกุล', '-')}</div>
                    <div class="patient-info-row">
                        HN: <b>{person_data.get('HN', '-')}</b> 
                        <span class="info-pill">{int(get_float('อายุ', person_data) or 0)} ปี</span>
                        <span class="info-pill">{person_data.get('หน่วยงาน', '-')}</span>
                    </div>
                </div>
            </div>

            {render_vitals_grid(person_data)}

            <div class="main-content">
                <div class="col-left">
                    {render_table_group("HEMATOLOGY", ["TEST", "RESULT", "NORMAL"], cbc_rows)}
                    {render_table_group("URINALYSIS & STOOL", ["TEST", "RESULT", "NORMAL"], u_rows)}
                    {render_special_group("SPECIAL TESTS", sp_items)}
                </div>
                <div class="col-right">
                    {render_table_group("METABOLIC PROFILE", ["TEST", "RESULT", "NORMAL"], meta_rows)}
                    {render_table_group("KIDNEY & LIVER", ["TEST", "RESULT", "NORMAL"], organ_rows)}
                    
                    <div class="footer-wrap" style="height: auto; flex-grow: 1; flex-direction: column; border: none;">
                         <div class="f-block" style="border: 1px solid #000; border-bottom: none; flex: 1;">
                            <div class="f-head">DOCTOR'S OPINION</div>
                            <div class="f-body">{op}</div>
                        </div>
                        <div class="f-block" style="border: 1px solid #000; flex: 1;">
                            <div class="f-head">RECOMMENDATIONS</div>
                            <div class="f-body">{rec_html}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="signature-section">
                <div class="sig-block">
                    <div class="sig-line"></div>
                    <div class="sig-name">นายแพทย์นพรัตน์ รัชฎาพร</div>
                    <div class="sig-pos">แพทย์อาชีวเวชศาสตร์ (ว.26674)</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
