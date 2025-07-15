import pandas as pd
from datetime import datetime
import re
import html
from collections import OrderedDict
import base64

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

def kidney_summary_gfr_only(gfr_raw):
    try:
        gfr = float(str(gfr_raw).replace(",", "").strip())
        if gfr == 0:
            return ""
        elif gfr < 60:
            return "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย"
        else:
            return "ปกติ"
    except:
        return ""

def kidney_advice_from_summary(summary_text):
    if summary_text == "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย":
        return (
            "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย "
            "ลดอาหารเค็ม อาหารโปรตีนสูงย่อยยาก ดื่มน้ำ 8-10 แก้วต่อวัน "
            "และไม่ควรกลั้นปัสสาวะ มีอาการบวมผิดปกติให้พบแพทย์"
        )
    return ""

def fbs_advice(fbs_raw):
    if is_empty(fbs_raw):
        return ""
    try:
        value = float(str(fbs_raw).replace(",", "").strip())
        if value == 0:
            return ""
        elif 100 <= value < 106:
            return "ระดับน้ำตาลเริ่มสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภคอาหารหวาน แป้ง และออกกำลังกาย"
        elif 106 <= value < 126:
            return "ระดับน้ำตาลสูงเล็กน้อย ควรลดอาหารหวาน แป้ง ของมัน ตรวจติดตามน้ำตาลซ้ำ และออกกำลังกายสม่ำเสมอ"
        elif value >= 126:
            return "ระดับน้ำตาลสูง ควรพบแพทย์เพื่อตรวจยืนยันเบาหวาน และติดตามอาการ"
        else:
            return ""
    except:
        return ""

def summarize_liver(alp_val, sgot_val, sgpt_val):
    try:
        alp = float(alp_val)
        sgot = float(sgot_val)
        sgpt = float(sgpt_val)
        if alp == 0 or sgot == 0 or sgpt == 0:
            return "-"
        if alp > 120 or sgot > 36 or sgpt > 40:
            return "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย"
        return "ปกติ"
    except:
        return ""

def liver_advice(summary_text):
    if summary_text == "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย":
        return "ควรลดอาหารไขมันสูงและตรวจติดตามการทำงานของตับซ้ำ"
    elif summary_text == "ปกติ":
        return ""
    return "-"

def uric_acid_advice(value_raw):
    try:
        value = float(value_raw)
        if value > 7.2:
            return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
        return ""
    except:
        return ""

def summarize_lipids(chol_raw, tgl_raw, ldl_raw):
    try:
        chol = float(str(chol_raw).replace(",", "").strip())
        tgl = float(str(tgl_raw).replace(",", "").strip())
        ldl = float(str(ldl_raw).replace(",", "").strip())
        if chol == 0 and tgl == 0:
            return ""
        if chol >= 250 or tgl >= 250 or ldl >= 180:
            return "ไขมันในเลือดสูง"
        elif chol <= 200 and tgl <= 150:
            return "ปกติ"
        else:
            return "ไขมันในเลือดสูงเล็กน้อย"
    except:
        return ""

def lipids_advice(summary_text):
    if summary_text == "ไขมันในเลือดสูง":
        return (
            "ไขมันในเลือดสูง ควรลดอาหารที่มีไขมันอิ่มตัว เช่น ของทอด หนังสัตว์ "
            "ออกกำลังกายสม่ำเสมอ และพิจารณาพบแพทย์เพื่อตรวจติดตาม"
        )
    elif summary_text == "ไขมันในเลือดสูงเล็กน้อย":
        return (
            "ไขมันในเลือดสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภค ลดของมัน "
            "และออกกำลังกายเพื่อควบคุมระดับไขมัน"
        )
    return ""

