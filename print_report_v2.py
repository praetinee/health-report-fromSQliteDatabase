import pandas as pd
import html
from datetime import datetime
import numpy as np

# --- Import Logic การแปลผล ---
try:
    from performance_tests import (
        interpret_audiogram, interpret_lung_capacity, 
        interpret_cxr, interpret_ekg, interpret_urine, 
        interpret_stool, interpret_hepatitis, interpret_vision
    )
except ImportError:
    # Fallback functions กรณี import ไม่ได้
    def interpret_cxr(v): return (v if v else "-"), False
    def interpret_ekg(v): return (v if v else "-"), False
    def interpret_vision(*args): return "-","-","-"
    def interpret_audiogram(*args): return {"summary": {"right": "-", "left": "-"}}
    def interpret_lung_capacity(*args): return "-", "-", "-"
    def interpret_urine(k, v): return False # Dummy

# --- Helper Functions ---
def is_empty(val):
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def get_float(col, person_data):
    try:
        val = person_data.get(col, "")
        if is_empty(val): return None
        return float(str(val).replace(",", "").strip())
    except: return None

def get_str(col, person_data, default="-"):
    val = person_data.get(col, default)
    if is_empty(val): return default
    return str(val).strip()

def flag_value(val, low=None, high=None, higher_is_better=False):
    """
    ตรวจสอบค่าผิดปกติ
    Returns: (formatted_value, is_abnormal)
    """
    try:
        if is_empty(val): return "-", False
        num_val = float(str(val).replace(",", "").strip())
    except:
        return str(val), False

    # Format
    if num_val == int(num_val):
        fmt_val = f"{int(num_val):,}"
    else:
        fmt_val = f"{num_val:,.1f}"

    is_abnormal = False
    if higher_is_better:
        if low is not None and num_val < low: is_abnormal = True
    else:
        if low is not None and num_val < low: is_abnormal = True
        if high is not None and num_val > high: is_abnormal = True
        
    return fmt_val, is_abnormal

def check_urine_abnormal(test_name, value, normal_text="Bg"):
    """ตรวจสอบความผิดปกติของปัสสาวะ"""
    val_str = str(value).lower().strip()
    if val_str in ["-", "", "nan", "none"]: return False
    
    if test_name == "pH":
        try: return not (4.6 <= float(value) <= 8.0)
        except: return False
    if test_name == "Sp.gr":
        try: return not (1.005 <= float(value) <= 1.030)
        except: return False
        
    # เช็คคำว่า Negative หรือ Normal
    if "neg" in normal_text.lower():
        if "neg" not in val_str and "nl" not in val_str and "normal" not in val_str: return True
    return False

