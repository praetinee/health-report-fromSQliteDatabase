import pandas as pd
from datetime import datetime
import re
import html

# ==============================================================================
# หมายเหตุ: ไฟล์นี้มีฟังก์ชันที่จำเป็นสำหรับการสร้างรายงานในรูปแบบ HTML
# ฟังก์ชันส่วนใหญ่ถูกคัดลอกมาจาก app.py และปรับเปลี่ยนเพื่อสร้างผลลัพธ์เป็นสตริง HTML
# แทนการแสดงผลบน Streamlit โดยตรง
# ==============================================================================


# --- Helper Functions (คัดลอกมาจาก app.py) ---

def is_empty(val):
    return str(val).strip().lower() in ["", "-", "none", "nan", "null"]

THAI_MONTHS_GLOBAL = {
    1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน",
    5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม",
    9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"
}

def get_float(col, person_data):
    try:
        val = person_data.get(col, "")
        if is_empty(val):
            return None
        return float(str(val).replace(",", "").strip())
    except:
        return None

def flag(val, low=None, high=None, higher_is_better=False):
    try:
        val = float(str(val).replace(",", "").strip())
    except:
        return "-", False

    if higher_is_better and low is not None:
        return f"{val:.1f}", val < low
    if low is not None and val < low:
        return f"{val:.1f}", True
    if high is not None and val > high:
        return f"{val:.1f}", True
    return f"{val:.1f}", False

def safe_text(val):
    return "-" if str(val).strip().lower() in ["", "none", "nan", "-"] else str(val).strip()

def safe_value(val):
    val = str(val or "").strip()
    if val.lower() in ["", "nan", "none", "-"]:
        return "-"
    return val

def interpret_bp(sbp, dbp):
    try:
        sbp = float(sbp)
        dbp = float(dbp)
        if sbp == 0 or dbp == 0:
            return "-"
        if sbp >= 160 or dbp >= 100:
            return "ความดันสูง"
        elif sbp >= 140 or dbp >= 90:
            return "ความดันสูงเล็กน้อย"
        elif sbp < 120 and dbp < 80:
            return "ความดันปกติ"
        else:
            return "ความดันค่อนข้างสูง"
    except:
        return "-"

def combined_health_advice(bmi, sbp, dbp):
    if is_empty(bmi) and is_empty(sbp) and is_empty(dbp):
        return ""
    try:
        bmi = float(bmi)
    except:
        bmi = None
    try:
        sbp = float(sbp)
        dbp = float(dbp)
    except:
        sbp = dbp = None
    
    bmi_text = ""
    bp_text = ""
    
    if bmi is not None:
        if bmi > 30:
            bmi_text = "น้ำหนักเกินมาตรฐานมาก"
        elif bmi >= 25:
            bmi_text = "น้ำหนักเกินมาตรฐาน"
        elif bmi < 18.5:
            bmi_text = "น้ำหนักน้อยกว่ามาตรฐาน"
        else:
            bmi_text = "น้ำหนักอยู่ในเกณฑ์ปกติ"
    
    if sbp is not None and dbp is not None:
        if sbp >= 160 or dbp >= 100:
            bp_text = "ความดันโลหิตอยู่ในระดับสูงมาก"
        elif sbp >= 140 or dbp >= 90:
            bp_text = "ความดันโลหิตอยู่ในระดับสูง"
        elif sbp >= 120 or dbp >= 80:
            bp_text = "ความดันโลหิตเริ่มสูง"
    
    if bmi is not None and "ปกติ" in bmi_text and not bp_text:
        return "น้ำหนักอยู่ในเกณฑ์ดี ควรรักษาพฤติกรรมสุขภาพนี้ต่อไป"
    if not bmi_text and bp_text:
        return f"{bp_text} แนะนำให้ดูแลสุขภาพ และติดตามค่าความดันอย่างสม่ำเสมอ"
    if bmi_text and bp_text:
        return f"{bmi_text} และ {bp_text} แนะนำให้ปรับพฤติกรรมด้านอาหารและการออกกำลังกาย"
    if bmi_text and not bp_text:
        return f"{bmi_text} แนะนำให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"
    return ""

def merge_final_advice_grouped(messages):
    groups = {
        "FBS": [], "ไต": [], "ตับ": [], "ยูริค": [], "ไขมัน": [], "อื่นๆ": []
    }
    for msg in messages:
        if not msg or msg.strip() in ["-", ""]:
            continue
        if "น้ำตาล" in msg: groups["FBS"].append(msg)
        elif "ไต" in msg: groups["ไต"].append(msg)
        elif "ตับ" in msg: groups["ตับ"].append(msg)
        elif "พิวรีน" in msg or "ยูริค" in msg: groups["ยูริค"].append(msg)
        elif "ไขมัน" in msg: groups["ไขมัน"].append(msg)
        else: groups["อื่นๆ"].append(msg)
            
    output = []
    for title, msgs in groups.items():
        if msgs:
            unique_msgs = list(OrderedDict.fromkeys(msgs))
            output.append(f"<b>{title}:</b> {' '.join(unique_msgs)}")
            
    if not output:
        return "ไม่พบคำแนะนำเพิ่มเติมจากผลตรวจ"
    return "<br>".join(output)