def cbc_advice(hb, hct, wbc, plt, sex="ชาย"):
    advice_parts = []
    try:
        hb_val = float(hb)
        hb_ref = 13 if sex == "ชาย" else 12
        if hb_val < hb_ref:
            advice_parts.append("ระดับฮีโมโกลบินต่ำ ควรตรวจหาภาวะโลหิตจางและติดตามซ้ำ")
    except: pass
    try:
        hct_val = float(hct)
        hct_ref = 39 if sex == "ชาย" else 36
        if hct_val < hct_ref:
            advice_parts.append("ค่าฮีมาโตคริตต่ำ ควรตรวจหาภาวะเลือดจางและตรวจติดตาม")
    except: pass
    try:
        wbc_val = float(wbc)
        if wbc_val < 4000:
            advice_parts.append("เม็ดเลือดขาวต่ำ อาจเกิดจากภูมิคุ้มกันลด ควรติดตาม")
        elif wbc_val > 10000:
            advice_parts.append("เม็ดเลือดขาวสูง อาจมีการอักเสบ ติดเชื้อ หรือความผิดปกติ ควรพบแพทย์")
    except: pass
    try:
        plt_val = float(plt)
        if plt_val < 150000:
            advice_parts.append("เกล็ดเลือดต่ำ อาจมีภาวะเลือดออกง่าย ควรตรวจยืนยันซ้ำ")
        elif plt_val > 500000:
            advice_parts.append("เกล็ดเลือดสูง ควรพบแพทย์เพื่อตรวจหาสาเหตุเพิ่มเติม")
    except: pass
    return " ".join(advice_parts)

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
    
def interpret_alb(value):
    val = str(value).strip().lower()
    if val == "negative":
        return "ไม่พบ"
    elif val in ["trace", "1+", "2+"]:
        return "พบโปรตีนในปัสสาวะเล็กน้อย"
    elif val in ["3+", "4+"]:
        return "พบโปรตีนในปัสสาวะ"
    return "-"
    
def interpret_sugar(value):
    val = str(value).strip().lower()
    if val == "negative":
        return "ไม่พบ"
    elif val == "trace":
        return "พบน้ำตาลในปัสสาวะเล็กน้อย"
    elif val in ["1+", "2+", "3+", "4+", "5+", "6+"]:
        return "พบน้ำตาลในปัสาวะ"
    return "-"
    
def parse_range_or_number(val):
    val = val.replace("cell/hpf", "").replace("cells/hpf", "").replace("cell", "").strip().lower()
    try:
        if "-" in val:
            low, high = map(float, val.split("-"))
            return low, high
        else:
            num = float(val)
            return num, num
    except:
        return None, None
    
def interpret_rbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]:
        return "-"
    low, high = parse_range_or_number(val)
    if high is None:
        return value
    if high <= 2:
        return "ปกติ"
    elif high <= 5:
        return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
    else:
        return "พบเม็ดเลือดแดงในปัสสาวะ"
    
def interpret_wbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]:
        return "-"
    low, high = parse_range_or_number(val)
    if high is None:
        return value
    if high <= 5:
        return "ปกติ"
    elif high <= 10:
        return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    else:
        return "พบเม็ดเลือดขาวในปัสสาวะ"
    
def advice_urine(sex, alb, sugar, rbc, wbc):
    alb_t = interpret_alb(alb)
    sugar_t = interpret_sugar(sugar)
    rbc_t = interpret_rbc(rbc)
    wbc_t = interpret_wbc(wbc)
    
    if all(x in ["-", "ปกติ", "ไม่พบ", "พบโปรตีนในปัสสาวะเล็กน้อย", "พบน้ำตาลในปัสสาวะเล็กน้อย"]
                   for x in [alb_t, sugar_t, rbc_t, wbc_t]):
        return ""
    
    if "พบน้ำตาลในปัสสาวะ" in sugar_t and "เล็กน้อย" not in sugar_t:
        return "ควรลดการบริโภคน้ำตาล และตรวจระดับน้ำตาลในเลือดเพิ่มเติม"
    
    if sex == "หญิง" and "พบเม็ดเลือดแดง" in rbc_t and "ปกติ" in wbc_t:
        return "อาจมีปนเปื้อนจากประจำเดือน แนะนำให้ตรวจซ้ำ"
    
    if sex == "ชาย" and "พบเม็ดเลือดแดง" in rbc_t and "ปกติ" in wbc_t:
        return "พบเม็ดเลือดแดงในปัสสาวะ ควรตรวจทางเดินปัสสาวะเพิ่มเติม"
    
    if "พบเม็ดเลือดขาว" in wbc_t and "เล็กน้อย" not in wbc_t:
        return "อาจมีการอักเสบของระบบทางเดินปัสสาวะ แนะนำให้ตรวจซ้ำ"
    
    return "ควรตรวจปัสสาวะซ้ำเพื่อติดตามผล"
    
