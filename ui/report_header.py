import streamlit as st
from utils import format_thai_date, get_float  # ✅ ใช้ format_thai_date + get_float
st.markdown(f"วันที่ตรวจ: {format_thai_date(person['วันที่ตรวจ'])}")

def render_report_header(person):
    date = format_thai_date(person["วันที่ตรวจ"])  # ✅ แปลงวันที่ให้เป็น พ.ศ.
    name = person["ชื่อ-สกุล"]
    age = int(float(person["อายุ"]))
    gender = person["เพศ"]
    hn = person["HN"]
    org = person["หน่วยงาน"]
    weight = person["น้ำหนัก"]
    height = person["ส่วนสูง"]
    waist = person["รอบเอว"]
    sbp = get_float("SBP", person)
    dbp = get_float("DBP", person)
    pulse = get_float("pulse", person)
    advice = person.get("สรุปความดัน", "")

    st.markdown(
        f"""
        <div style="text-align: center; font-size: 18px; font-weight: bold;">
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

        <div style="font-size: 16px;">
            <b>ชื่อ-สกุล:</b> {name} &nbsp;&nbsp;
            <b>อายุ:</b> {age} ปี &nbsp;&nbsp;
            <b>เพศ:</b> {gender} &nbsp;&nbsp;
            <b>HN:</b> {hn}
        </div>

        <div>
            <b>หน่วยงาน:</b> {org}
        </div>

        <div>
            <b>น้ำหนัก:</b> {weight} กก. &nbsp;&nbsp;
            <b>ส่วนสูง:</b> {height} ซม. &nbsp;&nbsp;
            <b>รอบเอว:</b> {waist} ซม.
        </div>

        <div>
            <b>ความดันโลหิต:</b> {sbp}/{dbp} มม.ปรอท &nbsp;&nbsp;
            <b>ชีพจร:</b> {pulse} ครั้ง/นาที
        </div>

        <div style="margin-top: 0.5rem;">
            <b>คำแนะนำ:</b> {advice if advice else "-"}
        </div>
        """,
        unsafe_allow_html=True
    )
