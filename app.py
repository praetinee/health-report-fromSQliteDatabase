import streamlit as st
import sqlite3
import requests
import pandas as pd
import io
import tempfile
import html  # Used for html.escape()
import numpy as np
from collections import OrderedDict
from datetime import datetime
import re

def is_empty(val):
    return str(val).strip().lower() in ["", "-", "none", "nan", "null"]

# --- Global Helper Functions: START ---
# Moved to global scope to prevent NameError

# Function to normalize and convert Thai dates
def normalize_thai_date(date_str):
    if is_empty(date_str):
        return "-" # Or "ไม่ระบุ"
    
    s = str(date_str).strip()

    # Aggressive initial cleaning of punctuation and specific text patterns
    s_cleaned_punc_temp = s.replace('.', '').replace('พ.ศ.', '').replace('พศ.', '').strip()
    s_cleaned_punc_temp = s_cleaned_punc_temp.replace('-', '').replace('/', '').replace(' ', '').strip() # Remove all spaces/hyphens/slashes/dots temporarily for parsing
    
    # Handle specific non-date strings after basic cleaning
    if str(date_str).strip().lower() in ["ไม่ตรวจ", "นัดที่หลัง", "ไม่ได้เข้ารับการตรวจ", ""]:
        return str(date_str).strip() # Return original non-date string if matched

    # Define Thai month mappings (local to this function for clarity)
    thai_months = {
        1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน",
        5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม",
        9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"
    }
    thai_month_abbr_to_num = {
        "ม.ค.": 1, "ม.ค": 1, "มกราคม": 1,
        "ก.พ.": 2, "ก.พ": 2, "กพ": 2, "กุมภาพันธ์": 2,
        "มี.ค.": 3, "มี.ค": 3, "มีนาคม": 3,
        "เม.ย.": 4, "เม.ย": 4, "เมษายน": 4,
        "พ.ค.": 5, "พ.ค": 5, "พฤษภาคม": 5,
        "มิ.ย.": 6, "มิ.ย": 6, "มิถุนายน": 6,
        "ก.ค.": 7, "ก.ค": 7, "กรกฎาคม": 7,
        "ส.ค.": 8, "ส.ค": 8, "สิงหาคม": 8,
        "ก.ย.": 9, "ก.ย": 9, "กันยายน": 9,
        "ต.ค.": 10, "ต.ค": 10, "ตุลาคม": 10,
        "พ.ย.": 11, "พ.ย": 11, "พฤศจิกายน": 11,
        "ธ.ค.": 12, "ธ.ค": 12, "ธันวาคม": 12
    }

    # --- Step 1: Try to parse with pandas (most robust for various formats with separators) ---
    try:
        # Use the original string for pandas.to_datetime first, it's very robust with separators.
        # errors='coerce' will turn unparsable dates into NaT (Not a Time).
        parsed_dt = pd.to_datetime(s, dayfirst=True, errors='coerce')

        if pd.notna(parsed_dt): # Check if pandas successfully parsed it
            # Adjust for Buddhist Era year interpretation if needed
            if parsed_dt.year > datetime.now().year + 50: # Heuristic for BE year
                parsed_dt = parsed_dt.replace(year=parsed_dt.year - 543)
            
            # Reconstruct the string with guaranteed space
            return " ".join([str(parsed_dt.day), thai_months[parsed_dt.month], str(parsed_dt.year + 543)])
    except Exception:
        pass # Fall through to regex attempts if pandas fails

    # --- Step 2: Try specific regex patterns on the aggressively cleaned string ('s_cleaned_punc') ---
    # These patterns are for cases where pandas might fail due to lack of separators, but structure is fixed.

    # Regex for DDMonthNameYYYY without explicit spaces (because s_cleaned_punc has no spaces)
    # Example: "5กุมภาพันธ์2568"
    match_thai_text_date_no_space = re.match(r'^(?P<day1>\d{1,2})(?P<month_str>[ก-ฮ]+)(?P<year>\d{4})$', s_cleaned_punc_temp)
    if match_thai_text_date_no_space:
        try:
            day = int(match_thai_text_date_no_space.group('day1'))
            month_str = match_thai_text_date_no_space.group('month_str')
            year = int(match_thai_text_date_no_space.group('year'))
            
            month_num = thai_month_abbr_to_num.get(month_str)
            if month_num:
                dt = datetime(year - 543, month_num, day)
                return " ".join([str(day), thai_months[dt.month], str(year)])
        except (ValueError, KeyError):
            pass

    # Fallback if nothing else works
    return s # Final fallback, returns the original string 's' if all parsing fails.

def interpret_bp(sbp_raw, dbp_raw):
    """Interprets blood pressure values and returns a descriptive string."""
    try:
        sbp = float(str(sbp_raw).strip())
        dbp = float(str(dbp_raw).strip())

        if sbp < 90 or dbp < 60:
            return "ความดันโลหิตต่ำ"
        elif sbp < 120 and dbp < 80:
            return "ปกติ"
        elif (sbp >= 120 and sbp <= 129) and dbp < 80:
            return "ความดันโลหิตสูงเล็กน้อย"  # Elevated
        elif (sbp >= 130 and sbp <= 139) or (dbp >= 80 and dbp <= 89):
            return "ความดันโลหิตสูง (ระยะที่ 1)"  # Stage 1 Hypertension
        elif sbp >= 140 or dbp >= 90:
            return "ความดันโลหิตสูง (ระยะที่ 2)"  # Stage 2 Hypertension
        else:
            return "ผิดปกติ"
    except (ValueError, TypeError):
        return "-"

def get_bmi_category(bmi_val):
    if bmi_val is None:
        return ""
    if bmi_val < 18.5:
        return "น้ำหนักน้อย"
    elif 18.5 <= bmi_val < 23:
        return "น้ำหนักปกติ"
    elif 23 <= bmi_val < 25:
        return "น้ำหนักเกิน"
    elif 25 <= bmi_val < 30:
        return "โรคอ้วนระดับ 1"
    else:
        return "โรคอ้วนระดับ 2"

def get_waist_category(waist_val, sex):
    try:
        waist_cm = float(str(waist_val).strip())
        if sex == "ชาย":
            if waist_cm >= 90:
                return "มีภาวะอ้วนลงพุง"
        elif sex == "หญิง":
            if waist_cm >= 80:
                return "มีภาวะอ้วนลงพุง"
        return ""
    except (ValueError, TypeError):
        return ""

