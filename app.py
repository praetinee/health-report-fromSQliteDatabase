import streamlit as st
import sqlite3
import requests
import pandas as pd
import io
import tempfile
import html  # ใช้สำหรับ html.escape()

@st.cache_data(ttl=600)
def load_sqlite_data():
    try:
        file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url)
        response.raise_for_status()

        # บันทึกไฟล์ลง temp file เพื่อให้ sqlite3 อ่านได้
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        tmp.write(response.content)
        tmp.flush()
        tmp.close()

        conn = sqlite3.connect(tmp.name)
        df = pd.read_sql_query("SELECT * FROM health_data", conn)
        conn.close()

        # Strip & แปลงชนิดข้อมูลสำคัญ
        df.columns = df.columns.str.strip()
        df['เลขบัตรประชาชน'] = df['เลขบัตรประชาชน'].astype(str).str.strip()
        df['HN'] = df['HN'].astype(str).str.strip()
        df['ชื่อ-สกุล'] = df['ชื่อ-สกุล'].astype(str).str.strip()
        df['Year'] = df['Year'].astype(int)

        # ปรับค่าที่หาย / แทนที่ - หรือ None
        df.replace(["-", "None", None], pd.NA, inplace=True)

        return df
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        st.stop()

df = load_sqlite_data()

# ==================== UI SEARCH FORM ====================
st.markdown("<h1 style='text-align:center;'>ระบบรายงานผลตรวจสุขภาพ</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray;'>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม รพ.สันทราย -</h4>", unsafe_allow_html=True)

with st.form("search_form"):
    col1, col2, col3 = st.columns(3)
    id_card = col1.text_input("เลขบัตรประชาชน")
    hn = col2.text_input("HN")
    full_name = col3.text_input("ชื่อ-สกุล")
    submitted = st.form_submit_button("ค้นหา")

if submitted:
    query = df.copy()

    if id_card.strip():
        query = query[query["เลขบัตรประชาชน"] == id_card.strip()]
    if hn.strip():
        try:
            hn_val = float(hn.strip())
            query = query[np.isclose(query["HN"], hn_val)]
        except ValueError:
            st.error("❌ HN ต้องเป็นตัวเลข เช่น 12345 หรือ 100.0")
            st.stop()
    if full_name.strip():
        query = query[query["ชื่อ-สกุล"].str.strip() == full_name.strip()]

    if query.empty:
        st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
        st.session_state.pop("search_result", None)
    else:
        st.session_state["search_result"] = query

# ==================== SELECT YEAR FROM RESULTS ====================
if "search_result" in st.session_state:
    results_df = st.session_state["search_result"]

    available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
    selected_year = st.selectbox(
        "📅 เลือกปีที่ต้องการดูผลตรวจรายงาน", 
        options=available_years,
        format_func=lambda y: f"พ.ศ. {y}"
    )

    # ดึงข้อมูลเฉพาะปีที่เลือก
    person_year_df = results_df[results_df["Year"] == selected_year]

    # ถ้ามีมากกว่า 1 วันที่ตรวจในปีเดียวกัน → แสดงปุ่มเลือกครั้ง
    exam_dates = person_year_df["วันที่ตรวจ"].dropna().unique()
    if len(person_year_df) > 1:
        date_buttons = []
        for idx, row in person_year_df.iterrows():
            label = row["วันที่ตรวจ"] if pd.notna(row["วันที่ตรวจ"]) else f"ครั้งที่ {idx+1}"
            if st.button(label, key=f"checkup_{idx}"):
                st.session_state["person_row"] = row.to_dict()
    else:
        st.session_state["person_row"] = person_year_df.iloc[0].to_dict()