def is_urine_abnormal(test_name, value, normal_range):
    val = str(value or "").strip().lower()
    if val in ["", "-", "none", "nan", "null"]:
        return False
    
    if test_name == "กรด-ด่าง (pH)":
        try:
            return not (5.0 <= float(val) <= 8.0)
        except:
            return True
    
    if test_name == "ความถ่วงจำเพาะ (Sp.gr)":
        try:
            return not (1.003 <= float(val) <= 1.030)
        except:
            return True
    
    if test_name == "เม็ดเลือดแดง (RBC)":
        return "พบ" in interpret_rbc(val).lower()
    
    if test_name == "เม็ดเลือดขาว (WBC)":
        return "พบ" in interpret_wbc(val).lower()
    
    if test_name == "น้ำตาล (Sugar)":
        return val.lower() not in ["negative"]
    
    if test_name == "โปรตีน (Albumin)":
        return val.lower() not in ["negative", "trace"]
    
    if test_name == "สี (Colour)":
        return val not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"]
    
    return False

def interpret_stool_exam(val):
    if is_empty(val):
        return "ไม่ได้เข้ารับการตรวจ"
    val_lower = str(val).strip().lower()
    if val_lower == "normal":
        return "ไม่พบเม็ดเลือดขาวในอุจจาระ ถือว่าปกติ"
    elif "wbc" in val_lower or "เม็ดเลือดขาว" in val_lower:
        return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
    return val

def interpret_stool_cs(value):
    if is_empty(value):
        return "ไม่ได้เข้ารับการตรวจ"
    val_strip = str(value).strip()
    if "ไม่พบ" in val_strip or "ปกติ" in val_strip:
        return "ไม่พบการติดเชื้อ"
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"

def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val):
        return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def get_ekg_col_name(year):
    current_thai_year = datetime.now().year + 543
    return "EKG" if year == current_thai_year else f"EKG{str(year)[-2:]}"

def interpret_ekg(val):
    val = str(val or "").strip()
    if is_empty(val):
        return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def hepatitis_b_advice(hbsag, hbsab, hbcab):
    hbsag = hbsag.lower()
    hbsab = hbsab.lower()
    hbcab = hbcab.lower()
    
    if "positive" in hbsag:
        return "ติดเชื้อไวรัสตับอักเสบบี"
    elif "positive" in hbsab and "positive" not in hbsag:
        return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี"
    elif "positive" in hbcab and "positive" not in hbsab:
        return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน"
    elif all(x == "negative" for x in [hbsag, hbsab, hbcab]):
        return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ"

# --- HTML Rendering Functions ---

def render_section_header(title, subtitle=None):
    if subtitle:
        full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>"
    else:
        full_title = title

    return f"""
    <div style='
        background-color: #f0f2f6;
        color: #333;
        text-align: center;
        padding: 0.2rem 0.4rem;
        font-weight: bold;
        border-radius: 6px;
        margin-top: 1rem;
        margin-bottom: 0.4rem;
        font-size: 11px;
        border: 1px solid #ddd;
    '>
        {full_title}
    </div>
    """