def combined_health_advice(bmi_val, sbp_raw, dbp_raw, waist_raw=None, sex="ไม่ระบุ"):
    """
    Provides combined health advice based on BMI, Blood Pressure, and Waist Circumference.
    """
    advice_parts = []

    # BMI Advice
    bmi_category = get_bmi_category(bmi_val)
    if bmi_category:
        if bmi_category == "น้ำหนักน้อย":
            advice_parts.append("น้ำหนักน้อยกว่าเกณฑ์: ควรเพิ่มน้ำหนักโดยการรับประทานอาหารที่มีประโยชน์และออกกำลังกายอย่างเหมาะสม")
        elif bmi_category == "น้ำหนักเกิน":
            advice_parts.append("น้ำหนักเกินเกณฑ์: ควรควบคุมน้ำหนักเพื่อสุขภาพที่ดี")
        elif bmi_category.startswith("โรคอ้วน"):
            advice_parts.append(f"มีภาวะ{bmi_category}: ควรปรึกษาแพทย์หรือนักโภชนาการเพื่อวางแผนลดน้ำหนัก")
        # No advice for "น้ำหนักปกติ"

    # Blood Pressure Advice
    bp_desc = interpret_bp(sbp_raw, dbp_raw)
    if "ความดันโลหิตต่ำ" in bp_desc:
        advice_parts.append("ความดันโลหิตต่ำ: ควรดื่มน้ำให้เพียงพอ, หลีกเลี่ยงการเปลี่ยนท่าทางกะทันหัน")
    elif "สูง" in bp_desc:
        advice_parts.append("ความดันโลหิตสูง: ควรควบคุมอาหารลดเค็ม, ออกกำลังกายสม่ำเสมอ, พักผ่อนให้เพียงพอ และพบแพทย์เพื่อติดตามอาการ")
    
    # Waist circumference Advice
    if waist_raw is not None:
        waist_category = get_waist_category(waist_raw, sex)
        if waist_category == "มีภาวะอ้วนลงพุง":
            advice_parts.append("รอบเอวเกินเกณฑ์: มีภาวะอ้วนลงพุง ควรลดไขมันหน้าท้องด้วยการออกกำลังกายแบบคาร์ดิโอและควบคุมอาหาร")

    if not advice_parts:
        return "สุขภาพโดยรวมอยู่ในเกณฑ์ปกติ"
    else:
        return " ".join(advice_parts)

def render_section_header(title, subtitle=None):
    if subtitle:
        full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>"
    else:
        full_title = title

    return f"""
    <div style='
        background-color: #1b5e20;
        color: white;
        text-align: center;
        padding: 1rem 0.5rem;
        font-size: 18px; /* Adjusted font size */
        font-weight: bold;
        font-family: "Sarabun", sans-serif;
        border-radius: 8px;
        margin-top: 2rem;
        margin-bottom: 1rem;
    '>
        {full_title}
    </div>
    """

def render_lab_table_html(title, subtitle, headers, rows, table_class="lab-table"):
    """
    Generates HTML for lab result tables (CBC, Blood Chemistry).
    Uses the same styling and abnormal highlighting logic.
    """
    style = f"""
    <style>
        .{table_class}-container {{
            background-color: var(--background-color);
            margin-top: 1rem;
        }}
        .{table_class} {{
            width: 100%;
            border-collapse: collapse;
            font-size: 18px; /* Adjusted font size */
            font-family: "Sarabun", sans-serif;
            color: var(--text-color);
            table-layout: fixed; /* Ensures column widths are respected */
        }}
        .{table_class} thead th {{
            background-color: var(--secondary-background-color);
            color: var(--text-color);
            padding: 2px 2px; /* Adjusted padding to make columns closer */
            text-align: center;
            font-weight: bold;
            border: 1px solid transparent;
        }}
        .{table_class} td {{
            padding: 2px 2px; /* Adjusted padding to make columns closer */
            border: 1px solid transparent;
            text-align: center;
            color: var(--text-color);
        }}
        .{table_class}-abn {{
            background-color: rgba(255, 64, 64, 0.25); /* Translucent red */
        }}
        .{table_class}-row {{
            background-color: rgba(255,255,255,0.02);
        }}
    </style>
    """
    
    header_html = render_section_header(title, subtitle)
    
    html_content = f"{style}{header_html}<div class='{table_class}-container'><table class='{table_class}'>"
    # Add colgroup for explicit column widths (equal distribution for 3 columns)
    html_content += """
        <colgroup>
            <col style="width: 33.33%;"> <col style="width: 33.33%;"> <col style="width: 33.33%;"> </colgroup>
    """
    html_content += "<thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i == 0 else ("left" if i == 2 else "center") # 'การตรวจ' and 'ค่าปกติ' left-aligned, 'ผล' center-aligned
        html_content += f"<th style='text-align: {align};'>{h}</th>"
    html_content += "</tr></thead><tbody>"
    
    for row in rows:
        # Check if any item in the row tuple indicates abnormality
        is_abn = False
        for item_tuple in row:
            if len(item_tuple) > 1 and item_tuple[1]: # Check if the second element (boolean flag) is True
                is_abn = True
                break
        
        row_class = f"{table_class}-abn" if is_abn else f"{table_class}-row"
        
        html_content += f"<tr>"
        # Access the first element of each tuple for display
        html_content += f"<td class='{row_class}' style='text-align: left;'>{row[0][0]}</td>"
        html_content += f"<td class='{row_class}'>{row[1][0]}</td>"
        html_content += f"<td class='{row_class}' style='text-align: left;'>{row[2][0]}</td>"
        html_content += f"</tr>"
    html_content += "</tbody></table></div>"
    return html_content

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
        alp = float(str(alp_val).replace(",", "").strip())
        sgot = float(str(sgot_val).replace(",", "").strip())
        sgpt = float(str(sgpt_val).replace(",", "").strip())
        if alp == 0 or sgot == 0 or sgpt == 0:
            return "-"
        if alp > 120 or sgot > 36 or sgpt > 40:
            return "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย"
        return "ปกติ"
    except:
        return "-"

def liver_advice(summary_text):
    if summary_text == "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย":
        return "ควรลดอาหารไขมันสูงและตรวจติดตามการทำงานของตับซ้ำ"
    elif summary_text == "ปกติ":
        return ""
    return "-"

def uric_acid_advice(value_raw):
    try:
        value = float(str(value_raw).replace(",", "").strip())
        if value > 7.2:
            return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
        return ""
    except:
        return "-"

