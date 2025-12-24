import pandas as pd
from datetime import datetime
import html

# --- Helper Functions ---

def is_empty(val):
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def get_float(col, person_data):
    try:
        val = person_data.get(col, "")
        if is_empty(val): return None
        return float(str(val).replace(",", "").strip())
    except: return None

def flag(val, low=None, high=None, higher_is_better=False, text_ref=None):
    """
    ตรวจสอบค่าผิดปกติ
    - val: ค่าที่วัดได้
    - low, high: ช่วงปกติ (ตัวเลข)
    - text_ref: ช่วงปกติ (ข้อความ) สำหรับแสดงผล
    """
    try:
        val_float = float(str(val).replace(",", "").strip())
    except: 
        # กรณีไม่ใช่ตัวเลข
        v_str = str(val).strip()
        return (v_str if v_str else "-"), False
    
    formatted_val = f"{int(val_float):,}" if val_float == int(val_float) else f"{val_float:,.1f}"
    is_abn = False
    
    if higher_is_better:
        if low is not None and val_float < low: is_abn = True
    else:
        if low is not None and val_float < low: is_abn = True
        if high is not None and val_float > high: is_abn = True
        
    return formatted_val, is_abn

def safe_value(val):
    v = str(val or "").strip()
    return "-" if v.lower() in ["", "nan", "none", "-"] else v

def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้ตรวจ"
    if any(k in val.lower() for k in ["ปกติ", "normal", "unremarkable", "clear"]):
        return val
    return f"<span style='color:red;font-weight:bold;'>{val}</span>"

