import sys
import os

# ✅ เพิ่ม path โฟลเดอร์หลัก เพื่อให้ Python หา utils.py ได้
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import streamlit as st

try:
    from utils import format_thai_date, parse_date_thai, get_float
except ImportError as e:
    st.error(f"❌ ไม่สามารถ import 'utils.py' ได้: {e}")
    st.stop()

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
    advice = person.get("สรุปความดัน", "")

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
        <div><b>ความดันโลหิต:</b> {sbp}/{dbp} มม.ปรอท</div>
        <div><b>ชีพจร:</b> {pulse} ครั้ง/นาที</div>
    </div>

    <div style="margin-top: 0.5rem; text-align: center;">
        <b>คำแนะนำ:</b> {advice if advice else "-"}
    </div>
    """, unsafe_allow_html=True)
