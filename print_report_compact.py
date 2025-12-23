import pandas as pd
from datetime import datetime
import html

# --- Helper Functions & Constants ---

RECOMMENDATION_TEXTS_CBC = {
    "C2": "รับประทานอาหารที่มีประโยชน์ (นม, ผักใบเขียว, ตับ, เนื้อสัตว์) พักผ่อนให้เพียงพอ หากมีอาการหน้ามืดให้พบแพทย์",
    "C4": "ดูแลสุขภาพ ออกกำลังกาย ระวังการเกิดแผลเนื่องจากเลือดอาจหยุดยาก",
    "C6": "รักษาสุขภาพให้แข็งแรง เลี่ยงแหล่งชุมชนแออัด รักษาต่อเนื่อง",
    "C8": "พบแพทย์หาสาเหตุภาวะโลหิตจาง หรือรักษาต่อเนื่อง",
    "C9": "พบแพทย์หาสาเหตุภาวะโลหิตจาง และดูแลสุขภาพ",
    "C10": "พบแพทย์หาสาเหตุเกล็ดเลือดสูง",
    "C13": "รับประทานอาหารที่มีธาตุเหล็ก พักผ่อนให้เพียงพอ",
}

def is_empty(val):
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def get_float(col, person_data):
    try:
        val = person_data.get(col, "")
        if is_empty(val): return None
        return float(str(val).replace(",", "").strip())
    except: return None

def flag(val, low=None, high=None, higher_is_better=False):
    try:
        val_float = float(str(val).replace(",", "").strip())
    except: return "-", False
    
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
    if any(k in val.lower() for k in ["ผิดปกติ", "abnormal", "infiltrate", "lesion"]):
        return f"<span style='color:red;font-weight:bold;'>{val}</span>"
    return val