# --- HTML Rendering Functions ---

def render_html_header(person):
    check_date = person.get("วันที่ตรวจ", "-")
    return f"""
    <div class="report-header-container" style="text-align: center; margin-bottom: 1rem; margin-top: 1rem;">
        <h1>รายงานผลการตรวจสุขภาพ</h1>
        <h2>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม -</h2>
        <p>ชั้น 2 อาคารผู้ป่วยนอก-อุบัติเหตุ โรงพยาบาลสันทราย 201 หมู่ 11 ถ.เชียงใหม่–พร้าว ต.หนองหาร อ.สันทราย จ.เชียงใหม่ 50290</p>
        <p>ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p>
        <p><b>วันที่ตรวจ:</b> {check_date or "-"}</p>
    </div>
    """

def render_personal_info(person):
    sbp = person.get("SBP", "")
    dbp = person.get("DBP", "")
    weight_raw = person.get("น้ำหนัก", "-")
    height_raw = person.get("ส่วนสูง", "-")

    try:
        weight_val = float(str(weight_raw).replace("กก.", "").strip())
        height_val = float(str(height_raw).replace("ซม.", "").strip())
        bmi_val = weight_val / ((height_val / 100) ** 2) if height_val > 0 else None
    except:
        bmi_val = None

    try:
        sbp_int = int(float(sbp))
        dbp_int = int(float(dbp))
        bp_val = f"{sbp_int}/{dbp_int} ม.ม.ปรอท"
    except:
        sbp_int = dbp_int = None
        bp_val = "-"
    
    bp_desc = interpret_bp(sbp, dbp)
    bp_full = f"{bp_val} - {bp_desc}" if bp_desc != "-" else bp_val
    
    advice_text = combined_health_advice(bmi_val, sbp, dbp)
    summary_advice = html.escape(advice_text) if advice_text else ""

    return f"""
    <div class="personal-info-container">
        <hr style="margin-top: 0.5rem; margin-bottom: 0.5rem;">
        <div style="display: flex; flex-wrap: wrap; justify-content: space-around; gap: 16px; margin-bottom: 0.2rem; text-align: left;">
            <span><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</span>
            <span><b>อายุ:</b> {str(int(float(person.get('อายุ')))) if str(person.get('อายุ')).replace('.', '', 1).isdigit() else person.get('อายุ', '-')} ปี</span>
            <span><b>เพศ:</b> {person.get('เพศ', '-')}</span>
            <span><b>HN:</b> {str(int(float(person.get('HN')))) if str(person.get('HN')).replace('.', '', 1).isdigit() else person.get('HN', '-')}</span>
            <span><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</span>
        </div>
        <div style="display: flex; flex-wrap: wrap; justify-content: space-around; gap: 16px; margin-bottom: 1rem; text-align: left;">
            <span><b>น้ำหนัก:</b> {person.get("น้ำหนัก", "-")} กก.</span>
            <span><b>ส่วนสูง:</b> {person.get("ส่วนสูง", "-")} ซม.</span>
            <span><b>รอบเอว:</b> {person.get("รอบเอว", "-")} ซม.</span>
            <span><b>ความดันโลหิต:</b> {bp_full}</span>
            <span><b>ชีพจร:</b> {person.get("pulse", "-")} ครั้ง/นาที</span>
        </div>
        {f"<div style='margin-top: 1rem; text-align: center;'><b>คำแนะนำ:</b> {summary_advice}</div>" if summary_advice else ""}
    </div>
    """

def render_lab_section(person, sex):
    # CBC Data
    if sex == "หญิง": hb_low, hct_low = 12, 36
    elif sex == "ชาย": hb_low, hct_low = 13, 39
    else: hb_low, hct_low = 12, 36

    cbc_config = [
        ("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None),
        ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None),
        ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000),
        ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000),
    ]
    cbc_rows = []
    for label, col, norm, low, high in cbc_config:
        val = get_float(col, person)
        result, is_abn = flag(val, low, high)
        cbc_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])
    
    # Blood Chemistry Data
    blood_config = [
        ("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106),
        ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20),
        ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17),
        ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True),
        ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2),
        ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200),
        ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150),
        ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True),
        ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160),
        ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37),
        ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41),
    ]
    blood_rows = []
    for label, col, norm, low, high, *opt in blood_config:
        higher = opt[0] if opt else False
        val = get_float(col, person)
        result, is_abn = flag(val, low, high, higher)
        blood_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])

    cbc_html = render_lab_table_html("ผลตรวจ CBC", None, ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows, "print-lab-table")
    blood_html = render_lab_table_html("ผลตรวจเลือด", None, ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows, "print-lab-table")
    
    return f"""
    <table style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="width: 50%; vertical-align: top; padding-right: 10px;">{cbc_html}</td>
            <td style="width: 50%; vertical-align: top; padding-left: 10px;">{blood_html}</td>
        </tr>
    </table>
    """