def render_lab_table_html(title, subtitle, headers, rows, table_class="print-lab-table"):
    header_html = render_section_header(title, subtitle)
    
    html_content = f"{header_html}<table class='{table_class}'>"
    html_content += """
        <colgroup>
            <col style="width: 40%;">
            <col style="width: 20%;">
            <col style="width: 40%;">
        </colgroup>
    """
    html_content += "<thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i == 0 or i == 2 else "center"
        html_content += f"<th style='text-align: {align};'>{h}</th>"
    html_content += "</tr></thead><tbody>"
    
    for row in rows:
        is_abn = any(flag for _, flag in row)
        row_class = f"{table_class}-abn" if is_abn else ""
        
        html_content += f"<tr class='{row_class}'>"
        html_content += f"<td style='text-align: left;'>{row[0][0]}</td>"
        html_content += f"<td>{row[1][0]}</td>"
        html_content += f"<td style='text-align: left;'>{row[2][0]}</td>"
        html_content += f"</tr>"
    html_content += "</tbody></table>"
    return html_content


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
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; margin-bottom: 0.2rem; text-align: center;">
            <span><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</span>
            <span><b>อายุ:</b> {str(int(float(person.get('อายุ')))) if str(person.get('อายุ')).replace('.', '', 1).isdigit() else person.get('อายุ', '-')} ปี</span>
            <span><b>เพศ:</b> {person.get('เพศ', '-')}</span>
            <span><b>HN:</b> {str(int(float(person.get('HN')))) if str(person.get('HN')).replace('.', '', 1).isdigit() else person.get('HN', '-')}</span>
            <span><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</span>
        </div>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; margin-bottom: 0.5rem; text-align: center;">
            <span><b>น้ำหนัก:</b> {person.get("น้ำหนัก", "-")} กก.</span>
            <span><b>ส่วนสูง:</b> {person.get("ส่วนสูง", "-")} ซม.</span>
            <span><b>รอบเอว:</b> {person.get("รอบเอว", "-")} ซม.</span>
            <span><b>ความดันโลหิต:</b> {bp_full}</span>
            <span><b>ชีพจร:</b> {person.get("pulse", "-")} ครั้ง/นาที</span>
        </div>
        {f"<div style='margin-top: 0.5rem; text-align: center; border: 1px solid #ddd; padding: 3px; border-radius: 5px; background-color: #f8f9fa;'><b>คำแนะนำทั่วไป:</b> {summary_advice}</div>" if summary_advice else ""}
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
        ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70),
        ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44),
        ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9),
        ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9),
        ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3),
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
    <table style="width: 100%; border-collapse: collapse; page-break-inside: avoid;">
        <tr>
            <td style="width: 50%; vertical-align: top; padding-right: 5px;">{cbc_html}</td>
            <td style="width: 50%; vertical-align: top; padding-left: 5px;">{blood_html}</td>
        </tr>
    </table>
    """

def render_other_results_html(person, sex):
    # Urinalysis
    urine_data = [
        ("สี (Colour)", "Color", "Yellow, Pale Yellow"),
        ("น้ำตาล (Sugar)", "sugar", "Negative"),
        ("โปรตีน (Albumin)", "Alb", "Negative, trace"),
        ("กรด-ด่าง (pH)", "pH", "5.0 - 8.0"),
        ("ความถ่วงจำเพาะ (Sp.gr)", "Spgr", "1.003 - 1.030"),
        ("เม็ดเลือดแดง (RBC)", "RBC1", "0 - 2 cell/HPF"),
        ("เม็ดเลือดขาว (WBC)", "WBC1", "0 - 5 cell/HPF"),
        ("เซลล์เยื่อบุผิว (Squam.epit.)", "SQ-epi", "0 - 10 cell/HPF"),
        ("อื่นๆ", "ORTER", "-"),
    ]
    urine_rows = []
    for label, key, norm in urine_data:
        val = person.get(key, "-")
        is_abn = is_urine_abnormal(label, val, norm)
        urine_rows.append([(label, is_abn), (safe_value(val), is_abn), (norm, is_abn)])
    urine_html = render_lab_table_html("ผลการตรวจปัสสาวะ", "Urinalysis", ["การตรวจ", "ผลตรวจ", "ค่าปกติ"], urine_rows, "print-lab-table")

    # Urine Advice Box - SHOW IMMEDIATELY AFTER urine table, in left column
    urine_summary = advice_urine(sex, person.get("Alb", "-"), person.get("sugar", "-"), person.get("RBC1", "-"), person.get("WBC1", "-"))
    urine_advice_box_html = ""
    if urine_summary:
        urine_advice_box_html = f"""
        <div style="
            background-color: #fff8e1;
            width: 100%;
            box-sizing: border-box;
            margin-top: 1rem;
            border: 1px solid #ddd;
            border-radius: 8px;
            line-height: 1.5;
            font-size: 11px;
            padding: 0.4rem 1.5rem;
            ">
            <b>คำแนะนำผลตรวจปัสสาวะ:</b> {urine_summary}
        </div>
        """

    # Stool
    stool_exam_raw = person.get("Stool exam", "")
    stool_cs_raw = person.get("Stool C/S", "")
    stool_exam_text = interpret_stool_exam(stool_exam_raw)
    stool_cs_text = interpret_stool_cs(stool_cs_raw)
    stool_html = f"""
    {render_section_header("ผลตรวจอุจจาระ")}
    <table class="print-lab-table">
        <tr><td style="text-align: left; width: 40%;"><b>ผลตรวจอุจจาระทั่วไป</b></td><td style="text-align: left;">{stool_exam_text}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>ผลตรวจอุจจาระเพาะเชื้อ</b></td><td style="text-align: left;">{stool_cs_text}</td></tr>
    </table>
    """

    # Other tests
    year = person.get("Year", datetime.now().year + 543)
    cxr_result = interpret_cxr(person.get(f"CXR{str(year)[-2:]}" if year != (datetime.now().year+543) else "CXR", ""))
    ekg_result = interpret_ekg(person.get(get_ekg_col_name(year), ""))
    other_tests_html = f"""
    {render_section_header("ผลตรวจอื่นๆ")}
    <table class="print-lab-table">
        <tr><td style="text-align: left; width: 40%;"><b>ผลเอกซเรย์ (Chest X-ray)</b></td><td style="text-align: left;">{cxr_result}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>ผลคลื่นไฟฟ้าหัวใจ (EKG)</b></td><td style="text-align: left;">{ekg_result}</td></tr>
    </table>
    """

    # Hepatitis
    hep_a_raw = safe_text(person.get("Hepatitis A"))
    hbsag_raw = safe_text(person.get("HbsAg"))
    hbsab_raw = safe_text(person.get("HbsAb"))
    hbcab_raw = safe_text(person.get("HBcAB"))
    hep_b_advice = hepatitis_b_advice(hbsag_raw, hbsab_raw, hbcab_raw)

    hepatitis_html = f"""
    {render_section_header("ผลตรวจไวรัสตับอักเสบ")}
    <table class="print-lab-table">
        <tr><td style="text-align: left; width: 40%;"><b>ไวรัสตับอักเสบ เอ</b></td><td style="text-align: left;">{hep_a_raw}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>ไวรัสตับอักเสบ บี (HBsAg)</b></td><td style="text-align: left;">{hbsag_raw}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>ภูมิคุ้มกัน (HBsAb)</b></td><td style="text-align: left;">{hbsab_raw}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>การติดเชื้อ (HBcAb)</b></td><td style="text-align: left;">{hbcab_raw}</td></tr>
        <tr><td colspan="2" style="text-align: left; background-color: #f8f9fa;"><b>คำแนะนำ:</b> {hep_b_advice}</td></tr>
    </table>
    """

    # Doctor Suggestion - SHOW AFTER hepatitis, in right column
    doctor_suggestion = str(person.get("DOCTER suggest", "")).strip()
    if is_empty(doctor_suggestion):
        doctor_suggestion = "<i>ไม่มีคำแนะนำจากแพทย์</i>"
    doctor_suggestion_html = f"""
    <div style="background-color: #e8f5e9; color: #1b5e20; padding: 0.4rem 1.5rem; border-radius: 8px; line-height: 1.5; margin-top: 1rem; font-size: 11px; border: 1px solid #a5d6a7;">
        <b>สรุปความเห็นของแพทย์:</b><br> {doctor_suggestion}
    </div>
    """

    # RE-ARRANGE layout
    return f"""
    <table style="width: 100%; border-collapse: collapse; page-break-inside: avoid;">
        <tr>
            <td style="width: 50%; vertical-align: top; padding-right: 5px;">
                {urine_html}
                {urine_advice_box_html}
                {stool_html}
            </td>
            <td style="width: 50%; vertical-align: top; padding-left: 5px;">
                {other_tests_html}
                {hepatitis_html}
                {doctor_suggestion_html}
            </td>
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
    other_results_html = render_other_results_html(person, sex)

    # --- Blood Advice Box ---
    blood_advice_list = [
        kidney_advice_from_summary(kidney_summary_gfr_only(person.get("GFR", ""))),
        fbs_advice(person.get("FBS", "")),
        liver_advice(summarize_liver(person.get("ALP", ""), person.get("SGOT", ""), person.get("SGPT", ""))),
        uric_acid_advice(person.get("Uric Acid", "")),
        lipids_advice(summarize_lipids(person.get("CHOL", ""), person.get("TGL", ""), person.get("LDL", ""))),
        cbc_advice(person.get("Hb(%)", ""), person.get("HCT", ""), person.get("WBC (cumm)", ""), person.get("Plt (/mm)", ""), sex=sex),
    ]
    final_blood_advice_html = merge_final_advice_grouped(blood_advice_list)
    has_blood_advice = "ไม่พบคำแนะนำเพิ่มเติม" not in final_blood_advice_html
    bg_color_blood_advice = "#fff8e1" if has_blood_advice else "#e8f5e9"
    
    blood_advice_box_html = f"""
    <div style="background-color: {bg_color_blood_advice}; padding: 0.4rem 1.5rem; border-radius: 8px; line-height: 1.5; font-size: 11px; margin-top: 0.5rem; border: 1px solid #ddd;">
        {final_blood_advice_html}
    </div>
    """

    # --- Signature ---
    signature_html = """
    <div style="margin-top: 2rem; text-align: right; padding-right: 1rem; page-break-inside: avoid;">
        <div style="display: inline-block; text-align: center; width: 280px;">
            <div style="border-bottom: 1px dotted #333; margin-bottom: 0.4rem; width: 100%;"></div>
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
                font-size: 9px;
                margin: 10mm;
                color: #333;
            }}
            p {{ margin: 0.1rem 0; }}
            table {{ border-collapse: collapse; width: 100%; }}
            .print-lab-table td, .print-lab-table th {{
                padding: 1px 3px;
                border: 1px solid #ccc;
                text-align: center;
            }}
            .print-lab-table th {{ background-color: #f2f2f2; font-weight: bold; }}
            .print-lab-table-abn {{ background-color: #ffdddd !important; }}
            @media print {{
                body {{ -webkit-print-color-adjust: exact; margin: 0; }}
            }}
        </style>
    </head>
    <body>
        {header_html}
        {personal_info_html}
        {lab_section_html}
        {blood_advice_box_html}
        {other_results_html}
        {signature_html}
    </body>
    </html>
    """
    return final_html

