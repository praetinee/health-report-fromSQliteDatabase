import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import streamlit as st
from utils import format_thai_date, parse_date_thai, get_float

def interpret_bp(sbp, dbp):
    if sbp is None or dbp is None:
        return "-"
    if sbp < 120 and dbp < 80:
        return "ความดันปกติ"
    elif 120 <= sbp < 130 and dbp < 80:
        return "ความดันเริ่มสูง"
    elif 130 <= sbp or dbp >= 80:
        return "ความดันโลหิตสูง"
    return "-"

def render_report_header(person):
    raw_date = parse_date_thai(person["วันที่ตรวจ"])
    date = format_thai_date(raw_date)

    name = person["ชื่อ-สกุล"]
    age = int(float(person["อายุ"]))
    gender = person["เพศ"]
    hn = person["HN"]
    hn_display = str(int(float(hn))) if hn else "-"
    org = person["หน่วยงาน"]
    weight = person["น้ำหนัก"]
    height = person["ส่วนสูง"]
    waist = person["รอบเอว"]
    sbp = get_float("SBP", person)
    dbp = get_float("DBP", person)
    pulse = get_float("pulse", person)

    # ➕ แปลความดัน
    bp_interpret = interpret_bp(sbp, dbp)

    # ✅ แสดงค่ารูปแบบตามที่ระบุ
    try:
        weight = f"{float(weight):.1f}"
        height = f"{float(height):.1f}"
        waist = f"{float(waist):.1f}"
        sbp = f"{float(sbp):.0f}" if sbp is not None else "-"
        dbp = f"{float(dbp):.0f}" if dbp is not None else "-"
        pulse = f"{float(pulse):.0f}" if pulse is not None else "-"
    except:
        pass

    st.markdown(f"""
    <div style="text-align: center; font-size: 20px; font-weight: bold;">
        รายงานผลการตรวจสุขภาพ
    </div>
    <div style="text-align: center; margin-bottom: 1rem;">
        วันที่ตรวจ: {date}
    </div>
    <div style="text-align: center;">
        โรงพยาบาลสันทราย 201 หมู่ที่ 11 ถนน เชียงใหม่ - พร้าว<br>
        ตำบลหนองหาร อำเภอสันทราย เชียงใหม่ 50290 โทร 053 921 199 ต่อ 167
    </div>
    <hr style="margin: 1.5rem 0;">
    
    <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap; font-size: 16px;">
        <div><b>ชื่อ-สกุล:</b> {name}</div>
        <div><b>อายุ:</b> {age} ปี</div>
        <div><b>เพศ:</b> {gender}</div>
        <div><b>HN:</b> {hn_display}</div>
        <div><b>หน่วยงาน:</b> {org}</div>
    </div>

    <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap; margin-top: 1rem;">
        <div><b>น้ำหนัก:</b> {weight} กก.</div>
        <div><b>ส่วนสูง:</b> {height} ซม.</div>
        <div><b>รอบเอว:</b> {waist} ซม.</div>
        <div><b>ความดันโลหิต:</b> {sbp}/{dbp} - {bp_interpret}</div>
        <div><b>ชีพจร:</b> {pulse} ครั้ง/นาที</div>
    </div>
    """, unsafe_allow_html=True)