def interpret_ekg(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้ตรวจ"
    if any(k in val.lower() for k in ["ผิดปกติ", "abnormal", "arrhythmia"]):
        return f"<span style='color:red;font-weight:bold;'>{val}</span>"
    return val

# --- Compact CSS (ออกแบบเพื่อให้อยู่ในหน้าเดียว) ---
def get_compact_css():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
        @page { 
            size: A4; 
            margin: 0.5cm; 
        }
        body { 
            font-family: 'Sarabun', sans-serif; 
            font-size: 9px; 
            line-height: 1.1; 
            color: #333; 
            background: white;
        }
        .container {
            width: 100%;
        }
        
        /* Header Compact */
        .header-bar {
            border-bottom: 2px solid #00796B;
            padding-bottom: 4px;
            margin-bottom: 6px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }
        .h-title { font-size: 14px; font-weight: bold; color: #00796B; margin: 0; }
        .h-sub { font-size: 10px; color: #555; margin: 0; }
        .h-info { font-size: 11px; font-weight: 600; text-align: right; }
        .h-info span { margin-left: 8px; }

        /* Vitals Bar */
        .vitals-bar {
            background-color: #f0f4f4;
            border-radius: 4px;
            padding: 3px 6px;
            margin-bottom: 6px;
            font-size: 9px;
            display: flex;
            justify-content: space-between;
            border: 1px solid #e0e0e0;
        }
        .vital-item b { color: #004D40; }

        /* 3-Column Layout */
        .grid-layout {
            display: flex;
            gap: 8px; /* Gap between columns */
            align-items: flex-start;
        }
        .col-3 {
            flex: 1;
            min-width: 0; /* Prevent overflow */
            display: flex;
            flex-direction: column;
            gap: 6px; /* Gap between boxes in column */
        }

        /* Content Box */
        .box {
            border: 1px solid #ccc;
            border-radius: 4px;
            overflow: hidden;
        }
        .box-head {
            background-color: #00796B;
            color: white;
            padding: 2px 5px;
            font-size: 9.5px;
            font-weight: bold;
        }
        .box-body {
            padding: 0;
        }

        /* Tables */
        table { width: 100%; border-collapse: collapse; font-size: 8.5px; }
        th { background-color: #f2f2f2; font-weight: 600; padding: 2px 4px; text-align: left; border-bottom: 1px solid #ddd; }
        td { padding: 1px 4px; border-bottom: 1px solid #eee; vertical-align: top; }
        tr:last-child td { border-bottom: none; }
        
        .val-abn { color: #d32f2f; font-weight: bold; }
        .t-center { text-align: center; }
        .t-right { text-align: right; }
        
        /* Recommendation Box */
        .rec-box {
            background-color: #fff8e1;
            border: 1px solid #ffe082;
            border-radius: 4px;
            padding: 5px;
            font-size: 9px;
            margin-top: auto; /* Push to bottom if flex */
        }
        .rec-title { font-weight: bold; color: #f57f17; margin-bottom: 2px; font-size: 9.5px; }
        .rec-list { margin: 0; padding-left: 12px; }
        .rec-list li { margin-bottom: 1px; }

        /* Signature */
        .signature {
            margin-top: 8px;
            text-align: center;
            border-top: 1px dotted #999;
            padding-top: 4px;
            width: 80%;
            margin-left: auto;
            margin-right: auto;
        }
        
        @media print {
            body { -webkit-print-color-adjust: exact; }
            .box { break-inside: avoid; }
        }
    </style>
    """

# --- Rendering Logic ---

def render_compact_header(p):
    name = p.get('ชื่อ-สกุล', '-')
    age = str(int(float(p.get('อายุ')))) if str(p.get('อายุ')).replace('.', '', 1).isdigit() else '-'
    hn = str(p.get('HN', '-')).replace('.0', '')
    date = p.get("วันที่ตรวจ", "-")
    dept = p.get('หน่วยงาน', '-')
    
    # Vitals
    w = get_float('น้ำหนัก', p)
    h = get_float('ส่วนสูง', p)
    bmi = w / ((h/100)**2) if w and h else None
    waist = p.get('รอบเอว', '-')
    sbp, dbp = get_float("SBP", p), get_float("DBP", p)
    bp = f"{int(sbp)}/{int(dbp)}" if sbp and dbp else "-"
    pulse = f"{int(get_float('pulse', p))}" if get_float('pulse', p) else "-"

    return f"""
    <div class="header-bar">
        <div>
            <h1 class="h-title">รายงานผลการตรวจสุขภาพ (Health Checkup Report)</h1>
            <p class="h-sub">คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม โรงพยาบาลสันทราย (วันที่ตรวจ: {date})</p>
        </div>
        <div class="h-info">
            <span style="font-size:13px;">{name}</span><br>
            <span>HN: {hn}</span>
            <span>อายุ: {age} ปี</span>
            <span>แผนก: {dept}</span>
        </div>
    </div>
    <div class="vitals-bar">
        <span class="vital-item"><b>BP:</b> {bp} mmHg</span>
        <span class="vital-item"><b>PR:</b> {pulse} bpm</span>
        <span class="vital-item"><b>Weight:</b> {w or '-'} kg</span>
        <span class="vital-item"><b>Height:</b> {h or '-'} cm</span>
        <span class="vital-item"><b>BMI:</b> {f'{bmi:.1f}' if bmi else '-'}</span>
        <span class="vital-item"><b>Waist:</b> {waist} cm</span>
    </div>
    """

def render_table_rows(config, p, sex):
    rows = ""
    abnormal_found = False
    for label, col, norm, low, high, *opt in config:
        val = get_float(col, p)
        val_str, is_abn = flag(val, low, high, opt[0] if opt else False)
        
        # Override format for specific fields
        if val is None: val_str = "-"
        
        cls = "val-abn" if is_abn else ""
        if is_abn: abnormal_found = True
        
        rows += f"<tr><td>{label}</td><td class='t-center {cls}'>{val_str}</td><td class='t-center' style='color:#666;'>{norm}</td></tr>"
    return rows, abnormal_found

def generate_compact_body(p, history_df=None):
    sex = p.get("เพศ", "ชาย")
    
    # --- 1. CBC ---
    hb_low = 12 if sex == "หญิง" else 13
    hct_low = 36 if sex == "หญิง" else 39
    cbc_cfg = [
        ("Hb", "Hb(%)", f">{hb_low}", hb_low, None),
        ("Hct", "HCT", f">{hct_low}", hct_low, None),
        ("WBC", "WBC (cumm)", "4-10k", 4000, 10000),
        ("Neutrophil", "Ne (%)", "43-70", 43, 70),
        ("Lymphocyte", "Ly (%)", "20-44", 20, 44),
        ("Platelet", "Plt (/mm)", "1.5-5แสน", 150000, 500000)
    ]
    cbc_rows, cbc_abn = render_table_rows(cbc_cfg, p, sex)
    
    # --- 2. Urine ---
    # Simplified Urine Logic for table
    urine_data = [
        ("Color", "Color", "Yell"),
        ("pH", "pH", "5-8"),
        ("Sp.gr", "Spgr", "1.003-1.030"),
        ("Alb", "Alb", "Neg"),
        ("Sugar", "sugar", "Neg"),
        ("RBC", "RBC1", "0-2"),
        ("WBC", "WBC1", "0-5")
    ]
    urine_rows = ""
    for label, key, norm in urine_data:
        val = safe_value(p.get(key))
        is_abn = False
        if key == "Alb" and val.lower() not in ["negative", "trace", "-", ""]: is_abn = True
        if key == "sugar" and val.lower() not in ["negative", "-", ""]: is_abn = True
        # Basic check for others just to highlight
        style = "class='val-abn'" if is_abn else ""
        urine_rows += f"<tr><td>{label}</td><td {style}>{val}</td><td>{norm}</td></tr>"

    # --- 3. Blood Chem ---
    chem_cfg = [
        ("FBS", "FBS", "74-106", 74, 106),
        ("Cholesterol", "CHOL", "<200", None, 200),
        ("Triglyceride", "TGL", "<150", None, 150),
        ("HDL", "HDL", ">40", 40, None, True),
        ("LDL", "LDL", "<130", None, 130),
        ("Uric Acid", "Uric Acid", "<7.2", None, 7.2),
        ("Creatinine", "Cr", "0.5-1.2", 0.5, 1.17),
        ("GFR", "GFR", ">60", 60, None, True),
        ("SGOT", "SGOT", "<37", None, 37),
        ("SGPT", "SGPT", "<41", None, 41),
        ("ALP", "ALP", "30-120", 30, 120)
    ]
    chem_rows, chem_abn = render_table_rows(chem_cfg, p, sex)

    # --- 4. Stool ---
    stool_exam = safe_value(p.get("Stool exam"))
    stool_cs = safe_value(p.get("Stool C/S"))
    
    # --- 5. Special Tests ---
    cxr = interpret_cxr(p.get(f"CXR{str(p.get('Year'))[-2:]}" if p.get('Year') else "CXR"))
    ekg = interpret_ekg(p.get(f"EKG{str(p.get('Year'))[-2:]}" if p.get('Year') else "EKG"))
    
    # Hep B
    hbsag = safe_value(p.get("HbsAg", p.get("HbsAg67")))
    hbsab = safe_value(p.get("HbsAb", p.get("HbsAb67")))
    
    # --- 6. Recommendations Logic ---
    recs = []
    
    # Auto-generate basic recs
    fbs = get_float("FBS", p)
    if fbs and fbs > 100: recs.append("ลดอาหารหวาน แป้ง ผลไม้รสหวาน ออกกำลังกาย")
    
    chol = get_float("CHOL", p)
    if chol and chol > 200: recs.append("ลดไขมันสัตว์ กะทิ ของทอด ออกกำลังกาย")
    
    uric = get_float("Uric Acid", p)
    if uric and uric > 7.2: recs.append("งดเครื่องในสัตว์ ยอดผัก สัตว์ปีก ดื่มน้ำมากๆ")
    
    bp_s = get_float("SBP", p)
    if bp_s and bp_s > 140: recs.append("ลดเค็ม ลดความเครียด วัดความดันสม่ำเสมอ")

    # Manual Doctor Suggestion
    doc_suggest = str(p.get("DOCTER suggest", "")).strip()
    if doc_suggest and doc_suggest not in ["-", ""]:
        recs.append(f"<b>แพทย์แนะนำ:</b> {doc_suggest}")
    
    if not recs: recs.append("สุขภาพโดยรวมอยู่ในเกณฑ์ดี")

    rec_html = "".join([f"<li>{r}</li>" for r in recs])

    # --- Construct HTML Grid ---
    return f"""
    {render_compact_header(p)}
    <div class="grid-layout">
        <!-- Col 1 -->
        <div class="col-3">
            <div class="box">
                <div class="box-head">ความสมบูรณ์ของเลือด (CBC)</div>
                <div class="box-body">
                    <table>
                        <tr><th width="40%">Test</th><th width="30%" class="t-center">Result</th><th width="30%">Normal</th></tr>
                        {cbc_rows}
                    </table>
                </div>
            </div>
            <div class="box">
                <div class="box-head">ปัสสาวะ (Urine)</div>
                <div class="box-body">
                    <table>
                        <tr><th width="40%">Test</th><th width="30%">Result</th><th width="30%">Normal</th></tr>
                        {urine_rows}
                    </table>
                </div>
            </div>
        </div>

        <!-- Col 2 -->
        <div class="col-3">
            <div class="box">
                <div class="box-head">เคมีคลินิก (Blood Chemistry)</div>
                <div class="box-body">
                    <table>
                        <tr><th width="40%">Test</th><th width="30%" class="t-center">Result</th><th width="30%">Normal</th></tr>
                        {chem_rows}
                    </table>
                </div>
            </div>
            <div class="box">
                <div class="box-head">อุจจาระ (Stool)</div>
                <div class="box-body">
                    <table>
                        <tr><td>Exam:</td><td>{stool_exam}</td></tr>
                        <tr><td>Culture:</td><td>{stool_cs}</td></tr>
                    </table>
                </div>
            </div>
        </div>

        <!-- Col 3 -->
        <div class="col-3">
            <div class="box">
                <div class="box-head">ตรวจพิเศษ (Special Tests)</div>
                <div class="box-body">
                    <table>
                        <tr><td colspan="2"><b>Chest X-Ray:</b><br>{cxr}</td></tr>
                        <tr><td colspan="2"><b>EKG:</b><br>{ekg}</td></tr>
                        <tr><td style="border-top:1px solid #eee;">HBsAg: {hbsag}</td><td style="border-top:1px solid #eee;">HBsAb: {hbsab}</td></tr>
                    </table>
                </div>
            </div>
            
            <div class="rec-box">
                <div class="rec-title">สรุปและคำแนะนำ (Recommendation)</div>
                <ul class="rec-list">
                    {rec_html}
                </ul>
            </div>

            <div class="signature">
                <img src="" alt="" height="0"><br> <!-- Placeholder for space -->
                (นพ.นพรัตน์ รัชฎาพร)<br>
                แพทย์อาชีวเวชศาสตร์ (ว.26674)
            </div>
        </div>
    </div>
    """

def generate_compact_report(person_data, history_df=None):
    css = get_compact_css()
    body = generate_compact_body(person_data, history_df)
    return f"""<!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8">{css}</head>
    <body>
        <div class="container">
            {body}
        </div>
    </body>
    </html>"""