# --- CSS: A4 Portrait Compact Layout ---
def get_compact_css():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
        
        @page { 
            size: A4 portrait; 
            margin: 1cm; /* ขอบกระดาษพอประมาณไม่ชิดเกินไป */
        }
        
        body { 
            font-family: 'Sarabun', sans-serif; 
            font-size: 10px; /* ขนาดตัวอักษรมาตรฐานอ่านง่าย */
            line-height: 1.2; 
            color: #222; 
            background: white;
            margin: 0;
            padding: 0;
        }

        /* --- Layout Structure --- */
        .container { width: 100%; }
        
        .row {
            display: flex;
            width: 100%;
            gap: 15px; /* ช่องว่างระหว่างคอลัมน์ซ้ายขวา */
        }
        
        .col-left { width: 48%; }
        .col-right { width: 52%; } /* ฝั่งขวา (ผลเลือด) มักใช้ที่เยอะกว่านิดหน่อย */
        
        /* --- Header Section --- */
        .header-section {
            border-bottom: 2px solid #004D40;
            padding-bottom: 5px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }
        .hospital-name { font-size: 16px; font-weight: bold; color: #004D40; }
        .report-title { font-size: 12px; color: #555; }
        .patient-info { text-align: right; font-size: 11px; }
        .patient-name { font-size: 14px; font-weight: bold; color: #000; }

        /* --- Vitals Strip --- */
        .vitals-strip {
            background-color: #E0F2F1;
            border: 1px solid #B2DFDB;
            border-radius: 4px;
            padding: 4px 8px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            font-weight: 600;
            font-size: 10px;
        }
        
        /* --- Content Blocks --- */
        .block { margin-bottom: 10px; }
        .block-title {
            background-color: #00695C;
            color: white;
            padding: 3px 6px;
            font-weight: bold;
            font-size: 10.5px;
            border-radius: 4px 4px 0 0;
        }
        
        .table-container {
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 4px 4px;
            padding: 2px;
        }

        /* --- Tables --- */
        table { width: 100%; border-collapse: collapse; font-size: 9.5px; }
        th { 
            background-color: #f5f5f5; 
            text-align: left; 
            padding: 2px 4px; 
            border-bottom: 1px solid #ccc;
            color: #444;
            font-weight: 600;
        }
        td { 
            padding: 2px 4px; 
            border-bottom: 1px solid #eee; 
            vertical-align: top;
        }
        tr:last-child td { border-bottom: none; }
        
        .col-test { width: 45%; }
        .col-res { width: 25%; text-align: center; font-weight: 600; }
        .col-norm { width: 30%; color: #666; font-size: 9px; text-align: center;}
        
        .val-abn { color: #D32F2F; } /* สีแดงสำหรับค่าผิดปกติ */

        /* --- Special Box (CXR, EKG) --- */
        .special-row {
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid #eee;
            padding: 3px 0;
        }
        .special-label { font-weight: 600; width: 30%; }
        .special-val { width: 70%; }

        /* --- Footer / Recommendation --- */
        .rec-section {
            border: 1px solid #FFECB3;
            background-color: #FFF8E1;
            border-radius: 4px;
            padding: 8px;
            margin-top: 5px;
            font-size: 10px;
        }
        .rec-head { font-weight: bold; color: #F57F17; margin-bottom: 4px; text-decoration: underline; }
        
        .signature-section {
            margin-top: 15px;
            text-align: right;
            padding-right: 20px;
        }
        .sig-line {
            display: inline-block;
            text-align: center;
        }
    </style>
    """

# --- Rendering Logic ---

def render_table_rows(config, p, sex):
    rows = ""
    for label, col, norm, low, high, *opt in config:
        val = get_float(col, p)
        val_str, is_abn = flag(val, low, high, opt[0] if opt else False)
        
        # Override format if needed
        if val is None: val_str = safe_value(p.get(col)) # Fallback to string if not float
        
        cls = "val-abn" if is_abn else ""
        rows += f"""
        <tr>
            <td class="col-test">{label}</td>
            <td class="col-res {cls}">{val_str}</td>
            <td class="col-norm">{norm}</td>
        </tr>
        """
    return rows

def generate_compact_body(p, history_df=None):
    sex = p.get("เพศ", "ชาย")
    
    # --- 1. Header Info ---
    name = p.get('ชื่อ-สกุล', '-')
    hn = str(p.get('HN', '-')).replace('.0', '')
    age = str(int(float(p.get('อายุ')))) if str(p.get('อายุ')).replace('.', '', 1).isdigit() else '-'
    date = p.get("วันที่ตรวจ", "-")
    dept = p.get('หน่วยงาน', '-')
    
    # Vitals
    w = p.get('น้ำหนัก', '-')
    h = p.get('ส่วนสูง', '-')
    bmi = "-"
    try:
        w_f = float(w)
        h_f = float(h)
        bmi = f"{w_f / ((h_f/100)**2):.1f}"
    except: pass
    
    bp = f"{int(get_float('SBP', p) or 0)}/{int(get_float('DBP', p) or 0)}"
    if bp == "0/0": bp = "-"
    pulse = str(p.get('pulse', '-')).replace('.0', '')
    waist = str(p.get('รอบเอว', '-')).replace('.0', '')

    header_html = f"""
    <div class="header-section">
        <div>
            <div class="hospital-name">รายงานผลการตรวจสุขภาพ (Health Checkup Report)</div>
            <div class="report-title">คลินิกตรวจสุขภาพ โรงพยาบาลสันทราย | วันที่: {date}</div>
        </div>
        <div class="patient-info">
            <div class="patient-name">{name}</div>
            <div>HN: {hn} | เพศ: {sex} | อายุ: {age} ปี</div>
            <div>แผนก/หน่วยงาน: {dept}</div>
        </div>
    </div>
    
    <div class="vitals-strip">
        <span>ความดันโลหิต (BP): {bp} mmHg</span>
        <span>ชีพจร (PR): {pulse} bpm</span>
        <span>น้ำหนัก: {w} kg</span>
        <span>ส่วนสูง: {h} cm</span>
        <span>BMI: {bmi}</span>
        <span>รอบเอว: {waist} cm</span>
    </div>
    """
    
    # --- 2. Left Column Content ---
    
    # 2.1 CBC
    hb_low = 12 if sex == "หญิง" else 13
    hct_low = 36 if sex == "หญิง" else 39
    cbc_cfg = [
        ("Hemoglobin (Hb)", "Hb(%)", f">{hb_low}", hb_low, None),
        ("Hematocrit (Hct)", "HCT", f">{hct_low}", hct_low, None),
        ("WBC Count", "WBC (cumm)", "4,000-10,000", 4000, 10000),
        ("Neutrophil", "Ne (%)", "40-75", 40, 75),
        ("Lymphocyte", "Ly (%)", "20-50", 20, 50),
        ("Platelet Count", "Plt (/mm)", "140,000-450,000", 140000, 450000)
    ]
    cbc_rows = render_table_rows(cbc_cfg, p, sex)
    
    # 2.2 Urine (Updated to include more fields)
    urine_rows = ""
    urine_list = [
        ("Color", "Color", "Yellow"),
        ("Transparency", "Transparency", "Clear"),
        ("pH", "pH", "4.6-8.0"),
        ("Sp. Gr.", "Spgr", "1.005-1.030"),
        ("Protein/Alb", "Alb", "Negative"),
        ("Sugar", "sugar", "Negative"),
        ("RBC", "RBC1", "0-2"),
        ("WBC", "WBC1", "0-5"),
        ("Epithelial", "Epi", "-"),
        ("Bacteria", "Bacteria", "-")
    ]
    for lbl, key, norm in urine_list:
        val = safe_value(p.get(key))
        is_abn = False
        # Logic check for highlight
        if key in ["Alb", "sugar"] and val.lower() not in ["negative", "neg", "-", ""]: is_abn = True
        cls = "val-abn" if is_abn else ""
        urine_rows += f"<tr><td>{lbl}</td><td class='col-res {cls}'>{val}</td><td class='col-norm'>{norm}</td></tr>"

    # 2.3 Stool
    stool_rows = ""
    stool_val = safe_value(p.get("Stool exam"))
    ob_val = safe_value(p.get("Occult blood"))
    stool_rows += f"<tr><td>Stool Exam</td><td colspan='2'>{stool_val}</td></tr>"
    if ob_val != "-":
        stool_rows += f"<tr><td>Occult Blood</td><td colspan='2'>{ob_val}</td></tr>"
    
    # --- 3. Right Column Content ---
    
    # 3.1 Chemistry
    chem_cfg = [
        ("FBS (น้ำตาลในเลือด)", "FBS", "70-100", 70, 100),
        ("Cholesterol (ไขมันรวม)", "CHOL", "< 200", None, 200),
        ("Triglyceride (ไตรกลีฯ)", "TGL", "< 150", None, 150),
        ("HDL-C (ไขมันดี)", "HDL", "> 40", 40, None, True),
        ("LDL-C (ไขมันไม่ดี)", "LDL", "< 130", None, 130),
        ("Creatinine (ค่าไต)", "Cr", "0.6-1.2", 0.6, 1.2),
        ("eGFR (การทำงานไต)", "GFR", "> 60", 60, None, True),
        ("Uric Acid (กรดยูริก)", "Uric Acid", "ชาย<7.0 หญิง<6.0", None, 7.0 if sex=="ชาย" else 6.0),
        ("SGOT (ค่าตับ)", "SGOT", "0-40", 0, 40),
        ("SGPT (ค่าตับ)", "SGPT", "0-41", 0, 41),
        ("Alkaline Phos.", "ALP", "35-105", 35, 105)
    ]
    chem_rows = render_table_rows(chem_cfg, p, sex)
    
    # 3.2 Special Tests
    cxr = interpret_cxr(p.get(f"CXR{str(p.get('Year'))[-2:]}" if p.get('Year') else "CXR"))
    ekg = p.get(f"EKG{str(p.get('Year'))[-2:]}" if p.get('Year') else "EKG") or "-"
    hbsag = safe_value(p.get("HbsAg", p.get("HbsAg67")))
    hbsab = safe_value(p.get("HbsAb", p.get("HbsAb67")))
    
    # --- 4. Recommendations ---
    recs = []
    doc_suggest = str(p.get("DOCTER suggest", "")).strip()
    
    # Auto logic
    fbs = get_float("FBS", p)
    if fbs and fbs > 100: recs.append("- ควบคุมอาหารหวาน/แป้ง ออกกำลังกายสม่ำเสมอ")
    chol = get_float("CHOL", p)
    if chol and chol > 200: recs.append("- ควบคุมอาหารมัน/ของทอด/กะทิ")
    bp_s = get_float("SBP", p)
    if bp_s and bp_s > 140: recs.append("- ควบคุมอาหารเค็ม วัดความดันสม่ำเสมอ")
    
    # Merge with manual suggestion
    if doc_suggest and doc_suggest not in ["-", ""]:
        # แยกบรรทัดถ้ามีหลายคำแนะนำ
        lines = doc_suggest.split('\n')
        for l in lines:
            if l.strip(): recs.append(f"- {l.strip()}")
            
    if not recs: recs.append("- สุขภาพโดยรวมอยู่ในเกณฑ์ปกติ ควรตรวจสุขภาพประจำปีอย่างต่อเนื่อง")
    
    rec_html = "<br>".join(recs)

    # --- Construct Full HTML Body ---
    return f"""
    {header_html}
    
    <div class="row">
        <!-- Left Column -->
        <div class="col-left">
            <!-- CBC -->
            <div class="block">
                <div class="block-title">ความสมบูรณ์ของเม็ดเลือด (CBC)</div>
                <div class="table-container">
                    <table>
                        <tr><th>รายการตรวจ</th><th>ผลตรวจ</th><th>ค่าปกติ</th></tr>
                        {cbc_rows}
                    </table>
                </div>
            </div>
            
            <!-- Urine -->
            <div class="block">
                <div class="block-title">ปัสสาวะ (Urine Analysis)</div>
                <div class="table-container">
                    <table>
                        <tr><th>รายการตรวจ</th><th>ผลตรวจ</th><th>ค่าปกติ</th></tr>
                        {urine_rows}
                    </table>
                </div>
            </div>
            
            <!-- Stool -->
            <div class="block">
                <div class="block-title">อุจจาระ (Stool Examination)</div>
                <div class="table-container">
                    <table>
                        {stool_rows}
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Right Column -->
        <div class="col-right">
            <!-- Chemistry -->
            <div class="block">
                <div class="block-title">เคมีคลินิก (Blood Chemistry)</div>
                <div class="table-container">
                    <table>
                        <tr><th>รายการตรวจ</th><th>ผลตรวจ</th><th>ค่าปกติ</th></tr>
                        {chem_rows}
                    </table>
                </div>
            </div>
            
            <!-- Special Tests -->
            <div class="block">
                <div class="block-title">การตรวจพิเศษ (Special Tests)</div>
                <div class="table-container" style="padding: 8px;">
                    <div class="special-row">
                        <span class="special-label">Chest X-Ray:</span>
                        <span class="special-val">{cxr}</span>
                    </div>
                    <div class="special-row">
                        <span class="special-label">EKG:</span>
                        <span class="special-val">{ekg}</span>
                    </div>
                    <div class="special-row">
                        <span class="special-label">ไวรัสตับอักเสบ B:</span>
                        <span class="special-val">
                            Ag: {hbsag} / Ab: {hbsab}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Footer Section: Recommendation & Signature -->
    <div class="rec-section">
        <div class="rec-head">สรุปผลการตรวจและคำแนะนำแพทย์ (Conclusion & Recommendation)</div>
        <div>{rec_html}</div>
    </div>
    
    <div class="signature-section">
        <div class="sig-line">
            <br><br>
            ...........................................................<br>
            (นพ.นพรัตน์ รัชฎาพร)<br>
            แพทย์อาชีวเวชศาสตร์ (ว.26674)<br>
            ผู้ตรวจรายงาน
        </div>
    </div>
    """

def generate_compact_report(person_data, history_df=None):
    css = get_compact_css()
    body = generate_compact_body(person_data, history_df)
    return f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Health Report</title>
        {css}
    </head>
    <body>
        <div class="container">
            {body}
        </div>
    </body>
    </html>"""