def summarize_lipids(chol_raw, tgl_raw, ldl_raw):
    try:
        chol = float(str(chol_raw).replace(",", "").strip())
        tgl = float(str(tgl_raw).replace(",", "").strip())
        ldl = float(str(ldl_raw).replace(",", "").strip())
        if chol == 0 and tgl == 0 and ldl == 0:
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
        hb_val = float(str(hb).replace(",", "").strip())
        hb_ref = 13 if sex == "ชาย" else 12
        if hb_val < hb_ref:
            advice_parts.append("ระดับฮีโมโกลบินต่ำ ควรตรวจหาภาวะเลือดจางและตรวจติดตาม")
    except (ValueError, TypeError):
        pass

    try:
        hct_val = float(str(hct).replace(",", "").strip())
        hct_ref = 39 if sex == "ชาย" else 36
        if hct_val < hct_ref:
            advice_parts.append("ค่าฮีมาโตคริตต่ำ ควรตรวจหาภาวะเลือดจางและตรวจติดตาม")
    except (ValueError, TypeError):
        pass

    try:
        wbc_val = float(str(wbc).replace(",", "").strip())
        if wbc_val > 0 and wbc_val < 4000:
            advice_parts.append("เม็ดเลือดขาวต่ำ อาจเกิดจากภูมิคุ้มกันลด ควรติดตาม")
        elif wbc_val > 10000:
            advice_parts.append("เม็ดเลือดขาวสูง อาจมีการอักเสบ ติดเชื้อ หรือความผิดปกติ ควรพบแพทย์")
    except (ValueError, TypeError):
        pass

    try:
        plt_val = float(str(plt).replace(",", "").strip())
        if plt_val > 0 and plt_val < 150000:
            advice_parts.append("เกล็ดเลือดต่ำ อาจมีภาวะเลือดออกง่าย ควรตรวจยืนยันซ้ำ")
        elif plt_val > 500000:
            advice_parts.append("เกล็ดเลือดสูง ควรพบแพทย์เพื่อตรวจหาสาเหตุเพิ่มเติม")
    except (ValueError, TypeError):
        pass

    return " ".join(advice_parts)

def safe_text(value):
    """Safely converts a value to string, handling None/NaN, and HTML escapes it."""
    if is_empty(value):
        return "-"
    return html.escape(str(value).strip())

def normalize_date_for_display(date_str):
    """
    Normalizes and formats a date string for display.
    This is a simplified version; you might want to use normalize_thai_date if it's a full date.
    """
    if is_empty(date_str):
        return "-"
    return str(date_str).strip()

def interpret_urine_result(val):
    if is_empty(val):
        return "-", False, ""
    
    val_str = str(val).strip().lower()
    is_abnormal = False
    notes = ""

    if "pos" in val_str or "พบ" in val_str:
        is_abnormal = True
        notes = "ผิดปกติ"
    elif "neg" in val_str or "ไม่พบ" in val_str or "normal" in val_str or "ปกติ" in val_str:
        is_abnormal = False
        notes = "ปกติ"
    else:
        notes = "ปกติ" # Default to normal if not clearly positive
    
    return safe_text(val), is_abnormal, notes


def render_urine_section(person_data, sex, selected_year):
    st.markdown(render_section_header("ผลตรวจปัสสาวะ", "Urinalysis"), unsafe_allow_html=True)
    
    ua_config = [
        ("สี (Color)", "Color", "เหลืองใส"),
        ("ความขุ่น (Turbidity)", "Turbidity", "ใส"),
        ("ปฏิกิริยา (pH)", "PH", "4.8 - 7.5"),
        ("ความถ่วงจำเพาะ (S.G.)", "S.G.", "1.003 - 1.030"),
        ("น้ำตาล (Sugar)", "Sugar", "Negative"),
        ("โปรตีน (Albumin)", "Albumin", "Negative"),
        ("เม็ดเลือดขาว (WBC)", "WBC (UA)", "0-5 /HPF"),
        ("เม็ดเลือดแดง (RBC)", "RBC (UA)", "0-5 /HPF"),
        ("เซลล์เยื่อบุผิว (Epithelial Cell)", "Epithelial Cell", "ไม่พบ"),
        ("Cast", "Cast", "ไม่พบ"),
        ("Crystals", "Crystals", "ไม่พบ"),
        ("แบคทีเรีย (Bacteria)", "Bacteria", "ไม่พบ"),
        ("ยีสต์ (Yeast)", "Yeast", "ไม่พบ"),
    ]

    urine_rows = []
    # For urine, we typically don't use flag function with numeric low/high.
    # Instead, we interpret text results and mark abnormality.
    for label, col, normal_range in ua_config:
        raw_val = person_data.get(col, "")
        display_val, is_abnormal, _ = interpret_urine_result(raw_val) # Interpret to get display value and abnormality
        urine_rows.append([(label, is_abnormal), (display_val, is_abnormal), (normal_range, is_abnormal)])

    # Reuse render_lab_table_html for consistent styling
    st.markdown(render_lab_table_html("ผลตรวจปัสสาวะ", "Urinalysis", ["การตรวจ", "ผล", "ค่าปกติ"], urine_rows, table_class="urine-table"), unsafe_allow_html=True)

    # Simplified advice for urinalysis - extend as needed
    ua_wbc_raw = person_data.get("WBC (UA)", "")
    ua_rbc_raw = person_data.get("RBC (UA)", "")
    ua_sugar_raw = person_data.get("Sugar", "")
    ua_albumin_raw = person_data.get("Albumin", "")

    urine_advice_parts = []

    if "pos" in str(ua_sugar_raw).lower() or "พบ" in str(ua_sugar_raw).lower():
        urine_advice_parts.append("ตรวจพบน้ำตาลในปัสสาวะ ควรปรึกษาแพทย์เพื่อตรวจเบาหวานเพิ่มเติม")
    if "pos" in str(ua_albumin_raw).lower() or "พบ" in str(ua_albumin_raw).lower():
        urine_advice_parts.append("ตรวจพบโปรตีนในปัสสาวะ อาจบ่งชี้ถึงความผิดปกติของไต ควรปรึกษาแพทย์")
    if "pos" in str(ua_wbc_raw).lower() or "พบ" in str(ua_wbc_raw).lower() and not any(char.isdigit() for char in str(ua_wbc_raw)):
         urine_advice_parts.append("ตรวจพบเม็ดเลือดขาวในปัสสาวะ อาจมีการติดเชื้อทางเดินปัสสาวะ ควรปรึกษาแพทย์")
    if "pos" in str(ua_rbc_raw).lower() or "พบ" in str(ua_rbc_raw).lower() and not any(char.isdigit() for char in str(ua_rbc_raw)):
        urine_advice_parts.append("ตรวจพบเม็ดเลือดแดงในปัสสาวะ ควรปรึกษาแพทย์เพื่อหาสาเหตุ")

    if urine_advice_parts:
        final_urine_advice = " ".join(urine_advice_parts)
        bg_color = "rgba(255, 255, 0, 0.2)" # Yellow if advice
    else:
        final_urine_advice = "ผลตรวจปัสสาวะปกติ"
        bg_color = "rgba(57, 255, 20, 0.2)" # Green if normal

    st.markdown(f"""
        <div style='
            background-color: {bg_color};
            padding: 1rem;
            border-radius: 6px;
            font-size: 18px; /* Adjusted font size */
            margin-top: 1rem;
            margin-bottom: 1rem;
            line-height: 1.6;
            color: var(--text-color);
            font-family: "Sarabun", sans-serif;
        '>
            <b>คำแนะนำ:</b> {final_urine_advice}
        </div>
        """, unsafe_allow_html=True)

