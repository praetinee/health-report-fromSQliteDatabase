import pandas as pd
from datetime import datetime
import html
from collections import OrderedDict

# --- แก้ไข: import ฟังก์ชันที่จำเป็นสำหรับการตรวจสมรรถภาพ ---
from performance_tests import (
    generate_comprehensive_recommendations, 
    interpret_audiogram, 
    interpret_lung_capacity
)

# ==============================================================================
# หมายเหตุ: ไฟล์นี้ถูกปรับปรุงใหม่เพื่อรองรับการพิมพ์ผลตรวจสมรรถภาพ (ตา, หู, ปอด)
# โดยจะตรวจสอบข้อมูลและแสดงผลเฉพาะรายการที่มีการตรวจในปีนั้นๆ รวมอยู่ในหน้าเดียว
# ==============================================================================


# --- Helper & Data Availability Functions ---

def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def get_float(person_data, key):
    """Safely gets a float value from person_data dictionary."""
    val = person_data.get(key)
    if is_empty(val): return None
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None

def has_vision_data(person_data):
    """Check for any vision test data."""
    detailed_keys = [
        'ป.การรวมภาพ', 'ผ.การรวมภาพ', 'ป.ความชัดของภาพระยะไกล', 
        'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)', 'ป.การจำแนกสี'
    ]
    return any(not is_empty(person_data.get(key)) for key in detailed_keys)

def has_hearing_data(person_data):
    """Check for detailed hearing (audiogram) data."""
    hearing_keys = ['R500', 'L500', 'R1k', 'L1k', 'R4k', 'L4k']
    return any(not is_empty(person_data.get(key)) for key in hearing_keys)

def has_lung_data(person_data):
    """Check for lung capacity test data."""
    key_indicators = ['FVC เปอร์เซ็นต์', 'FEV1เปอร์เซ็นต์', 'FEV1/FVC%']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)


# --- Core Interpretation & Formatting Functions (from app.py) ---
# (ส่วนนี้เป็นฟังก์ชันพื้นฐานที่จำเป็นสำหรับการแสดงผลตารางผลเลือดและข้อมูลส่วนตัว)

def flag(val, low=None, high=None, higher_is_better=False):
    try:
        val_float = float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return "-", False
    formatted_val = f"{int(val_float):,}" if val_float == int(val_float) else f"{val_float:,.1f}"
    is_abn = False
    if higher_is_better:
        if low is not None and val_float < low: is_abn = True
    else:
        if low is not None and val_float < low: is_abn = True
        if high is not None and val_float > high: is_abn = True
    return formatted_val, is_abn

def interpret_bp(sbp, dbp):
    try:
        sbp, dbp = float(sbp), float(dbp)
        if sbp == 0 or dbp == 0: return "-"
        if sbp >= 160 or dbp >= 100: return "ความดันสูง"
        elif sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
        elif sbp < 120 and dbp < 80: return "ความดันปกติ"
        else: return "ความดันค่อนข้างสูง"
    except: return "-"


# --- HTML Rendering Functions ---

def render_section_header(title, subtitle=None, is_sub_header=False):
    bg_color = "#555" if is_sub_header else "#333"
    font_size = "10px" if is_sub_header else "11px"
    margin_top = "0.8rem" if is_sub_header else "1.5rem"
    
    full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
    return f"""
    <div style='
        background-color: {bg_color};
        color: white;
        text-align: center;
        padding: 0.2rem 0.4rem;
        font-weight: bold;
        border-radius: 6px;
        margin-top: {margin_top};
        margin-bottom: 0.5rem;
        font-size: {font_size};
    '>
        {full_title}
    </div>
    """