def generate_printable_report(person):
    """
    Generates a full, self-contained HTML string for the health report.
    """
    sex = str(person.get("เพศ", "")).strip()
    if sex not in ["ชาย", "หญิง"]: sex = "ไม่ระบุ"
    
    # --- Generate all HTML parts ---
    header_html = render_html_header(person)
    personal_info_html = render_personal_info(person)
    lab_section_html = render_lab_section(person, sex)

    # --- Final Advice Box ---
    advice_list = [
        kidney_advice_from_summary(kidney_summary_gfr_only(person.get("GFR", ""))),
        fbs_advice(person.get("FBS", "")),
        liver_advice(summarize_liver(person.get("ALP", ""), person.get("SGOT", ""), person.get("SGPT", ""))),
        uric_acid_advice(person.get("Uric Acid", "")),
        lipids_advice(summarize_lipids(person.get("CHOL", ""), person.get("TGL", ""), person.get("LDL", ""))),
        cbc_advice(person.get("Hb(%)", ""), person.get("HCT", ""), person.get("WBC (cumm)", ""), person.get("Plt (/mm)", ""), sex=sex)
    ]
    final_advice_html = merge_final_advice_grouped(advice_list)
    has_general_advice = "ไม่พบคำแนะนำเพิ่มเติม" not in final_advice_html
    bg_color_advice = "rgba(255, 255, 0, 0.2)" if has_general_advice else "rgba(57, 255, 20, 0.2)"
    
    advice_box_html = f"""
    <div style="background-color: {bg_color_advice}; padding: 0.6rem 2.5rem; border-radius: 10px; line-height: 1.6; font-size: 14px; margin-top: 1rem;">
        {final_advice_html}
    </div>
    """

    # --- Doctor Suggestion ---
    doctor_suggestion = str(person.get("DOCTER suggest", "")).strip()
    if is_empty(doctor_suggestion):
        doctor_suggestion = "<i>ไม่มีคำแนะนำจากแพทย์</i>"
    
    doctor_suggestion_html = f"""
    <div style="background-color: #1b5e20; color: white; padding: 0.4rem 2rem; border-radius: 8px; line-height: 1.6; margin-top: 2rem; font-size: 14px;">
        <b>สรุปความเห็นของแพทย์:</b><br> {doctor_suggestion}
    </div>
    """

    # --- Signature ---
    signature_html = """
    <div style="margin-top: 5rem; text-align: right; padding-right: 1rem;">
        <div style="display: inline-block; text-align: center; width: 340px;">
            <div style="border-bottom: 1px dotted #333; margin-bottom: 0.5rem; width: 100%;"></div>
            <div style="white-space: nowrap;">นายแพทย์นพรัตน์ รัชฎาพร</div>
            <div style="white-space: nowrap;">เลขที่ใบอนุญาตผู้ประกอบวิชาชีพเวชกรรม ว.26674</div>
        </div>
    </div>
    """

    # --- Assemble the final HTML page ---
    final_html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลการตรวจสุขภาพ - {person.get('ชื่อ-สกุล', '')}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
            body {{
                font-family: 'Sarabun', sans-serif !important;
                font-size: 12px;
                margin: 20px;
            }}
            p {{ margin: 0.2rem 0; }}
            h1 {{ font-size: 1.6rem; margin: 0; }}
            h2 {{ font-size: 1rem; color: #555; font-weight: bold; margin: 0; }}
            table {{ border-collapse: collapse; width: 100%; }}
            .print-lab-table td, .print-lab-table th {{
                padding: 2px 4px;
                border: 1px solid #ddd;
                text-align: center;
            }}
            .print-lab-table th {{ background-color: #f2f2f2; font-weight: bold; }}
            .print-lab-table-abn {{ background-color: #ffdddd; }}
            @media print {{
                body {{ -webkit-print-color-adjust: exact; margin: 0; }}
            }}
        </style>
    </head>
    <body>
        {header_html}
        {personal_info_html}
        {lab_section_html}
        {advice_box_html}
        {doctor_suggestion_html}
        {signature_html}
    </body>
    </html>
    """
    return final_html