def interpret_stool_exam(stool_exam_raw):
    """Interprets stool examination result."""
    if is_empty(stool_exam_raw):
        return "ไม่มีข้อมูล"
    s = str(stool_exam_raw).strip()
    if "ไม่พบ" in s or "ปกติ" in s or "negative" in s.lower():
        return "ปกติ"
    return s # Return as is if it contains other values

def interpret_stool_cs(stool_cs_raw):
    """Interprets stool C/S result."""
    if is_empty(stool_cs_raw):
        return "ไม่มีข้อมูล"
    s = str(stool_cs_raw).strip()
    if "ไม่พบ" in s or "ปกติ" in s or "negative" in s.lower():
        return "ปกติ"
    return s # Return as is if it contains other values

def render_stool_html_table(exam_text, cs_text):
    """Generates HTML table for stool examination."""
    # Determine if any part is abnormal to apply a highlight to the table if needed
    is_abnormal_exam = ("ปกติ" not in exam_text) and ("ไม่มีข้อมูล" not in exam_text)
    is_abnormal_cs = ("ปกติ" not in cs_text) and ("ไม่มีข้อมูล" not in cs_text)
    
    # Decide table background based on abnormality
    table_bg_color = "rgba(255, 64, 64, 0.1)" if is_abnormal_exam or is_abnormal_cs else "rgba(255,255,255,0.02)"

    return f"""
    <div style='
        background-color: {table_bg_color};
        margin-top: 1rem;
        padding: 0.5rem; /* Reduced padding */
        border-radius: 6px;
        font-family: "Sarabun", sans-serif;
    '>
        <table style='
            width: 100%;
            border-collapse: collapse;
            font-size: 18px; /* Adjusted font size */
            color: var(--text-color);
        '>
            <thead>
                <tr>
                    <th style="padding: 2px 2px; text-align: left; border-bottom: 1px solid var(--secondary-background-color);">การตรวจ</th>
                    <th style="padding: 2px 2px; text-align: left; border-bottom: 1px solid var(--secondary-background-color);">ผล</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding: 2px 2px; text-align: left;">Stool exam</td>
                    <td style="padding: 2px 2px; text-align: left;">{exam_text}</td>
                </tr>
                <tr>
                    <td style="padding: 2px 2px; text-align: left;">Stool C/S</td>
                    <td style="padding: 2px 2px; text-align: left;">{cs_text}</td>
                </tr>
            </tbody>
        </table>
    </div>
    """

def interpret_cxr(cxr_raw):
    """Interprets Chest X-ray result."""
    if is_empty(cxr_raw):
        return "ไม่มีข้อมูล"
    s = str(cxr_raw).strip().lower()
    if "normal" in s or "ปกติ" in s or "no significant findings" in s:
        return "ผลปกติ"
    return s.capitalize() # Return as is, capitalizing the first letter.

def get_ekg_col_name(selected_year_int):
    """Determines the correct EKG column name based on the selected year."""
    if selected_year_int == 2568:
        return "EKG"
    else:
        return f"EKG{str(selected_year_int)[-2:]}"

def interpret_ekg(ekg_raw):
    """Interprets EKG result."""
    if is_empty(ekg_raw):
        return "ไม่มีข้อมูล"
    s = str(ekg_raw).strip().lower()
    if "normal" in s or "ปกติ" in s or "within normal limits" in s:
        return "ผลปกติ"
    return s.capitalize() # Return as is, capitalizing the first letter.

def hepatitis_b_advice(hbsag_raw, hbsab_raw, hbcab_raw):
    """Provides advice based on Hepatitis B markers."""
    hbsag = str(hbsag_raw).strip().lower()
    hbsab = str(hbsab_raw).strip().lower()
    hbcab = str(hbcab_raw).strip().lower()

    if hbsag == "positive" or hbsag == "pos" or "พบ" in hbsag:
        return "ตรวจพบเชื้อไวรัสตับอักเสบบี ควรพบแพทย์เพื่อประเมินและวางแผนการรักษา"
    elif (hbsab == "positive" or hbsab == "pos" or "พบ" in hbsab) and (hbcab == "negative" or hbcab == "neg" or "ไม่พบ" in hbcab):
        return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี (จากการฉีดวัคซีน)"
    elif (hbsab == "positive" or hbsab == "pos" or "พบ" in hbsab) and (hbcab == "positive" or hbcab == "pos" or "พบ" in hbcab):
        return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี (จากการติดเชื้อในอดีต)"
    elif (hbsag == "negative" or hbsag == "neg" or "ไม่พบ" in hbsag) and (hbsab == "negative" or hbsab == "neg" or "ไม่พบ" in hbsab) and (hbcab == "negative" or hbcab == "neg" or "ไม่พบ" in hbcab):
        return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน"
    else:
        return "ไม่มีข้อมูลที่ชัดเจน ควรปรึกษาแพทย์เพื่อประเมินผลตรวจไวรัสตับอักเสบบีเพิ่มเติม"

def merge_final_advice_grouped(advice_list):
    """
    Combines a list of advice strings into a single HTML formatted string,
    removing duplicates and empty strings, and handling the "no advice" case.
    """
    cleaned_advice = [item.strip() for item in advice_list if item.strip() != ""]
    unique_advice = list(OrderedDict.fromkeys(cleaned_advice)) # Preserve order while making unique

    if not unique_advice:
        return "ไม่พบคำแนะนำเพิ่มเติมในส่วนผลตรวจทางห้องปฏิบัติการ"
    else:
        # Group related advice, or just list them
        # For simplicity, let's just list them as bullet points
        formatted_advice = ""
        for i, advice in enumerate(unique_advice):
            formatted_advice += f"• {advice}<br>"
        return formatted_advice


