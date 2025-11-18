import pandas as pd
from datetime import datetime
import html
from collections import OrderedDict
import json

# --- Import a key function from performance_tests ---
from performance_tests import generate_holistic_advice # (ยังคง import ไว้เผื่อใช้ในอนาคต แต่เราจะไม่เรียกใช้)
from print_performance_report import generate_performance_report_html_for_main_report

# ==============================================================================
# NOTE: This file generates the printable health report.
# The header is compact, while the body retains the original layout.
# ==============================================================================

# --- START OF CHANGE: Add CBC Recommendation Texts ---
# ... (existing code) ...
RECOMMENDATION_TEXTS_CBC = {
    "C2": "ให้รับประทานอาหารที่มีประโยชน์ เช่น นม ผักใบเขียว ถั่วเมล็ดแห้ง เนื้อสัตว์ ไข่ เป็นต้น พักผ่อนให้เพียงพอ ถ้ามีหน้ามืดวิงเวียน อ่อนเพลียหรือมีไข้ให้พบแพทย์",
# ... (existing code) ...
}
# --- END OF CHANGE ---

# --- START OF CHANGE: Add Urine Recommendation Texts ---
RECOMMENDATION_TEXTS_URINE = {
    "E11": "ให้หลีกเลี่ยงการทานอาหารที่มีน้ำตาลสูง",
# ... (existing code) ...
    "E2": "อาจเกิดจากการปนเปื้อนในการเก็บปัสสาวะหรือมีการติดเชื้อในระบบทางเดินปัสสาวะให้ดื่มน้ำมากๆ ไม่ควรกลั้นปัสสาวะ ถ้ามีอาการ ผิดปกติ ปัสสาวะแสบขัด ขุ่น ปวดท้องน้อย ปวดบั้นเอว กลั้นปัสสาวะไม่อยู่ ไข้สูง หนาวสั่น ควรรีบไปพบแพทย์",
}
# --- END OF CHANGE ---


# --- Helper Functions (adapted from app.py for printing) ---

def is_empty(val):
# ... (existing code) ...
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def get_float(col, person_data):
# ... (existing code) ...
    except: return None

def flag(val, low=None, high=None, higher_is_better=False):
# ... (existing code) ...
    return formatted_val, is_abn

def safe_value(val):
# ... (existing code) ...
    return "-" if val.lower() in ["", "nan", "none", "-"] else val

def parse_range_or_number(val):
# ... (existing code) ...
    except: return None, None

def interpret_rbc(value):
# ... (existing code) ...
    return "พบเม็ดเลือดแดงในปัสสาวะ"

def interpret_wbc(value):
# ... (existing code) ...
    return "พบเม็ดเลือดขาวในปัสสาวะ"

def is_urine_abnormal(test_name, value, normal_range):
# ... (existing code) ...
    if test_name == "สี (Colour)": return val not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"]
    return False

def interpret_stool_exam(val):
# ... (existing code) ...
    return val

def interpret_stool_cs(value):
# ... (existing code) ...
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"

def interpret_cxr(val):
# ... (existing code) ...
    return val

def get_ekg_col_name(year):
# ... (existing code) ...
    return "EKG" if year == current_thai_year else f"EKG{str(year)[-2:]}"

def interpret_ekg(val):
# ... (existing code) ...
    return val

def hepatitis_b_advice(hbsag, hbsab, hbcab):
    # --- START OF CHANGE: Treat '-' as 'negative' for HBcAb logic ---
    if all(x == "negative" for x in [hbsag_logic, hbsab_logic, hbcab_logic]): return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน", "no_immune"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ", "unclear"
    # --- END OF CHANGE ---

# --- START OF CHANGE: (เพิ่มฟังก์ชันที่ขาดไป) ---
def render_section_header(title, subtitle=None):
    full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
    return f"""
    <div style='background-color: #f0f2f6; color: #333; text-align: center; padding: 0.2rem 0.4rem; font-weight: bold; border-radius: 6px; margin-top: 0.5rem; margin-bottom: 0.2rem; font-size: 11px; border: 1px solid #ddd;'>
        {full_title}
    </div>
    """
# --- END OF CHANGE ---

# --- START OF CHANGE: Modified function to return a list ---
def generate_fixed_recommendations(person_data):
# ... (existing code) ...
    return recommendations # คืนค่าเป็น list ของ strings
# --- END OF CHANGE ---