def render_html_header(person):
    check_date = person.get("วันที่ตรวจ", "-")
    return f"""
    <div class="report-header-container" style="text-align: center; margin-bottom: 0.5rem; margin-top: 0.5rem;">
        <h1 style="font-size: 1.2rem; margin:0;">รายงานผลการตรวจสุขภาพ</h1>
        <h2 style="font-size: 0.8rem; margin:0;">- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม -</h2>
        <p style="font-size: 0.7rem; margin:0;">ชั้น 2 อาคารผู้ป่วยนอก-อุบัติเหตุ โรงพยาบาลสันทราย 201 หมู่ 11 ถ.เชียงใหม่–พร้าว ต.หนองหาร อ.สันทราย จ.เชียงใหม่ 50290</p>
        <p style="font-size: 0.7rem; margin:0;">ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167 | <b>วันที่ตรวจ:</b> {check_date or "-"}</p>
    </div>
    """

def render_personal_info(person):
    sbp = person.get("SBP", "")
    dbp = person.get("DBP", "")
    pulse_raw = person.get("pulse", "-")
    pulse_val = str(int(float(pulse_raw))) if not is_empty(pulse_raw) else "-"
    bp_desc = interpret_bp(sbp, dbp)
    bp_val = f"{int(float(sbp))}/{int(float(dbp))} ม.ม.ปรอท" if not is_empty(sbp) and not is_empty(dbp) else "-"
    bp_full = f"{bp_val} ({bp_desc})" if bp_desc != "-" else bp_val

    return f"""
    <div class="personal-info-container">
        <hr style="margin-top: 0.5rem; margin-bottom: 0.5rem;">
        <table class="info-table">
            <tr>
                <td><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</td>
                <td><b>อายุ:</b> {str(int(float(person.get('อายุ')))) if not is_empty(person.get('อายุ')) else '-'} ปี</td>
                <td><b>เพศ:</b> {person.get('เพศ', '-')}</td>
                <td><b>HN:</b> {str(int(float(person.get('HN')))) if not is_empty(person.get('HN')) else '-'}</td>
            </tr>
            <tr>
                <td><b>น้ำหนัก:</b> {person.get("น้ำหนัก", "-")} กก.</td>
                <td><b>ส่วนสูง:</b> {person.get("ส่วนสูง", "-")} ซม.</td>
                <td><b>ความดันโลหิต:</b> {bp_full}</td>
                <td><b>ชีพจร:</b> {pulse_val} ครั้ง/นาที</td>
            </tr>
        </table>
    </div>
    """

# --- NEW: Performance Test Print Renderers ---

def render_print_vision(person_data):
    vision_advice = person_data.get('สรุปเหมาะสมกับงาน', 'ไม่มีข้อมูลสรุป')
    
    # Logic from app.py's render_vision_details_table
    tests = [
        {'d': 'การมองด้วย 2 ตา', 'c': 'ป.การรวมภาพ', 'nk': ['ปกติ']},
        {'d': 'การมองภาพ 3 มิติ', 'c': 'ป.การกะระยะและมองความชัดลึกของภาพ', 'nk': ['ปกติ']},
        {'d': 'การมองจำแนกสี', 'c': 'ป.การจำแนกสี', 'nk': ['ปกติ']},
        {'d': 'การมองไกล (ตาขวา)', 'c': 'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)', 'nk': ['ชัดเจน', 'ปกติ']},
        {'d': 'การมองไกล (ตาซ้าย)', 'c': 'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)', 'nk': ['ชัดเจน', 'ปกติ']},
        {'d': 'การมองใกล้ (ตาขวา)', 'c': 'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)', 'nk': ['ชัดเจน', 'ปกติ']},
        {'d': 'การมองใกล้ (ตาซ้าย)', 'c': 'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)', 'nk': ['ชัดเจน', 'ปกติ']},
    ]
    
    rows_html = ""
    for test in tests:
        val = str(person_data.get(test['c'], '')).strip()
        status = "ไม่ได้ตรวจ"
        status_class = "status-nt"
        if not is_empty(val):
            if any(k.lower() in val.lower() for k in test['nk']):
                status = "ปกติ"
                status_class = "status-ok"
            else:
                status = "ผิดปกติ"
                status_class = "status-abn"
        rows_html += f"<tr><td>{test['d']}</td><td class='{status_class}'>{status}</td></tr>"

    return f"""
    <div class="perf-section">
        {render_section_header("ผลการตรวจสมรรถภาพการมองเห็น (Vision)", is_sub_header=True)}
        <div class="perf-columns">
            <div class="perf-col-summary">
                <b>สรุปความเหมาะสมกับงาน:</b>
                <div class="summary-box">{vision_advice}</div>
            </div>
            <div class="perf-col-details">
                <table class="perf-table">
                    <thead><tr><th>รายการตรวจ</th><th>ผล</th></tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
        </div>
    </div>
    """