@st.cache_data(ttl=600)
def load_sqlite_data():
    try:
        file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url)
        response.raise_for_status()

        # Save file to temp file for sqlite3 to read
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        tmp.write(response.content)
        tmp.flush()
        tmp.close()

        conn = sqlite3.connect(tmp.name)
        df = pd.read_sql("SELECT * FROM health_data", conn)
        conn.close()

        # Strip & convert essential data types
        df.columns = df.columns.str.strip()
        df['เลขบัตรประชาชน'] = df['เลขบัตรประชาชน'].astype(str).str.strip()
        # HN handling as per the "old code" for now (str(int(float(x))))
        # This converts "0000" to "0" and numerical HNs to strings without leading zeros
        df['HN'] = df['HN'].apply(lambda x: str(int(float(x))) if pd.notna(x) else "").str.strip()
        df['ชื่อ-สกุล'] = df['ชื่อ-สกุล'].astype(str).str.strip()
        df['Year'] = df['Year'].astype(int)

        # Create HN_SEARCHABLE for more lenient numerical HN matching
        # This function cleans HN to its pure digit form (e.g., "007" -> "7", "HN123" -> "123")
        def clean_hn_for_df_search(hn_value):
            if is_empty(hn_value):
                return ""
            s = str(hn_value)
            digits_only = re.sub(r'\D', '', s) # Keep only digits
            if digits_only:
                try:
                    return str(int(digits_only)) # Convert to int and back to str to remove leading zeros
                except ValueError:
                    return "" # Should not happen if digits_only is not empty
            return "" # If no digits are found (e.g., "ABC"), it becomes empty.
        
        df['HN_SEARCHABLE'] = df['HN'].apply(clean_hn_for_df_search)

        # Apply date normalization AFTER initial data loading and cleaning
        df['วันที่ตรวจ'] = df['วันที่ตรวจ'].apply(normalize_thai_date)

        # Adjust missing values / replace - or None
        df.replace(["-", "None", None], pd.NA, inplace=True)

        return df
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        st.stop()

df = load_sqlite_data()

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