if "person_row" in st.session_state:
    person = st.session_state["person_row"]
    year_display = person.get("Year", "-")

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
        try:
            bmi = float(bmi)
        except:
            bmi = None
        try:
            sbp = float(sbp)
            dbp = float(dbp)
        except:
            sbp = dbp = None

        if bmi is None:
            bmi_text = ""
        elif bmi > 30:
            bmi_text = "น้ำหนักเกินมาตรฐานมาก"
        elif bmi >= 25:
            bmi_text = "น้ำหนักเกินมาตรฐาน"
        elif bmi < 18.5:
            bmi_text = "น้ำหนักน้อยกว่ามาตรฐาน"
        else:
            bmi_text = "น้ำหนักอยู่ในเกณฑ์ปกติ"

        if sbp is None or dbp is None:
            bp_text = ""
        elif sbp >= 160 or dbp >= 100:
            bp_text = "ความดันโลหิตอยู่ในระดับสูงมาก"
        elif sbp >= 140 or dbp >= 90:
            bp_text = "ความดันโลหิตอยู่ในระดับสูง"
        elif sbp >= 120 or dbp >= 80:
            bp_text = "ความดันโลหิตเริ่มสูง"
        else:
            bp_text = ""

        if not bmi_text and not bp_text:
            return "ไม่พบข้อมูลเพียงพอในการประเมินสุขภาพ"
        if "ปกติ" in bmi_text and not bp_text:
            return "น้ำหนักอยู่ในเกณฑ์ดี ควรรักษาพฤติกรรมสุขภาพนี้ต่อไป"
        if not bmi_text and bp_text:
            return f"{bp_text} แนะนำให้ดูแลสุขภาพ และติดตามค่าความดันอย่างสม่ำเสมอ"
        if bmi_text and bp_text:
            return f"{bmi_text} และ {bp_text} แนะนำให้ปรับพฤติกรรมด้านอาหารและการออกกำลังกาย"
        return f"{bmi_text} แนะนำให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"

    # ===== ดึงข้อมูลหลัก =====
    sbp = person.get("SBP", "")
    dbp = person.get("DBP", "")
    pulse = person.get("pulse", "-")
    weight = person.get("น้ำหนัก", "-")
    height = person.get("ส่วนสูง", "-")
    waist = person.get("รอบเอว", "-")
    check_date = person.get("วันที่ตรวจ", "-")

    try:
        weight_val = float(str(weight).replace("กก.", "").strip())
        height_val = float(str(height).replace("ซม.", "").strip())
        bmi_val = weight_val / ((height_val / 100) ** 2)
    except:
        bmi_val = None

    sbp_val = f"{sbp}/{dbp} ม.ม.ปรอท" if sbp and dbp else "-"
    bp_desc = interpret_bp(sbp, dbp)
    bp_full = f"{sbp_val} - {bp_desc}" if bp_desc != "-" else sbp_val

    pulse = f"{pulse} ครั้ง/นาที" if pulse not in ["-", None, "nan"] else "-"
    weight = f"{weight} กก." if weight not in ["-", None, "nan"] else "-"
    height = f"{height} ซม." if height not in ["-", None, "nan"] else "-"
    waist = f"{waist} ซม." if waist not in ["-", None, "nan"] else "-"

    summary_advice = html.escape(combined_health_advice(bmi_val, sbp, dbp))

    # ===== แสดงผล =====
    st.markdown(f"""
    <div style="font-size: 18px; line-height: 1.8; color: inherit; padding: 24px 8px;">
        <div style="text-align: center; font-size: 22px; font-weight: bold;">รายงานผลการตรวจสุขภาพ</div>
        <div style="text-align: center;">วันที่ตรวจ: {check_date or "-"}</div>
        <div style="text-align: center; margin-top: 10px;">
            โรงพยาบาลสันทราย 201 หมู่ที่ 11 ถนน เชียงใหม่ - พร้าว<br>
            ตำบลหนองหาร อำเภอสันทราย เชียงใหม่ 50290 โทร 053 921 199 ต่อ 167
        </div>
        <hr style="margin: 24px 0;">
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 20px; text-align: center;">
            <div><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</div>
            <div><b>อายุ:</b> {person.get('อายุ', '-')} ปี</div>
            <div><b>เพศ:</b> {person.get('เพศ', '-')}</div>
            <div><b>HN:</b> {person.get('HN', '-')}</div>
            <div><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</div>
        </div>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 16px; text-align: center;">
            <div><b>น้ำหนัก:</b> {weight}</div>
            <div><b>ส่วนสูง:</b> {height}</div>
            <div><b>รอบเอว:</b> {waist}</div>
            <div><b>ความดันโลหิต:</b> {bp_full}</div>
            <div><b>ชีพจร:</b> {pulse}</div>
        </div>
        <div style="margin-top: 16px; text-align: center;">
            <b>คำแนะนำ:</b> {summary_advice}
        </div>
    </div>
    """, unsafe_allow_html=True)
