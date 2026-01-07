import pandas as pd
import html
from collections import OrderedDict
from datetime import datetime

# แก้ไข: import ฟังก์ชัน interpret_audiogram, interpret_lung_capacity, และ interpret_cxr
from performance_tests import interpret_audiogram, interpret_lung_capacity, interpret_cxr

# ==============================================================================
# Module: print_performance_report.py
# Purpose: Contains functions to generate HTML for performance test reports
# (Vision, Hearing, Lung) for the standalone printable version.
# Refactored for Batch Printing capability.
# Updated: Expanded font size and Auto-fit to 1 page layout.
# ==============================================================================


# --- Helper & Data Availability Functions ---

def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def has_vision_data(person_data):
    """Check for any ACTUAL vision test data, ignoring summary/advice fields."""
    detailed_keys = [
        'ป.การรวมภาพ', 'ผ.การรวมภาพ',
        'ป.ความชัดของภาพระยะไกล', 'ผ.ความชัดของภาพระยะไกล',
        'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)',
        'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)',
        'ป.การกะระยะและมองความชัดลึกของภาพ', 'ผ.การกะระยะและมองความชัดลึกของภาพ',
        'ป.การจำแนกสี', 'ผ.การจำแนกสี',
        'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง',
        'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน',
        'ป.ความชัดของภาพระยะใกล้', 'ผ.ความชัดของภาพระยะใกล้',
        'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)',
        'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)',
        'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน',
        'ป.ลานสายตา', 'ผ.ลานสายตา',
        'ผ.สายตาเขซ่อนเร้น'
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

# --- HTML Rendering Functions for Standalone Report ---

def render_section_header(title, subtitle=None):
    """Renders a styled section header for the print report."""
    full_title = f"{title} <span style='font-weight: normal; font-size: 0.9em;'>({subtitle})</span>" if subtitle else title
    return f"""
    <div class='section-header'>
        {full_title}
    </div>
    """

def render_html_header_and_personal_info(person):
    """Renders the main header and personal info table for the print report."""
    check_date = person.get("วันที่ตรวจ", "-")
    name = person.get('ชื่อ-สกุล', '-')
    age = str(int(float(person.get('อายุ')))) if str(person.get('อายุ')).replace('.', '', 1).isdigit() else person.get('อายุ', '-')
    sex = person.get('เพศ', '-')
    hn = str(int(float(person.get('HN')))) if str(person.get('HN')).replace('.', '', 1).isdigit() else person.get('HN', '-')
    department = person.get('หน่วยงาน', '-')
    
    sbp = person.get("SBP", "")
    dbp = person.get("DBP", "")
    try:
        sbp_int, dbp_int = int(float(sbp)), int(float(dbp))
        bp_val = f"{sbp_int}/{dbp_int}"
    except: bp_val = "-"
    
    pulse_raw = person.get("pulse", "-")
    pulse_val = str(int(float(pulse_raw))) if not is_empty(pulse_raw) and str(pulse_raw).replace('.', '', 1).isdigit() else "-"

    waist_val = person.get("รอบเอว", "-")
    waist_display = f"{waist_val}" if not is_empty(waist_val) else "-"
    
    weight = person.get("น้ำหนัก", "-")
    height = person.get("ส่วนสูง", "-")

    # Use compact flex layout with bigger font
    return f"""
    <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #00796B; padding-bottom: 8px; margin-bottom: 10px; font-family: 'Sarabun', sans-serif;">
        <div style="width: 45%;">
            <h3 style="margin: 0; color: #00796B; font-size: 20px; line-height: 1.2;">รายงานผลการตรวจสมรรถภาพ</h3>
            <p style="margin: 2px 0 0 0; font-size: 13px; font-weight: 600;">คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม</p>
            <p style="margin: 0; font-size: 13px;">โรงพยาบาลสันทราย</p>
            <p style="margin-top: 4px; font-size: 13px;"><b>วันที่ตรวจ:</b> {check_date}</p>
        </div>
        <div style="width: 55%; text-align: right;">
            <h3 style="margin: 0; font-size: 22px; line-height: 1.2;">{name}</h3>
            <p style="margin: 2px 0 0 0; font-size: 14px;">
                <b>HN:</b> {hn} <span style="color: #ddd;">|</span> <b>เพศ:</b> {sex} <span style="color: #ddd;">|</span> <b>อายุ:</b> {age} ปี
            </p>
            <p style="margin: 2px 0 0 0; font-size: 14px;"><b>หน่วยงาน:</b> {department}</p>
            
            <div style="margin-top: 5px; font-size: 13px; background-color: #f0f0f0; display: inline-block; padding: 2px 8px; border-radius: 4px; border: 1px solid #ddd;">
                <b>นน.</b> {weight} <span style="color: #ccc;">|</span> <b>สูง</b> {height} <span style="color: #ccc;">|</span> <b>เอว</b> {waist_display} <span style="color: #ccc;">/</span> <b>BP:</b> {bp_val} <span style="color: #ccc;">|</span> <b>PR:</b> {pulse_val}
            </div>
        </div>
    </div>
    """


def render_print_vision(person_data):
    """Renders the Vision Test section for the print report with complete logic."""
    if not has_vision_data(person_data):
        return ""

    vision_tests = [
        {'display': '1. การมองด้วย 2 ตา (Binocular vision)', 'type': 'paired_value', 'normal_col': 'ป.การรวมภาพ', 'abnormal_col': 'ผ.การรวมภาพ'},
        {'display': '2. ความชัดระยะไกล - สองตา (Far vision - Both)', 'type': 'paired_value', 'normal_col': 'ป.ความชัดของภาพระยะไกล', 'abnormal_col': 'ผ.ความชัดของภาพระยะไกล'},
        {'display': '3. ความชัดระยะไกล - ตาขวา (Far vision - Right)', 'type': 'value', 'col': 'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)'},
        {'display': '4. ความชัดระยะไกล - ตาซ้าย (Far vision - Left)', 'type': 'value', 'col': 'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)'},
        {'display': '5. การมองภาพ 3 มิติ (Stereo depth)', 'type': 'paired_value', 'normal_col': 'ป.การกะระยะและมองความชัดลึกของภาพ', 'abnormal_col': 'ผ.การกะระยะและมองความชัดลึกของภาพ'},
        {'display': '6. การมองจำแนกสี (Color discrimination)', 'type': 'paired_value', 'normal_col': 'ป.การจำแนกสี', 'abnormal_col': 'ผ.การจำแนกสี'},
        {'display': '7. สมดุลกล้ามเนื้อตาแนวดิ่ง (Far vertical phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง', 'related_keyword': 'แนวตั้งระยะไกล'},
        {'display': '8. สมดุลกล้ามเนื้อตาแนวนอน (Far lateral phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน', 'related_keyword': 'แนวนอนระยะไกล'},
        {'display': '9. ความชัดระยะใกล้ - สองตา (Near vision - Both)', 'type': 'paired_value', 'normal_col': 'ป.ความชัดของภาพระยะใกล้', 'abnormal_col': 'ผ.ความชัดของภาพระยะใกล้'},
        {'display': '10. ความชัดระยะใกล้ - ตาขวา (Near vision - Right)', 'type': 'value', 'col': 'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)'},
        {'display': '11. ความชัดระยะใกล้ - ตาซ้าย (Near vision - Left)', 'type': 'value', 'col': 'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)'},
        {'display': '12. สมดุลกล้ามเนื้อตาแนวนอน (Near lateral phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน', 'related_keyword': 'แนวนอนระยะใกล้'},
        {'display': '13. ลานสายตา (Visual field)', 'type': 'paired_value', 'normal_col': 'ป.ลานสายตา', 'abnormal_col': 'ผ.ลานสายตา'}
    ]

    rows_html = ""
    abnormal_details = []
    strabismus_val = str(person_data.get('ผ.สายตาเขซ่อนเร้น', '')).strip()

    for test in vision_tests:
        is_normal, is_abnormal = False, False
        result_text = ""
        status_text = "ไม่ได้