# --- ฟังก์ชันใหม่สำหรับสร้างปุ่มพิมพ์ ---
def get_print_component_html(report_html_string):
    """
    รับสตริง HTML ของรายงานและส่งคืนคอมโพเนนต์ HTML ของ Streamlit
    ซึ่งมีปุ่ม "พิมพ์" และ JavaScript ที่จำเป็นในการพิมพ์เนื้อหารายงาน

    Args:
        report_html_string (str): เนื้อหา HTML ฉบับเต็มของรายงานที่จะพิมพ์

    Returns:
        str: สตริง HTML สำหรับใช้กับ st.components.v1.html()
    """
    # เข้ารหัส HTML ของรายงานเป็น Base64 เพื่อให้สามารถฝังใน JavaScript ได้อย่างปลอดภัย
    # วิธีนี้ช่วยจัดการกับอักขระพิเศษ เช่น เครื่องหมายคำพูดหรือการขึ้นบรรทัดใหม่
    encoded_html = base64.b64encode(report_html_string.encode()).decode()

    # คอมโพเนนต์ HTML ประกอบด้วยปุ่มและฟังก์ชัน JavaScript
    # JavaScript จะสร้าง iframe ที่ซ่อนอยู่ เขียน HTML ที่ถอดรหัสแล้วลงไป
    # จากนั้นเรียกใช้หน้าต่างโต้ตอบการพิมพ์บน iframe นั้น
    component_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            /* จัดสไตล์ปุ่มพิมพ์ */
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
            .print-button {{
                font-family: 'Sarabun', sans-serif;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 8px;
                border: none;
                background-color: #007bff;
                color: white;
                cursor: pointer;
                transition: background-color 0.2s;
                display: inline-flex;
                align-items: center;
                gap: 8px; /* ระยะห่างระหว่างไอคอนกับข้อความ */
            }}
            .print-button:hover {{
                background-color: #0056b3;
            }}
        </style>
    </head>
    <body>
        <button class="print-button" onclick="printReport()">
            🖨️ พิมพ์รายงาน
        </button>

        <script type="text/javascript">
            function printReport() {{
                // 1. ถอดรหัส HTML จาก Base64
                const decodedHtml = atob('{encoded_html}');

                // 2. ค้นหาและลบ iframe เก่า (ถ้ามี) เพื่อป้องกันการซ้ำซ้อน
                const oldIframe = document.getElementById('print-iframe');
                if (oldIframe) {{
                    oldIframe.remove();
                }}

                // 3. สร้าง iframe ใหม่
                const iframe = document.createElement('iframe');
                iframe.id = 'print-iframe';
                iframe.style.display = 'none'; // ซ่อน iframe ไม่ให้แสดงบนหน้าจอ
                document.body.appendChild(iframe); // เพิ่ม iframe เข้าไปใน DOM

                // 4. เขียนเนื้อหา HTML ที่ถอดรหัสแล้วลงใน iframe
                iframe.contentDocument.open();
                iframe.contentDocument.write(decodedHtml);
                iframe.contentDocument.close();

                // 5. ตั้งค่า event listener 'onload' บน contentWindow ของ iframe
                // เพื่อให้แน่ใจว่าทรัพยากรทั้งหมด (เช่น ฟอนต์) โหลดเสร็จแล้ว
                iframe.contentWindow.onload = function() {{
                    // 6. เมื่อโหลดเสร็จ ให้เรียกใช้ฟังก์ชันพิมพ์
                    iframe.contentWindow.focus(); // Focus ที่ iframe (สำคัญสำหรับบางเบราว์เซอร์)
                    iframe.contentWindow.print(); // เรียกหน้าต่างพิมพ์
                    
                    // 7. ลบ iframe ออกหลังจากที่ผู้ใช้ปิดหน้าต่างพิมพ์แล้ว
                    // ใช้ setTimeout เพื่อให้มีเวลาเล็กน้อยก่อนที่จะลบ
                    setTimeout(() => {{
                        document.body.removeChild(iframe);
                    }}, 1000);
                }};
            }}
        </script>
    </body>
    </html>
    """
    return component_html