# ==================== UI SEARCH FORM ====================
st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
st.markdown("""
    <style>
    /* Import Sarabun font from Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');

    /* Apply Sarabun font globally */
    html, body, [class*="st-emotion"], [class*="css-"] { /* Target Streamlit elements */
        font-family: "Sarabun", sans-serif;
    }

    /* Override specific elements if needed, for example the main text */
    div.stMarkdown, div.stText, p {
        font-family: "Sarabun", sans-serif;
    }

    /* Adjust font for inputs/select boxes if they don't inherit automatically */
    .stTextInput > div > div > input, .stSelectbox > div > div > div > div {
        font-family: "Sarabun", sans-serif;
    }


    /* Original scrollbar CSS */
    div.stMarkdown {
        overflow: visible !important;
    }

    section.main > div {
        overflow-y: visible !important;
    }

    [data-testid="stVerticalBlock"] {
        overflow: visible !important;
    }

    ::-webkit-scrollbar {
        width: 0px;
        background: transparent;
    }

    div[style*="overflow: auto"] {
        overflow: visible !important;
    }

    div[style*="overflow-x: auto"] {
        overflow-x: visible !important;
    }

    div[style*="overflow-y: auto"] {
        overflow-y: visible !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center; font-family: \"Sarabun\", sans-serif;'>ระบบรายงานผลตรวจสุขภาพ</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray; font-family: \"Sarabun\", sans-serif;'>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม รพ.สันทราย -</h4>", unsafe_allow_html=True)

# Main search form moved to sidebar
with st.sidebar.form("search_form_sidebar"):
    st.markdown("<h3>ค้นหาข้อมูลผู้ป่วย</h3>", unsafe_allow_html=True)
    search_query = st.text_input("กรอก HN หรือ ชื่อ-สกุล")
    submitted_sidebar = st.form_submit_button("ค้นหา")

if submitted_sidebar:
    # Clear previous results immediately upon new search
    st.session_state.pop("search_result", None)
    st.session_state.pop("person_row", None)
    st.session_state.pop("selected_row_found", None)
    st.session_state.pop("selected_year_from_sidebar", None) # Clear previously selected year
    st.session_state.pop("selected_exam_date_from_sidebar", None) # Clear previously selected exam date

    query_df = df.copy()

    search_term = search_query.strip() # Clean user input right away

    # Only proceed with filtering if search_term is not empty
    if search_term:
        # Check if the query is purely numeric (potential HN)
        if search_term.isdigit():
            # Clean user input for HN search (digits only, no leading zeros)
            hn_search_value = str(int(search_term))
            query_df = query_df[query_df["HN_SEARCHABLE"] == hn_search_value]
        else:
            # Assume it's a full name if not purely numeric
            query_df = query_df[query_df["ชื่อ-สกุล"].str.strip() == search_term]
        
        if query_df.empty:
            st.sidebar.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบข้อมูลที่กรอกอีกครั้ง")
            # search_result remains None, so nothing will display, which is correct.
        else:
            st.session_state["search_result"] = query_df
            
            # --- NEW: Immediately select the first available person/date after successful search ---
            # This ensures person_row is set for display on the very next rerun
            first_available_year = sorted(query_df["Year"].dropna().unique().astype(int), reverse=True)[0]
            
            first_person_year_df = query_df[
                (query_df["Year"] == first_available_year) &
                (query_df["HN"] == query_df.iloc[0]["HN"]) # Use HN of the first result
            ].drop_duplicates(subset=["HN", "วันที่ตรวจ"]).sort_values(by="วันที่ตรวจ", key=lambda x: pd.to_datetime(x, errors='coerce', dayfirst=True), ascending=False)
            
            if not first_person_year_df.empty:
                st.session_state["person_row"] = first_person_year_df.iloc[0].to_dict()
                st.session_state["selected_row_found"] = True
                # Also set the initial selected year for the selectbox
                st.session_state["selected_year_from_sidebar"] = first_available_year
                st.session_state["selected_exam_date_from_sidebar"] = first_person_year_df.iloc[0]["วันที่ตรวจ"]
            else:
                # Should not happen if query_df is not empty, but defensive
                st.session_state.pop("person_row", None)
                st.session_state.pop("selected_row_found", None)
                st.sidebar.error("❌ พบข้อมูลแต่ไม่สามารถแสดงผลได้ กรุณาลองใหม่")
    else:
        # If search_query is empty, also display an error/info
        st.sidebar.info("กรุณากรอก HN หรือ ชื่อ-สกุล เพื่อค้นหา")
        # search_result is already popped to None, so no old data remains.

# ==================== SELECT YEAR AND EXAM DATE IN SIDEBAR ====================
if "search_result" in st.session_state:
    results_df = st.session_state["search_result"]

    with st.sidebar:
        st.markdown("<hr>", unsafe_allow_html=True) # Separator
        st.markdown("<h3>เลือกปีและวันที่ตรวจ</h3>", unsafe_allow_html=True)

        available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
        
        # Use session state to persist selection across reruns
        if "selected_year_from_sidebar" not in st.session_state:
            st.session_state["selected_year_from_sidebar"] = available_years[0] if available_years else None
        
        selected_year_from_sidebar = st.selectbox(
            "📅 เลือกปีที่ต้องการดูผลตรวจรายงาน",
            options=available_years,
            index=available_years.index(st.session_state["selected_year_from_sidebar"]) if st.session_state["selected_year_from_sidebar"] in available_years else (0 if available_years else None),
            format_func=lambda y: f"พ.ศ. {y}",
            key="year_select" # Use a key to manage state
        )
        st.session_state["selected_year_from_sidebar"] = selected_year_from_sidebar


        if selected_year_from_sidebar:
            selected_hn = results_df.iloc[0]["HN"] # Get HN of the first found person (assuming one person in results_df)

            person_year_df = results_df[
                (results_df["Year"] == selected_year_from_sidebar) &
                (results_df["HN"] == selected_hn)
            ].drop_duplicates(subset=["HN", "วันที่ตรวจ"]).sort_values(by="วันที่ตรวจ", key=lambda x: pd.to_datetime(x, errors='coerce', dayfirst=True), ascending=False) # Sort by date (robust)

            exam_dates_options = person_year_df["วันที่ตรวจ"].dropna().unique().tolist()
            
            if exam_dates_options:
                # If there's only one exam date, automatically select it and display the report
                if len(exam_dates_options) == 1:
                    st.session_state["selected_exam_date_from_sidebar"] = exam_dates_options[0]
                    # Automatically set person_row if only one date
                    st.session_state["person_row"] = person_year_df[
                        person_year_df["วันที่ตรวจ"] == st.session_state["selected_exam_date_from_sidebar"]
                    ].iloc[0].to_dict()
                    st.session_state["selected_row_found"] = True
                else:
                    # Dropdown for multiple exam dates
                    if "selected_exam_date_from_sidebar" not in st.session_state:
                        st.session_state["selected_exam_date_from_sidebar"] = exam_dates_options[0]
                    
                    selected_exam_date_from_sidebar = st.selectbox(
                        "🗓️ เลือกวันที่ตรวจ",
                        options=exam_dates_options,
                        index=exam_dates_options.index(st.session_state["selected_exam_date_from_sidebar"]) if st.session_state["selected_exam_date_from_sidebar"] in exam_dates_options else (0 if exam_dates_options else None),
                        key="exam_date_select" # Use a key
                    )
                    st.session_state["selected_exam_date_from_sidebar"] = selected_exam_date_from_sidebar

                    # Update person_row based on selected exam date
                    st.session_state["person_row"] = person_year_df[
                        person_year_df["วันที่ตรวจ"] == selected_exam_date_from_sidebar
                    ].iloc[0].to_dict()
                    st.session_state["selected_row_found"] = True
            else:
                st.info("ไม่พบข้อมูลการตรวจสำหรับปีที่เลือก")
                st.session_state.pop("person_row", None)
                st.session_state.pop("selected_row_found", None)


# ==================== Display Health Report (Main Content) ====================
# This entire section will only render if person_row and selected_row_found are true
# All helper functions are now defined globally above
if "person_row" in st.session_state and st.session_state.get("selected_row_found", False):
    person = st.session_state["person_row"]
    year_display = person.get("Year", "-")

    # ===== Fetch main data =====
    sbp = person.get("SBP", "")
    dbp = person.get("DBP", "")
    pulse_raw = person.get("pulse", "-")
    weight = person.get("น้ำหนัก", "-")
    height = person.get("ส่วนสูง", "-")
    waist = person.get("รอบเอว", "-")
    check_date = person.get("วันที่ตรวจ", "-")

    try:
        weight_val = float(str(weight).replace("กก.", "").strip())
        height_val = float(str(height).replace("ซม.", "").strip())
        bmi_val = weight_val / ((height_val / 100) ** 2) if height_val > 0 else None
    except:
        bmi_val = None

    try:
        sbp_int = int(float(str(sbp).strip()))
        dbp_int = int(float(str(dbp).strip()))
        bp_val = f"{sbp_int}/{dbp_int} ม.ม.ปรอท"
    except:
        sbp_int = dbp_int = None
        bp_val = "-"
    
    # Corrected: interpret_bp is now defined
    if sbp_int is None or dbp_int is None:
        bp_desc = "-"
        bp_full = "-"
    else:
        bp_desc = interpret_bp(sbp, dbp)
        bp_full = f"{bp_val} - {bp_desc}" if bp_desc != "-" else bp_val

    try:
        pulse_val = int(float(str(pulse_raw).strip()))
    except:
        pulse_val = None

    pulse = f"{pulse_val} ครั้ง/นาที" if pulse_val is not None else "-"
    weight_display = f"{weight} กก." if not is_empty(weight) else "-"
    height_display = f"{height} ซม." if not is_empty(height) else "-"
    waist_display = f"{waist} ซม." if not is_empty(waist) else "-"

    sex = str(person.get("เพศ", "")).strip()

    advice_text = combined_health_advice(bmi_val, sbp, dbp, waist, sex) # Pass sex to combined_health_advice
    summary_advice = html.escape(advice_text) if advice_text else ""
    
    # ===== Display General Information Section =====
    st.markdown(f"""
    <div style="font-size: 18px; line-height: 1.8; color: inherit; padding: 24px 8px; font-family: \"Sarabun\", sans-serif;">
        <div style="text-align: center; font-size: 29px; font-weight: bold;">รายงานผลการตรวจสุขภาพ</div>
        <div style="text-align: center;">วันที่ตรวจ: {check_date or "-"}</div>
        <div style="text-align: center; margin-top: 10px;">
            โรงพยาบาลสันทราย 201 หมู่ที่ 11 ถนน เชียงใหม่ - พร้าว ตำบลหนองหาร อำเภอสันทราย เชียงใหม่ 50290<br>
            ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167
        </div>
        <hr style="margin: 24px 0;">
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 20px; text-align: center;">
            <div><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</div>
            <div><b>อายุ:</b> {str(int(float(person.get('อายุ')))) if str(person.get('อายุ')).replace('.', '', 1).isdigit() else person.get('อายุ', '-')} ปี</div>
            <div><b>เพศ:</b> {person.get('เพศ', '-')}</div>
            <div><b>HN:</b> {str(int(float(person.get('HN')))) if str(person.get('HN')).replace('.', '', 1).isdigit() else person.get('HN', '-')}</div>
            <div><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</div>
        </div>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 16px; text-align: center;">
            <div><b>น้ำหนัก:</b> {weight_display}</div>
            <div><b>ส่วนสูง:</b> {height_display}</div>
            <div><b>รอบเอว:</b> {waist_display}</div>
            <div><b>ความดันโลหิต:</b> {bp_full}</div>
            <div><b>ชีพจร:</b> {pulse}</div>
        </div>
        {f"<div style='margin-top: 16px; text-align: center;'><b>คำแนะนำ:</b> {summary_advice}</div>" if summary_advice else ""}
    </div>
    """, unsafe_allow_html=True)

    if sex not in ["ชาย", "หญิง"]:
        st.warning("⚠️ เพศไม่ถูกต้องหรือไม่มีข้อมูล กำลังใช้ค่าอ้างอิงเริ่มต้น")
        sex = "ไม่ระบุ"

    if sex == "หญิง":
        hb_low = 12
        hct_low = 36
    elif sex == "ชาย":
        hb_low = 13
        hct_low = 39
    else: # Default for "ไม่ระบุ" or invalid sex
        hb_low = 12
        hct_low = 36

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

    blood_config = [
        ("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106),
        ("น้ำตาลในเลือด (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2),
        ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120),
        ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37),
        ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41),
        ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200),
        ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150),
        ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True),
        ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160),
        ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20),
        ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17),
        ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True),
    ]

    blood_rows = []
    for label, col, norm, low, high, *opt in blood_config:
        higher = opt[0] if opt else False
        val = get_float(col, person)
        result, is_abn = flag(val, low, high, higher)
        blood_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])

    left_spacer, col1, col2, right_spacer = st.columns([0.5, 3, 3, 0.5]) # Adjusted spacer ratio

    with col1:
        st.markdown(render_lab_table_html("ผลตรวจ CBC", "Complete Blood Count", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_lab_table_html("ผลตรวจเคมีเลือด", "Blood Chemistry", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

    # ==================== Combined Recommendations ====================
    gfr_raw = person.get("GFR", "")
    fbs_raw = person.get("FBS", "")
    alp_raw = person.get("ALP", "")
    sgot_raw = person.get("SGOT", "")
    sgpt_raw = person.get("SGPT", "")
    uric_raw = person.get("Uric Acid", "")
    chol_raw = person.get("CHOL", "")
    tgl_raw = person.get("TGL", "")
    ldl_raw = person.get("LDL", "")

    advice_list = []
    kidney_summary = kidney_summary_gfr_only(gfr_raw)
    advice_list.append(kidney_advice_from_summary(kidney_summary))
    advice_list.append(fbs_advice(fbs_raw))
    advice_list.append(liver_advice(summarize_liver(alp_raw, sgot_raw, sgpt_raw)))
    advice_list.append(uric_acid_advice(uric_raw))
    advice_list.append(lipids_advice(summarize_lipids(chol_raw, tgl_raw, ldl_raw)))
    advice_list.append(cbc_advice(
        person.get("Hb(%)", ""), 
        person.get("HCT", ""), 
        person.get("WBC (cumm)", ""), 
        person.get("Plt (/mm)", ""),
        sex=sex
    ))

    spacer_l, main_col, spacer_r = st.columns([0.5, 6, 0.5]) # Adjusted spacer ratio

    with main_col:
        final_advice_html = merge_final_advice_grouped(advice_list)
        # Determine if there's any *actual* advice for general health (i.e., not just "no advice")
        has_general_advice = "ไม่พบคำแนะนำเพิ่มเติม" not in final_advice_html
        
        # Set background color based on whether there's advice
        background_color_general_advice = (
            "rgba(255, 255, 0, 0.2)" if has_general_advice else "rgba(57, 255, 20, 0.2)" # Vibrant translucent yellow if advice, vibrant translucent green if normal
        )

        st.markdown(f"""
        <div style="
            background-color: {background_color_general_advice};
            padding: 1rem 2.5rem;
            border-radius: 10px;
            font-size: 18px; /* Adjusted font size */
            line-height: 1.5;
            color: var(--text-color);
            font-family: "Sarabun", sans-serif;
        ">
            {final_advice_html}
        </div>
        """, unsafe_allow_html=True)

    # ==================== Urinalysis Section ====================
    # selected_year is used here. Ensure it's correctly passed or accessed from session_state
    selected_year = st.session_state.get("selected_year_from_sidebar", None)
    if selected_year is None: # Fallback if for some reason it's not set
        selected_year = datetime.now().year + 543 # Default to current BE year

    with st.container(): # This was 'with col_ua_left:', now it's a general container
        left_spacer_ua, col_ua_left, col_ua_right, right_spacer_ua = st.columns([0.5, 3, 3, 0.5]) # Adjusted spacer ratio
        
        with col_ua_left:
            render_urine_section(person, sex, selected_year) # Pass all required args

            # ==================== Stool Section ====================
            st.markdown(render_section_header("ผลตรวจอุจจาระ", "Stool Examination"), unsafe_allow_html=True)
            
            stool_exam_raw = person.get("Stool exam", "")
            stool_cs_raw = person.get("Stool C/S", "")
            exam_text = interpret_stool_exam(stool_exam_raw)
            cs_text = interpret_stool_cs(stool_cs_raw)
            st.markdown(render_stool_html_table(exam_text, cs_text), unsafe_allow_html=True)

        with col_ua_right:
            # ============ X-ray Section ============
            st.markdown(render_section_header("ผลเอกซเรย์", "Chest X-ray"), unsafe_allow_html=True)
            
            selected_year_int = int(selected_year)
            cxr_col = "CXR" if selected_year_int == 2568 else f"CXR{str(selected_year_int)[-2:]}"
            cxr_raw = person.get(cxr_col, "")
            cxr_result = interpret_cxr(cxr_raw)
            
            st.markdown(f"""
            <div style='
                background-color: var(--background-color);
                color: var(--text-color);
                font-size: 18px; /* Adjusted font size */
                line-height: 1.6;
                padding: 1.25rem;
                border-radius: 6px;
                margin-bottom: 1.5rem;
                font-family: "Sarabun", sans-serif;
            '>
                {cxr_result}
            </div>
            """, unsafe_allow_html=True)

            # ==================== EKG Section ====================
            st.markdown(render_section_header("ผลคลื่นไฟฟ้าหัวใจ", "EKG"), unsafe_allow_html=True)

            ekg_col = get_ekg_col_name(selected_year_int)
            ekg_raw = person.get(ekg_col, "")
            ekg_result = interpret_ekg(ekg_raw)

            st.markdown(f"""
            <div style='
                background-color: var(--secondary-background-color);
                color: var(--text-color);
                font-size: 18px; /* Adjusted font size */
                line-height: 1.6;
                padding: 1.25rem;
                border-radius: 6px;
                margin-bottom: 1.5rem;
                font-family: "Sarabun", sans-serif;
            '>
                {ekg_result}
            </div>
            """, unsafe_allow_html=True)

            # ==================== Section: Hepatitis A ====================
            st.markdown(render_section_header("ผลการตรวจไวรัสตับอักเสบเอ (Viral hepatitis A)"), unsafe_allow_html=True)
            
            hep_a_raw = safe_text(person.get("Hepatitis A"))
            st.markdown(f"""
            <div style='
                font-size: 18px; /* Adjusted font size */
                padding: 1rem;
                border-radius: 6px;
                margin-bottom: 1.5rem;
                background-color: rgba(255,255,255,0.05);
                font-family: "Sarabun", sans-serif;
            '>
                {hep_a_raw}
            </div>
            """, unsafe_allow_html=True)
            
            # ================ Section: Hepatitis B =================

            hep_check_date_raw = person.get("ปีตรวจHEP")
            hep_check_date = normalize_date_for_display(hep_check_date_raw) # Use the new normalization function here
            
            st.markdown(render_section_header("ผลการตรวจไวรัสตับอักเสบบี (Viral hepatitis B)"), unsafe_allow_html=True)
            
            hbsag_raw = safe_text(person.get("HbsAg"))
            hbsab_raw = safe_text(person.get("HbsAb"))
            hbcab_raw = safe_text(person.get("HBcAB"))
            
            st.markdown(f"""
            <div style="margin-bottom: 1rem;">
            <table style='
                width: 100%;
                font-size: 18px; /* Adjusted font size */
                text-align: center;
                border-collapse: collapse;
                min-width: 300px;
                font-family: "Sarabun", sans-serif;
            '>
                <thead>
                    <tr>
                        <th style="padding: 8px; border: 1px solid transparent;">HBsAg</th>
                        <th style="padding: 8px; border: 1px solid transparent;">HBsAb</th>
                        <th style="padding: 8px; border: 1px solid transparent;">HBcAb</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding: 8px; border: 1px solid transparent;">{hbsag_raw}</td>
                        <td style="padding: 8px; border: 1px solid transparent;">{hbsab_raw}</td>
                        <td style="padding: 8px; border: 1px solid transparent;">{hbcab_raw}</td>
                    </tr>
                </tbody>
            </table>
            </div>
            """, unsafe_allow_html=True)
            
            hep_history = safe_text(person.get("สรุปประวัติ Hepb"))
            hep_vaccine = safe_text(person.get("วัคซีนhep b 67"))

            st.markdown(f"""
            <div style='
                font-size: 18px; /* Adjusted font size */
                padding: 0.75rem 1rem;
                background-color: rgba(255,255,255,0.05);
                border-radius: 6px;
                margin-bottom: 1.5rem;
                line-height: 1.8;
                font-family: "Sarabun", sans-serif;
            '>
                <b>วันที่ตรวจภูมิคุ้มกัน:</b> {hep_check_date}<br>
                <b>ประวัติโรคไวรัสตับอักเสบบี ปี พ.ศ. {selected_year}:</b> {hep_history}<br>
                <b>ประวัติการได้รับวัคซีนในปี พ.ศ. {selected_year}:</b> {hep_vaccine}
            </div>
            """, unsafe_allow_html=True)
            
            advice = hepatitis_b_advice(hbsag_raw, hbsab_raw, hbcab_raw)
            
            # 🌈 Set background color based on advice
            if advice.strip() == "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี":
                bg_color = "rgba(57, 255, 20, 0.2)"  # Vibrant translucent green
            else:
                bg_color = "rgba(255, 255, 0, 0.2)" # Vibrant translucent yellow

            st.markdown(f"""
            <div style='
                font-size: 18px; /* Adjusted font size */
                line-height: 1.6;
                padding: 1rem 1.5rem;
                border-radius: 6px;
                background-color: {bg_color};
                color: var(--text-color);
                margin-bottom: 1.5rem;
                font-family: "Sarabun", sans-serif;
            '>
                {advice}
            </div>
            """, unsafe_allow_html=True)
                
        #=========================== ความเห็นแพทย์ =======================
        doctor_suggestion = str(person.get("DOCTER suggest", "")).strip()
        if doctor_suggestion.lower() in ["", "-", "none", "nan", "null"]:
            doctor_suggestion = "<i>ไม่มีคำแนะนำจากแพทย์</i>"

        left_spacer3, doctor_col, right_spacer3 = st.columns([0.5, 6, 0.5]) # Adjusted spacer ratio

        with doctor_col:
            st.markdown(f"""
            <div style='
                background-color: #1b5e20;
                color: white;
                padding: 1.5rem 2rem;
                border-radius: 8px;
                font-size: 18px; /* Adjusted font size */
                line-height: 1.6;
                margin-top: 2rem;
                margin-bottom: 2rem;
                font-family: "Sarabun", sans-serif;
            '>
                <b>สรุปความเห็นของแพทย์:</b><br> {doctor_suggestion}
            </div>

            <div style='
                margin-top: 7rem;
                text-align: right;
                padding-right: 1rem;
            '>
                <div style='
                    display: inline-block;
                    text-align: center;
                    width: 340px;
                '>
                    <div style='
                        border-bottom: 1px dotted #ccc;
                        margin-bottom: 0.5rem;
                        width: 100%;
                    '></div>
                    <div style='white-space: nowrap;'>นายแพทย์นพรัตน์ รัชฎาพร</div>
                    <div style='white-space: nowrap;'>เลขที่ใบอนุญาตผู้ประกอบวิชาชีพเวชกรรม ว.26674</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