# --- START OF CHANGE: Add new function for CBC logic ---
# --- START OF REFACTOR: Return dictionary with statuses ---
def generate_cbc_recommendations(person_data, sex):
# ... (existing code) ...
    return {'summary': summary_html, 'status_ce': status_ce, 'status_cf': status_cf, 'status_cg': status_cg}
# --- END OF REFACTOR ---
# --- END OF CHANGE ---

# --- START OF CHANGE: Add new function for Urine logic ---
# --- START OF REFACTOR: Return dictionary with statuses ---
def generate_urine_recommendations(person_data, sex):
# ... (existing code) ...
    return {'summary': summary_html, 'status_ct': status_ct, 'status_cu': status_cu, 'status_cv': status_cv, 'status_cw': status_cw}
# --- END OF REFACTOR ---
# --- END OF CHANGE ---

# --- START OF CHANGE: Add new function for Doctor Opinion logic ---
def generate_doctor_opinion(person_data, sex, cbc_statuses, urine_statuses):
# ... (existing code) ...
    return f"   {final_opinion}" if final_opinion else "-" # ถ้าไม่มีอะไรเลย ให้แสดง "-"

# --- END OF CHANGE ---


# --- HTML Rendering Functions ---

def render_section_header(title, subtitle=None):
# ... (existing code) ...
    """
    </div>
    """

# --- START OF CHANGE: Modified function to accept footer_html ---
def render_lab_table_html(title, subtitle, headers, rows, table_class="print-lab-table", footer_html=None):
# ... (existing code) ...
    html_content += "</table>" # Close table
    return html_content
# --- END OF CHANGE ---

def render_header_and_vitals(person_data):
# ... (existing code) ...
    <hr style="border: 0; border-top: 1px solid #e0e0e0; margin: 0.5rem 0;">
    """

# --- START OF CHANGE: Pass cbc_statuses to render ---
def render_lab_section(person, sex, cbc_statuses):
# ... (existing code) ...
            <td style="width: 50%; vertical-align: top; padding-left: 5px;">{blood_html}</td>
        </tr>
    </table>
    """

# --- START OF CHANGE: Pass urine_statuses and doctor_opinion to render ---
# --- START OF REFACTOR: Add all_person_history_df ---
def render_other_results_html(person, sex, urine_statuses, doctor_opinion, all_person_history_df=None):
# ... (existing code) ...
    return f"""
    <table style="width: 100%; border-collapse: collapse; page-break-inside: avoid;">
        <tr>
            <td style="width: 50%; vertical-align: top; padding-right: 5px;">{urine_html}{stool_html}</td>
            <td style="width: 50%; vertical-align: top; padding-left: 5px;">{other_tests_html}{hepatitis_html}{doctor_opinion_html}</td>
        </tr>
    </table>
    """