# --- CSS Design ---
def get_single_page_style():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');
        
        @page { size: A4; margin: 0; }
        
        body {
            font-family: 'Sarabun', sans-serif;
            font-size: 11px;
            color: #000;
            background: #fff;
            margin: 0;
            padding: 15mm;
            width: 210mm;
            min-height: 296mm;
            box-sizing: border-box;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }

        .report-page {
            display: flex;
            flex-direction: column;
            height: 100%;
            page-break-after: always;
        }
        
        /* Header */
        .header-row { display: flex; justify-content: space-between; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 10px; }
        .h-title h1 { margin: 0; font-size: 22px; font-weight: bold; color: #1a237e; }
        .h-title p { margin: 2px 0 0 0; font-size: 12px; font-weight: normal; }
        .h-info { text-align: right; font-size: 12px; }
        .h-info b { font-size: 14px; }

        /* Vitals Bar */
        .vitals-bar {
            display: flex;
            background-color: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 8px;
            margin-bottom: 15px;
            justify-content: space-around;
        }
        .v-item { text-align: center; }
        .v-lbl { font-size: 10px; color: #666; text-transform: uppercase; font-weight: bold; }
        .v-val { font-size: 14px; font-weight: bold; color: #000; }
        .v-unit { font-size: 10px; color: #444; }

        /* Content Layout */
        .content-cols { display: flex; gap: 15px; }
        .col-1, .col-2 { flex: 1; display: flex; flex-direction: column; gap: 10px; }

        /* Tables */
        .res-box { border: 1px solid #999; border-radius: 4px; overflow: hidden; }
        .res-head {
            background-color: #e0e0e0;
            padding: 5px 8px;
            font-weight: bold;
            font-size: 12px;
            border-bottom: 1px solid #999;
            display: flex; justify-content: space-between;
        }
        table.res-tbl { width: 100%; border-collapse: collapse; font-size: 11px; }
        table.res-tbl th { background-color: #f0f0f0; padding: 4px; text-align: left; border-bottom: 1px solid #ccc; font-weight: 600; font-size: 10px; color: #444; }
        table.res-tbl td { padding: 3px 5px; border-bottom: 1px solid #eee; vertical-align: middle; }
        table.res-tbl tr:last-child td { border-bottom: none; }
        
        .val-norm { color: #2e7d32; }
        .val-abn { color: #d32f2f; font-weight: bold; }
        .val-plain { color: #000; }
        .t-right { text-align: right; }
        .t-center { text-align: center; }

        /* Footer / Opinion */
        .footer-sec {
            margin-top: auto;
            border: 2px solid #333;
            border-radius: 6px;
            padding: 10px;
            background-color: #fafafa;
            display: flex;
            gap: 15px;
        }
        .f-col { flex: 1; }
        .f-title { font-weight: bold; font-size: 13px; text-decoration: underline; margin-bottom: 5px; color: #1a237e; }
        .f-text { font-size: 12px; line-height: 1.4; }
        .f-text ul { margin: 0; padding-left: 20px; }

        .sig-row { margin-top: 20px; text-align: right; padding-right: 20px; }
        .sig-line { display: inline-block; text-align: center; }
        .sig-img { height: 40px; }
        .sig-txt { border-top: 1px solid #000; padding-top: 5px; font-size: 12px; font-weight: bold; margin-top: 5px; }

    </style>
    """

def render_table_rows(items):
    html = ""
    for label, val_tuple, norm in items:
        val_str, is_abn = val_tuple
        css_class = "val-abn" if is_abn else "val-norm"
        if val_str in ["-", ""]: css_class = "val-plain"
        
        html += f"""
        <tr>
            <td>{label}</td>
            <td class="t-center {css_class}">{val_str}</td>
            <td class="t-center" style="color:#666;">{norm}</td>
        </tr>
        """
    return html

def render_report_body(person_data, all_history_df=None):
    # --- เตรียมข้อมูล ---
    sex = person_data.get("เพศ", "ชาย")
    
    # 1. CBC
    hb_L, hb_H = (12, 16) if sex == "หญิง" else (13, 18)
    hct_L, hct_H = (36, 48) if sex == "หญิง" else (40, 54)
    
    cbc_data = [
        ("Hemoglobin", flag_value(person_data.get("Hb(%)"), hb_L, hb_H), f"{hb_L}-{hb_H}"),
        ("Hematocrit", flag_value(person_data.get("HCT"), hct_L, hct_H), f"{hct_L}-{hct_H}"),
        ("WBC Count", flag_value(person_data.get("WBC (cumm)"), 4000, 11000), "4,000-11,000"),
        ("Platelet", flag_value(person_data.get("Plt (/mm)"), 140000, 450000), "140,000-450,000"),
        ("Neutrophil", flag_value(person_data.get("Ne (%)"), 40, 75), "40-75 %"),
        ("Lymphocyte", flag_value(person_data.get("Ly (%)"), 20, 50), "20-50 %"),
        ("Eosinophil", flag_value(person_data.get("Eo (%)"), 0, 6), "0-6 %"),
        ("Monocyte", flag_value(person_data.get("Mo (%)"), 2, 10), "2-10 %"),
        ("Basophil", flag_value(person_data.get("Ba (%)"), 0, 1), "0-1 %"),
    ]

    # 2. Metabolic / Chemistry
    meta_data = [
        ("FBS (Sugar)", flag_value(person_data.get("FBS"), 70, 100), "70-100"),
        ("Cholesterol", flag_value(person_data.get("CHOL"), 0, 200), "< 200"),
        ("Triglyceride", flag_value(person_data.get("TGL"), 0, 150), "< 150"),
        ("HDL-C", flag_value(person_data.get("HDL"), 40, None, True), "> 40"),
        ("LDL-C", flag_value(person_data.get("LDL"), 0, 130), "< 130"),
    ]

    # 3. Kidney & Liver
    kl_data = [
        ("Uric Acid", flag_value(person_data.get("Uric Acid"), 2.5, 7.5), "2.5-7.5"),
        ("Creatinine", flag_value(person_data.get("Cr"), 0.5, 1.2), "0.5-1.2"),
        ("eGFR", flag_value(person_data.get("GFR"), 90, None, True), "> 90"),
        ("SGOT (AST)", flag_value(person_data.get("SGOT"), 0, 40), "0-40"),
        ("SGPT (ALT)", flag_value(person_data.get("SGPT"), 0, 41), "0-41"),
        ("Alk Phos", flag_value(person_data.get("ALP"), 30, 120), "30-120"),
    ]

    # 4. Urinalysis
    ua_raw = [
        ("Color", "Color", "Yellow"),
        ("Appearance", "Appearance", "Clear"),
        ("pH", "pH", "4.6-8.0"),
        ("Sp.Gr", "Sp.gr", "1.005-1.030"),
        ("Protein (Alb)", "Urine Alb", "Negative"),
        ("Sugar", "Urine Sugar", "Negative"),
        ("RBC", "RBC1", "0-2"),
        ("WBC", "WBC1", "0-5"),
        ("Epithelial", "Epith", "Negative"),
    ]
    ua_data = []
    for lbl, key, norm in ua_raw:
        val = get_str(key, person_data)
        is_abn = check_urine_abnormal(lbl, val, norm)
        ua_data.append((lbl, (val, is_abn), norm))

    # 5. Special Tests Interpretation
    try:
        yr = person_data.get("Year", datetime.now().year+543)
        yr_short = str(yr)[-2:]
        cxr_res, cxr_abn = interpret_cxr(person_data.get(f"CXR{yr_short}", person_data.get("CXR")))
        ekg_res, ekg_abn = interpret_ekg(person_data.get(f"EKG{yr_short}", person_data.get("EKG")))
        
        vis_res, col_res, _ = interpret_vision(person_data.get("สรุปเหมาะสมกับงาน"), person_data.get("Color_Blind"))
        vis_abn = "ผิดปกติ" in vis_res
        col_abn = "ผิดปกติ" in col_res
        
        hear_res = interpret_audiogram(person_data, all_history_df)
        hear_txt = f"R: {hear_res['summary']['right']}, L: {hear_res['summary']['left']}"
        hear_abn = "ผิดปกติ" in hear_txt

        lung_txt, _, lung_res_val = interpret_lung_capacity(person_data)
        lung_txt = lung_txt.replace("สมรรถภาพปอด","").strip()
        lung_abn = "ผิดปกติ" in lung_txt
    except:
        cxr_res, cxr_abn = "-", False
        ekg_res, ekg_abn = "-", False
        vis_res, vis_abn = "-", False
        col_res, col_abn = "-", False
        hear_txt, hear_abn = "-", False
        lung_txt, lung_abn = "-", False

    sp_data = [
        ("Chest X-Ray", (cxr_res, cxr_abn), "Normal"),
        ("EKG", (ekg_res, ekg_abn), "Normal"),
        ("Vision Acuity", (vis_res, vis_abn), "Normal"),
        ("Color Blindness", (col_res, col_abn), "Normal"),
        ("Audiogram", (hear_txt, hear_abn), "Normal"),
        ("Lung Function", (lung_txt, lung_abn), "Normal"),
    ]

    # --- Recommendations Logic (Simplified but comprehensive) ---
    rec_list = []
    
    # Sugar
    if flag_value(person_data.get("FBS"), 70, 100)[1]:
        rec_list.append("ควบคุมอาหารประเภทแป้ง น้ำตาล และของหวาน ผลไม้รสหวาน")
    
    # Fat
    chol = get_float("CHOL", person_data) or 0
    tgl = get_float("TGL", person_data) or 0
    ldl = get_float("LDL", person_data) or 0
    if chol > 200 or tgl > 150 or ldl > 130:
        rec_list.append("ควบคุมอาหารไขมันสูง หลีกเลี่ยงของทอด กะทิ เนื้อสัตว์ติดมัน")
        rec_list.append("ออกกำลังกายสม่ำเสมอ อย่างน้อย 30 นาที/วัน")

    # BP
    sbp = get_float("SBP", person_data) or 0
    if sbp > 140:
        rec_list.append("ควรวัดความดันโลหิตซ้ำ และควบคุมอาหารรสเค็ม")

    # Uric
    uric = get_float("Uric Acid", person_data) or 0
    if uric > 7.5:
        rec_list.append("งดเครื่องในสัตว์ ยอดผัก และเครื่องดื่มแอลกอฮอล์")
        
    # Liver
    sgot = get_float("SGOT", person_data) or 0
    sgpt = get_float("SGPT", person_data) or 0
    if sgot > 40 or sgpt > 41:
        rec_list.append("งดเครื่องดื่มแอลกอฮอล์ และควรตรวจติดตามค่าตับ")

    if not rec_list:
        rec_list.append("สุขภาพโดยรวมอยู่ในเกณฑ์ดี ควรตรวจสุขภาพประจำปีอย่างต่อเนื่อง")
        rec_list.append("รับประทานอาหารครบ 5 หมู่ และออกกำลังกายสม่ำเสมอ")

    rec_html = "".join([f"<li>{r}</li>" for r in rec_list])

    # Doctor Opinion
    problems = []
    bmi = 0
    w, h = get_float("น้ำหนัก", person_data), get_float("ส่วนสูง", person_data)
    if w and h:
        bmi = w / ((h/100)**2)
        if bmi > 25: problems.append("ภาวะน้ำหนักเกิน (Overweight)")
    
    if flag_value(person_data.get("FBS"), 70, 100)[1]: problems.append("ระดับน้ำตาลในเลือดสูง (High Blood Sugar)")
    if sbp > 140: problems.append("ความดันโลหิตสูง (Hypertension)")
    if chol > 200 or ldl > 130: problems.append("ไขมันในเลือดสูง (Dyslipidemia)")
    if cxr_abn: problems.append(f"X-Ray: {cxr_res}")
    
    doc_op = "สุขภาพปกติ (Normal)"
    if problems:
        doc_op = "พบความผิดปกติ (Abnormal Findings):<br>" + "<br>".join([f"- {p}" for p in problems])

    # --- HTML Assembly ---
    return f"""
    <div class="report-page">
        <div class="header-row">
            <div class="h-title">
                <h1>MEDICAL CHECK-UP REPORT</h1>
                <p>รายงานผลการตรวจสุขภาพประจำปี {person_data.get('Year', '-')}</p>
            </div>
            <div class="h-info">
                Name: <b>{person_data.get('ชื่อ-สกุล')}</b><br>
                HN: {person_data.get('HN')} | Age: {get_str('อายุ', person_data)} | Sex: {sex}<br>
                Dept: {person_data.get('หน่วยงาน', '-')}<br>
                Date: {get_str('วันที่ตรวจ', person_data)}
            </div>
        </div>

        <div class="vitals-bar">
            <div class="v-item"><div class="v-lbl">Weight</div><div class="v-val">{get_str('น้ำหนัก', person_data)}</div><div class="v-unit">kg</div></div>
            <div class="v-item"><div class="v-lbl">Height</div><div class="v-val">{get_str('ส่วนสูง', person_data)}</div><div class="v-unit">cm</div></div>
            <div class="v-item"><div class="v-lbl">BMI</div><div class="v-val">{bmi:.1f}</div><div class="v-unit">kg/m²</div></div>
            <div class="v-item"><div class="v-lbl">BP</div><div class="v-val">{get_str('SBP', person_data)}/{get_str('DBP', person_data)}</div><div class="v-unit">mmHg</div></div>
            <div class="v-item"><div class="v-lbl">Pulse</div><div class="v-val">{get_str('Pulse', person_data)}</div><div class="v-unit">bpm</div></div>
            <div class="v-item"><div class="v-lbl">Waist</div><div class="v-val">{get_str('รอบเอว', person_data)}</div><div class="v-unit">cm</div></div>
        </div>

        <div class="content-cols">
            <div class="col-1">
                <div class="res-box">
                    <div class="res-head">HEMATOLOGY</div>
                    <table class="res-tbl">
                        <tr><th width="40%">Test Name</th><th width="30%" class="t-center">Result</th><th width="30%" class="t-center">Normal Range</th></tr>
                        {render_table_rows(cbc_data)}
                    </table>
                </div>
                
                <div class="res-box">
                    <div class="res-head">URINALYSIS</div>
                    <table class="res-tbl">
                        <tr><th width="40%">Test Name</th><th width="30%" class="t-center">Result</th><th width="30%" class="t-center">Normal Range</th></tr>
                        {render_table_rows(ua_data)}
                    </table>
                </div>
                
                <div class="res-box">
                    <div class="res-head">SPECIAL EXAMINATIONS</div>
                    <table class="res-tbl">
                        <tr><th width="40%">Test Name</th><th width="60%" class="t-center">Result</th></tr>
                        {render_table_rows([(l,v,"") for l,v,n in sp_data])}
                    </table>
                </div>
            </div>

            <div class="col-2">
                <div class="res-box">
                    <div class="res-head">BLOOD CHEMISTRY</div>
                    <table class="res-tbl">
                        <tr><th width="40%">Test Name</th><th width="30%" class="t-center">Result</th><th width="30%" class="t-center">Normal Range</th></tr>
                        {render_table_rows(meta_data)}
                        {render_table_rows(kl_data)}
                    </table>
                </div>

                <div class="footer-sec">
                    <div class="f-col">
                        <div class="f-title">DOCTOR'S OPINION</div>
                        <div class="f-text">{doc_op}</div>
                    </div>
                    <div class="f-col">
                        <div class="f-title">RECOMMENDATIONS</div>
                        <div class="f-text"><ul>{rec_html}</ul></div>
                    </div>
                </div>

                <div class="sig-row">
                    <div class="sig-line">
                        <div class="sig-txt">
                            ( นายแพทย์นพรัตน์ รัชฎาพร )<br>
                            แพทย์ผู้ตรวจ (License No. 26674)
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

def generate_single_page_report(person_data, all_history_df=None):
    """ฟังก์ชันหลักที่ Admin Panel เรียกใช้"""
    style = get_single_page_style()
    body = render_report_body(person_data, all_history_df)
    
    return f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>Health Report {person_data.get('HN')}</title>
        {style}
    </head>
    <body>
        {body}
    </body>
    </html>
    """