def render_print_hearing(person_data):
    results = interpret_audiogram(person_data) # No history needed for basic print
    if results['summary'].get('overall') == "ไม่ได้เข้ารับการตรวจ": return ""

    summary_r = person_data.get('ผลตรวจการได้ยินหูขวา', 'N/A')
    summary_l = person_data.get('ผลตรวจการได้ยินหูซ้าย', 'N/A')
    advice = results.get('advice', 'ไม่มีคำแนะนำ')

    raw_data = results.get('raw_values', {})
    rows_html = ""
    for freq, values in raw_data.items():
        r_val = values.get('right', '-')
        l_val = values.get('left', '-')
        rows_html += f"<tr><td>{freq}</td><td>{r_val}</td><td>{l_val}</td></tr>"

    return f"""
    <div class="perf-section">
        {render_section_header("ผลการตรวจสมรรถภาพการได้ยิน (Hearing)", is_sub_header=True)}
        <div class="perf-columns">
            <div class="perf-col-summary">
                <b>สรุปผล:</b>
                <div class="summary-box">
                    <b>หูขวา:</b> {summary_r}<br>
                    <b>หูซ้าย:</b> {summary_l}
                </div>
                <b>คำแนะนำ:</b>
                <div class="summary-box">{advice}</div>
            </div>
            <div class="perf-col-details">
                <table class="perf-table">
                    <thead><tr><th>ความถี่ (Hz)</th><th>หูขวา (dB)</th><th>หูซ้าย (dB)</th></tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
        </div>
    </div>
    """

def render_print_lung(person_data):
    summary, advice, raw = interpret_lung_capacity(person_data)
    if summary == "ไม่ได้เข้ารับการตรวจ": return ""

    def format_val(key):
        val = raw.get(key)
        return f"{val:.1f}" if val is not None else "-"

    return f"""
    <div class="perf-section">
        {render_section_header("ผลการตรวจสมรรถภาพปอด (Lung Function)", is_sub_header=True)}
        <table class="info-table lung-table">
            <tr>
                <th>FVC (% Pred)</th><th>FEV1 (% Pred)</th><th>FEV1/FVC Ratio (%)</th>
            </tr>
            <tr>
                <td>{format_val('FVC %')}</td><td>{format_val('FEV1 %')}</td><td>{format_val('FEV1/FVC %')}</td>
            </tr>
        </table>
        <div class="perf-columns" style="margin-top: 0.5rem;">
             <div class="perf-col-summary">
                <b>สรุปผล:</b>
                <div class="summary-box">{summary}</div>
            </div>
             <div class="perf-col-summary">
                <b>คำแนะนำ:</b>
                <div class="summary-box">{advice}</div>
            </div>
        </div>
    </div>
    """


# --- Main Report Generator ---