# --- START: (REFACTOR) แยก CSS ออกมา ---
def get_main_report_css():
    """
    คืนค่าสตริง CSS สำหรับรายงานสุขภาพหลัก
    """
    return f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
        
        /* --- START OF CHANGE: Adjust body margin --- */
        body {{ 
            font-family: 'Sarabun', sans-serif !important; 
            font-size: 9.5px; 
            margin: 0.5cm; /* <-- ปรับ margin ทุกด้านเป็น 0.5cm */
            color: #333; 
            background-color: #fff; 
        }}
        /* --- END OF CHANGE --- */

        p, div, span, td, th {{ line-height: 1.4; }}
        table {{ border-collapse: collapse; width: 100%; }}
        .print-lab-table td, .print-lab-table th {{ padding: 2px 4px; border: 1px solid #ccc; text-align: center; vertical-align: middle; }}
        .print-lab-table th {{ background-color: #f2f2f2; font-weight: bold; }}
        .print-lab-table-abn {{ background-color: #fff1f0 !important; }}
        
        .print-lab-table tfoot .recommendation-row td {{
            background-color: #fcf8e3; /* Light yellow */
            font-size: 9px;
            line-height: 1.3;
            border: 1px solid #ccc;
            text-align: left;
            padding: 4px 6px;
        }}
        .print-lab-table tfoot ul {{
            padding-left: 15px;
            margin-top: 2px;
            margin-bottom: 2px;
        }}
        .print-lab-table tfoot li {{
            margin-bottom: 2px;
        }}
        
        .header-grid {{ display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 0.5rem; }}
        .header-left {{ text-align: left; }}
        .header-right {{ text-align: right; }}
        .info-table {{ font-size: 9.5px; text-align: left; }}
        .info-table td {{ padding: 1px 5px; border: none; }}
        
        /* This green box is no longer used, but CSS remains just in case */
        .advice-box {{ padding: 0.5rem 1rem; border-radius: 8px; line-height: 1.5; margin-top: 0.5rem; border: 1px solid #ddd; page-break-inside: avoid; }}
        .advice-title {{ font-weight: bold; margin-bottom: 0.3rem; font-size: 11px; }}
        .advice-content ul {{ padding-left: 20px; margin: 0; }}
        .advice-content ul li {{ margin-bottom: 4px; }}
        
        .doctor-opinion-box {{
            background-color: #e8f5e9; /* Light green */
            border-color: #a5d6a7;
            border: 1px solid #ddd;
            padding: 0rem 0.5rem; /* <-- ปรับลด padding บน/ล่าง เป็น 0 */
            border-radius: 8px;
            line-height: 1.5;
            margin-top: 0.5rem;
            page-break-inside: avoid;
            font-size: 9.5px; /* <-- ปรับจาก 9px เป็น 9.5px */
            white-space: pre-wrap; /* เพิ่ม white-space pre-wrap */
        }}
        
        .perf-section {{ margin-top: 0.5rem; page-break-inside: avoid; border: 1px solid #e0e0e0; border-radius: 8px; padding: 0.5rem; }}
        .summary-box {{ background-color: #f8f9fa; border-radius: 4px; padding: 4px 8px; margin-top: 2px; font-size: 9px; }}
        @media print {{ body {{ -webkit-print-color-adjust: exact; margin: 0; }} }}
    </style>
    """
# --- END: (REFACTOR) แยก CSS ออกมา ---

# --- START: (REFACTOR) แยก Body HTML ออกมา ---
def render_printable_report_body(person_data, all_person_history_df=None):
    """
    สร้างเฉพาะส่วน <body> ของรายงานสุขภาพหลัก
    """
    sex = str(person_data.get("เพศ", "")).strip()
    if sex not in ["ชาย", "หญิง"]: sex = "ไม่ระบุ"
    
    # --- START OF CHANGE: Call generation functions once ---
    cbc_results = generate_cbc_recommendations(person_data, sex)
    urine_results = generate_urine_recommendations(person_data, sex)
    doctor_opinion = generate_doctor_opinion(person_data, sex, cbc_results, urine_results)
    # --- END OF CHANGE ---
    
    header_vitals_html = render_header_and_vitals(person_data)
    # --- START OF CHANGE: Pass statuses AND history to render functions ---
    lab_section_html = render_lab_section(person_data, sex, cbc_results)
    other_results_html = render_other_results_html(person_data, sex, urine_results, doctor_opinion, all_person_history_df)
    # --- END OF CHANGE ---
    
    # --- START OF CHANGE: Remove the green recommendation box ---
    # The logic is now inside render_lab_section and render_other_results_html
    doctor_suggestion_html = ""
    # --- END OF CHANGE ---

    signature_html = """
    <div style="margin-top: 2rem; text-align: right; padding-right: 1rem; page-break-inside: avoid;">
        <div style="display: inline-block; text-align: center; width: 280px;">
            <div style="border-bottom: 1px dotted #333; margin-bottom: 0.4rem; width: 100%;"></div>
            <div style="white-space: nowrap;">นายแพทย์นพรัตน์ รัชฎาพร</div>
            <div style="white-space: nowrap;">แพทย์อาชีวเวชศาสตร์</div>
            <div style="white-space: nowrap;">ว.26674</div>
        </div>
    </div>
    """
    
    # รวม HTML ส่วน Body ทั้งหมด
    body_html = f"""
    {header_vitals_html}
    {lab_section_html}
    {other_results_html}
    {doctor_suggestion_html}
    {signature_html}
    """
    return body_html
# --- END: (REFACTOR) แยก Body HTML ออกมา ---


def generate_printable_report(person_data, all_person_history_df=None):
    """Generates a full, self-contained HTML string for the health report."""
    
    # --- START: (REFACTOR) เรียกใช้ฟังก์ชันที่แยกออกมา ---
    css_html = get_main_report_css()
    body_html = render_printable_report_body(person_data, all_person_history_df)
    # --- END: (REFACTOR) ---
    
    final_html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลการตรวจสุขภาพ - {html.escape(person_data.get('ชื่อ-สกุล', ''))}</title>
        {css_html}
    </head>
    <body>
        {body_html}
    </body>
    </html>
    """
    return final_html