def generate_printable_report(person):
    """
    Generates a full, self-contained HTML string for the health report,
    including performance tests if available.
    """
    # --- Generate all HTML parts for the main report ---
    header_html = render_html_header(person)
    personal_info_html = render_personal_info(person)
    recommendations_html = generate_comprehensive_recommendations(person)

    # --- NEW: Generate Performance Test HTML (if data exists) ---
    performance_html_parts = []
    if has_vision_data(person):
        performance_html_parts.append(render_print_vision(person))
    if has_hearing_data(person):
        performance_html_parts.append(render_print_hearing(person))
    if has_lung_data(person):
        performance_html_parts.append(render_print_lung(person))
    
    performance_section_html = ""
    if performance_html_parts:
        performance_section_html = (
            render_section_header("ผลการตรวจสมรรถภาพพิเศษ (Performance Tests)") +
            "".join(performance_html_parts)
        )

    # --- Assemble the final HTML page ---
    final_html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลการตรวจสุขภาพ - {html.escape(person.get('ชื่อ-สกุล', ''))}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
            body {{
                font-family: 'Sarabun', sans-serif !important;
                font-size: 9px;
                margin: 10mm;
                color: #333;
            }}
            p, div, span, td, th {{ line-height: 1.4; }}
            table {{ border-collapse: collapse; width: 100%; }}
            hr {{ border: 0; border-top: 1px solid #ccc; }}
            ul {{ padding-left: 15px; margin: 0.2rem 0; }}
            li {{ margin-bottom: 2px; }}

            .info-table td {{ padding: 2px 5px; }}
            
            .recommendation-section {{
                page-break-inside: avoid;
                margin-top: 1rem;
            }}
            .rec-columns {{ display: flex; flex-wrap: nowrap; gap: 20px; align-items: flex-start; }}
            .rec-col {{ flex: 1; min-width: 0; }}
            
            .perf-section {{ page-break-inside: avoid; margin-top: 0.5rem; }}
            .perf-columns {{ display: flex; flex-wrap: nowrap; gap: 15px; align-items: flex-start; }}
            .perf-col-summary {{ flex: 1; }}
            .perf-col-details {{ flex: 1.2; }}
            .summary-box {{ 
                border: 1px solid #eee; background-color: #fcfcfc; 
                padding: 5px; border-radius: 4px; margin-top: 2px; 
                min-height: 3em;
            }}
            .perf-table {{ width: 100%; font-size: 8px; }}
            .perf-table th, .perf-table td {{ border: 1px solid #ddd; padding: 2px 4px; text-align: center; }}
            .perf-table th {{ background-color: #f2f2f2; }}
            .perf-table td:first-child {{ text-align: left; }}
            .lung-table th, .lung-table td {{ text-align: center; border: 1px solid #ddd; padding: 3px; }}
            
            .status-ok {{ background-color: #e8f5e9; color: #2e7d32; }}
            .status-abn {{ background-color: #ffcdd2; color: #c62828; font-weight: bold; }}
            .status-nt {{ color: #757575; }}

            @media print {{
                body {{ -webkit-print-color-adjust: exact; margin: 0; }}
            }}
        </style>
    </head>
    <body>
        {header_html}
        {personal_info_html}
        {render_section_header("สรุปผลตรวจและคำแนะนำ (Summary & Recommendations)")}
        <div class="recommendation-section">
            <div class="rec-columns">
                <div class="rec-col">
                    {recommendations_html.split("<!-- SPLIT -->")[0]}
                </div>
                <div class="rec-col">
                    {recommendations_html.split("<!-- SPLIT -->")[1]}
                </div>
            </div>
        </div>
        
        {performance_section_html}

    </body>
    </html>
    """
    # Quick fix for splitting recommendations into two columns in the print layout
    # by splitting the generated HTML.
    # A more robust solution would be to generate left and right columns separately.
    # This is a temporary solution to meet the request.
    
    # Let's refine the split logic. I'll inject a split point in the generator.
    
    # Re-generate recommendations with a split point
    recommendations_html_full = generate_comprehensive_recommendations(person)
    
    # Split the HTML for two-column layout
    rec_parts = recommendations_html_full.split("<!-- SPLIT -->")
    rec_left_html = rec_parts[0]
    rec_right_html = rec_parts[1] if len(rec_parts) > 1 else ""

    # Re-assemble the final HTML with the correct split
    final_html = final_html.replace(
        '<div class="rec-col">', 
        f'<div class="rec-col">{rec_left_html}</div><div class="rec-col">{rec_right_html}</div><!--', 
        1
    ).replace(
        '</div>',
        '-->',
        1
    )


    return final_html

# --- แก้ไข generate_comprehensive_recommendations ให้รองรับการแบ่งคอลัมน์ ---
def generate_comprehensive_recommendations(person_data):
    """
    สร้างสรุปและคำแนะนำฯ และแทรกจุดแบ่งคอลัมน์สำหรับหน้าพิมพ์
    """
    key_indicators = ['FBS', 'CHOL', 'HCT', 'Cr', 'WBC (cumm)', 'น้ำหนัก', 'ส่วนสูง', 'SBP']
    has_data = any(not is_empty(person_data.get(key)) for key in key_indicators)

    if not has_data:
        return "" 

    issues = {'high': [], 'medium': [], 'low': []}
    conditions = set()
    
    # ... (โค้ดการแปลผลทั้งหมดเหมือนเดิม) ...
    # --- 1. Vital Signs & BMI ---
    weight = get_float(person_data, "น้ำหนัก")
    height = get_float(person_data, "ส่วนสูง")
    sbp = get_float(person_data, "SBP")
    dbp = get_float(person_data, "DBP")

    if weight and height and height > 0:
        bmi = weight / ((height / 100) ** 2)
        if bmi >= 30:
            issues['medium'].append(f"<b>ภาวะอ้วน (BMI ≥ 30):</b> เป็นความเสี่ยงหลักต่อโรคเรื้อรังต่างๆ")
            conditions.add('obesity')
        elif bmi >= 25:
            issues['low'].append(f"<b>น้ำหนักเกินเกณฑ์ (BMI 25-29.9):</b> ควรเริ่มควบคุมอาหารและออกกำลังกาย")
            conditions.add('overweight')
    
    if sbp and dbp:
        if sbp >= 160 or dbp >= 100:
            issues['high'].append(f"<b>ความดันโลหิตสูงรุนแรง ({int(sbp)}/{int(dbp)} mmHg):</b> มีความเสี่ยงอันตราย ควรพบแพทย์โดยเร็ว")
            conditions.add('hypertension')
        elif sbp >= 140 or dbp >= 90:
            issues['medium'].append(f"<b>ความดันโลหิตสูง ({int(sbp)}/{int(dbp)} mmHg):</b> ควรปรับเปลี่ยนพฤติกรรมและติดตามใกล้ชิด")
            conditions.add('hypertension')
        elif sbp >= 120 or dbp >= 80:
            issues['low'].append(f"<b>ความดันโลหิตเริ่มสูง ({int(sbp)}/{int(dbp)} mmHg):</b> เป็นสัญญาณเตือนให้เริ่มดูแลสุขภาพ")
            conditions.add('prehypertension')

    # --- 2. Blood Chemistry ---
    fbs = get_float(person_data, "FBS")
    if fbs:
        if fbs >= 126:
            issues['high'].append(f"<b>ระดับน้ำตาลในเลือดสูง ({int(fbs)} mg/dL):</b> เข้าเกณฑ์เบาหวาน ควรพบแพทย์เพื่อยืนยันและรักษา")
            conditions.add('diabetes')
        elif fbs >= 100:
            issues['medium'].append(f"<b>ภาวะเสี่ยงเบาหวาน ({int(fbs)} mg/dL):</b> ควรควบคุมอาหารและออกกำลังกายอย่างจริงจัง")
            conditions.add('prediabetes')

    chol = get_float(person_data, "CHOL")
    tgl = get_float(person_data, "TGL")
    ldl = get_float(person_data, "LDL")
    hdl = get_float(person_data, "HDL")
    lipid_issues_text = []
    is_lipid_high_risk = False
    
    if chol:
        if chol >= 240:
            lipid_issues_text.append("คอเลสเตอรอลสูงมาก")
            is_lipid_high_risk = True
        elif chol >= 200:
            lipid_issues_text.append("คอเลสเตอรอลสูง")
    if tgl:
        if tgl >= 500:
            lipid_issues_text.append("ไตรกลีเซอไรด์สูงมาก")
            is_lipid_high_risk = True
        elif tgl >= 200:
            lipid_issues_text.append("ไตรกลีเซอไรด์สูง")
        elif tgl >= 150:
            lipid_issues_text.append("ไตรกลีเซอไรด์เริ่มสูง")
    if ldl:
        if ldl >= 190:
            lipid_issues_text.append("LDL (ไขมันเลว) สูงมาก")
            is_lipid_high_risk = True
        elif ldl >= 160:
            lipid_issues_text.append("LDL (ไขมันเลว) สูง")
        elif ldl >= 130:
            lipid_issues_text.append("LDL (ไขมันเลว) เริ่มสูง")
    if hdl and hdl < 40:
        lipid_issues_text.append("HDL (ไขมันดี) ต่ำ")

    if lipid_issues_text:
        risk_level = 'high' if is_lipid_high_risk else 'medium'
        issues[risk_level].append(f"<b>ภาวะไขมันในเลือดผิดปกติ ({', '.join(lipid_issues_text)}):</b> เพิ่มความเสี่ยงโรคหัวใจและหลอดเลือด")
        conditions.add('dyslipidemia')

    gfr = get_float(person_data, "GFR")
    if gfr:
        if gfr < 30:
            issues['high'].append("<b>การทำงานของไตลดลงมาก (ระยะ 4-5):</b> ควรพบแพทย์ผู้เชี่ยวชาญโรคไตโดยด่วน")
            conditions.add('kidney_disease')
        elif gfr < 60:
            issues['medium'].append("<b>การทำงานของไตเริ่มเสื่อม (ระยะ 3):</b> ควรลดอาหารเค็มและโปรตีนสูง ปรึกษาแพทย์")
            conditions.add('kidney_disease')
        elif gfr < 90:
             issues['low'].append("<b>การทำงานของไตลดลงเล็กน้อย (ระยะ 2):</b> ควรดื่มน้ำให้เพียงพอและหลีกเลี่ยงยาที่มีผลต่อไต")
             conditions.add('kidney_disease')

    sgot = get_float(person_data, "SGOT")
    sgpt = get_float(person_data, "SGPT")
    sgot_upper, sgpt_upper = 37, 41
    if (sgot and sgot > sgot_upper) or (sgpt and sgpt > sgpt_upper):
        if (sgot and sgot > sgot_upper * 3) or (sgpt and sgpt > sgpt_upper * 3):
            issues['high'].append("<b>ค่าเอนไซม์ตับสูงมาก:</b> บ่งชี้ภาวะตับอักเสบ ควรพบแพทย์โดยเร็ว")
        else:
            issues['medium'].append("<b>ค่าเอนไซม์ตับสูง:</b> อาจเกิดจากไขมันพอกตับ ควรลดของมัน แอลกอฮอล์")
        conditions.add('liver')

    uric = get_float(person_data, "Uric Acid")
    if uric:
        if uric > 9.0:
            issues['medium'].append("<b>กรดยูริกสูงมาก:</b> มีความเสี่ยงสูงต่อโรคเกาต์ ควรปรึกษาแพทย์")
            conditions.add('uric_acid')
        elif uric > 7.2:
            issues['low'].append("<b>กรดยูริกสูง:</b> เสี่ยงต่อโรคเกาต์ ควรลดการทานเครื่องในสัตว์ สัตว์ปีก")
            conditions.add('uric_acid')

    # --- 3. Complete Blood Count (CBC) ---
    sex = person_data.get("เพศ", "ชาย")
    hb = get_float(person_data, "Hb(%)")
    wbc = get_float(person_data, "WBC (cumm)")
    platelet = get_float(person_data, "Plt (/mm)")
    
    hb_limit = 12 if sex == "หญิง" else 13
    if hb and hb < hb_limit:
        issues['medium'].append("<b>ภาวะโลหิตจาง:</b> ควรทานอาหารที่มีธาตุเหล็กสูงและตรวจหาสาเหตุเพิ่มเติม")
        conditions.add('anemia')
        
    if wbc:
        if wbc > 10000: issues['medium'].append("<b>เม็ดเลือดขาวสูง:</b> อาจมีการอักเสบหรือติดเชื้อในร่างกาย ควรตรวจหาสาเหตุ")
        if wbc < 4000: issues['low'].append("<b>เม็ดเลือดขาวต่ำ:</b> อาจส่งผลต่อภูมิคุ้มกัน ควรพักผ่อนให้เพียงพอ")
        
    if platelet:
        if platelet < 150000: issues['medium'].append("<b>เกล็ดเลือดต่ำ:</b> อาจเสี่ยงเลือดออกง่าย ควรระมัดระวังอุบัติเหตุและปรึกษาแพทย์")
        if platelet > 500000: issues['medium'].append("<b>เกล็ดเลือดสูง:</b> ควรพบแพทย์เพื่อตรวจหาสาเหตุ")

    # --- 4. Urinalysis, Stool, X-ray, EKG, Hepatitis ---
    urine_issues = interpret_urine(person_data)
    for issue, (text, level) in urine_issues.items():
        issues[level].append(f"<b>{issue}:</b> {text}")

    stool_issues = interpret_stool(person_data)
    for issue, (text, level) in stool_issues.items():
        issues[level].append(f"<b>{issue}:</b> {text}")
        
    hep_issues = interpret_hepatitis(person_data)
    for issue, (text, level) in hep_issues.items():
        issues[level].append(f"<b>{issue}:</b> {text}")

    year = person_data.get("Year", "")
    cxr_col = f"CXR{str(year)[-2:]}" if str(year) != "" and str(year) != str(np.datetime64('now', 'Y').astype(int) + 1970 + 543) else "CXR"
    cxr_result, cxr_status = interpret_cxr(person_data.get(cxr_col, ''))
    if cxr_status == 'abnormal':
        issues['high'].append(f"<b>ผลเอกซเรย์ทรวงอกผิดปกติ ({cxr_result}):</b> ควรพบแพทย์เพื่อตรวจวินิจฉัยเพิ่มเติม")

    ekg_col = f"EKG{str(year)[-2:]}" if str(year) != "" and str(year) != str(np.datetime64('now', 'Y').astype(int) + 1970 + 543) else "EKG"
    ekg_result, ekg_status = interpret_ekg(person_data.get(ekg_col, ''))
    if ekg_status == 'abnormal':
        issues['high'].append(f"<b>ผลคลื่นไฟฟ้าหัวใจผิดปกติ ({ekg_result}):</b> ควรพบแพทย์โรคหัวใจ")

    # --- Build Left Column (Issues) ---
    left_column_parts = []
    if issues['high']:
        left_column_parts.append("<div style='border-left: 5px solid #c62828; padding-left: 15px; margin-bottom: 1.5rem;'>")
        left_column_parts.append("<h5 style='color: #c62828; margin-top:0;'>ควรพบแพทย์เพื่อประเมินเพิ่มเติม</h5><ul>")
        for item in set(issues['high']): left_column_parts.append(f"<li>{item}</li>")
        left_column_parts.append("</ul></div>")
    if issues['medium']:
        left_column_parts.append("<div style='border-left: 5px solid #f9a825; padding-left: 15px; margin-bottom: 1.5rem;'>")
        left_column_parts.append("<h5 style='color: #f9a825; margin-top:0;'>ประเด็นสุขภาพที่ควรปรับพฤติกรรม</h5><ul>")
        for item in set(issues['medium']): left_column_parts.append(f"<li>{item}</li>")
        left_column_parts.append("</ul></div>")
    if issues['low']:
        left_column_parts.append("<div style='border-left: 5px solid #1976d2; padding-left: 15px; margin-bottom: 1.5rem;'>")
        left_column_parts.append("<h5 style='color: #1976d2; margin-top:0;'>ข้อควรระวังและการเฝ้าติดตาม</h5><ul>")
        for item in set(issues['low']): left_column_parts.append(f"<li>{item}</li>")
        left_column_parts.append("</ul></div>")

    # --- Build Right Column (Health Plan) ---
    right_column_parts = []
    health_plan = {'nutrition': set(), 'exercise': set(), 'monitoring': set()}
    
    if 'diabetes' in conditions or 'prediabetes' in conditions:
        health_plan['nutrition'].add("ควบคุมอาหารประเภทแป้งและน้ำตาลอย่างจริงจัง")
        health_plan['monitoring'].add("ตรวจติดตามระดับน้ำตาลในเลือดสม่ำเสมอ")
    if 'hypertension' in conditions or 'prehypertension' in conditions:
        health_plan['nutrition'].add("ลดอาหารเค็มและโซเดียมสูง")
        health_plan['monitoring'].add("วัดความดันโลหิตที่บ้านอย่างสม่ำเสมอ")
    if 'dyslipidemia' in conditions:
        health_plan['nutrition'].add("ลดอาหารมัน ของทอด และไขมันอิ่มตัว")
    if 'obesity' in conditions or 'overweight' in conditions:
        health_plan['nutrition'].add("ควบคุมปริมาณอาหารและเลือกทานอาหารแคลอรี่ต่ำ")
    if 'kidney_disease' in conditions:
        health_plan['nutrition'].add("ลดอาหารเค็มจัดและโปรตีนสูงบางชนิด (ปรึกษาแพทย์)")
        health_plan['monitoring'].add("ดื่มน้ำให้เพียงพอและหลีกเลี่ยงยาที่มีผลต่อไต")
    if 'liver' in conditions:
        health_plan['nutrition'].add("งดเครื่องดื่มแอลกอฮอล์และลดอาหารไขมันสูง")
    if 'uric_acid' in conditions:
        health_plan['nutrition'].add("ลดการทานเครื่องในสัตว์, สัตว์ปีก, และยอดผัก")
    if 'anemia' in conditions:
        health_plan['nutrition'].add("ทานอาหารที่มีธาตุเหล็กและวิตามินซีสูง เช่น ตับ, เนื้อแดง, ผักใบเขียว")

    if any(c in conditions for c in ['obesity', 'overweight', 'hypertension', 'diabetes', 'prediabetes', 'dyslipidemia']):
        health_plan['exercise'].add("ออกกำลังกายแบบแอโรบิก (เดินเร็ว, วิ่ง, ว่ายน้ำ) อย่างน้อย 150 นาที/สัปดาห์")
    else:
        health_plan['exercise'].add("เคลื่อนไหวร่างกายอย่างสม่ำเสมอ 3-4 วัน/สัปดาห์")

    health_plan['monitoring'].add("นอนหลับพักผ่อนให้เพียงพอ 7-8 ชั่วโมง/คืน")
    health_plan['monitoring'].add("มาตรวจสุขภาพประจำปีเพื่อติดตามผล")

    right_column_parts.append("<div style='border-left: 5px solid #4caf50; padding-left: 15px;'>")
    right_column_parts.append("<h5 style='color: #4caf50; margin-top:0;'>แผนการดูแลสุขภาพเบื้องต้น (Your Health Plan)</h5>")
    if health_plan['nutrition']:
        right_column_parts.append("<b>ด้านโภชนาการ:</b><ul>")
        for item in sorted(list(health_plan['nutrition'])): right_column_parts.append(f"<li>{item}</li>")
        right_column_parts.append("</ul>")
    if health_plan['exercise']:
        right_column_parts.append("<b>ด้านการออกกำลังกาย:</b><ul>")
        for item in sorted(list(health_plan['exercise'])): right_column_parts.append(f"<li>{item}</li>")
        right_column_parts.append("</ul>")
    if health_plan['monitoring']:
        right_column_parts.append("<b>การติดตามและดูแลทั่วไป:</b><ul>")
        for item in sorted(list(health_plan['monitoring'])): right_column_parts.append(f"<li>{item}</li>")
        right_column_parts.append("</ul>")
    right_column_parts.append("</div>")

    return "".join(left_column_parts) + "<!-- SPLIT -->" + "".join(right_column_parts)
