import streamlit as st
import sqlite3
import requests
import pandas as pd
import io
import tempfile
import html  # ใช้สำหรับ html.escape()
import numpy as np
from collections import OrderedDict

def is_empty(val):
    return str(val).strip().lower() in ["", "-", "none", "nan", "null"]

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
        df = pd.read_sql("SELECT * FROM health_data", conn)
        conn.close()

        # Strip & แปลงชนิดข้อมูลสำคัญ
        df.columns = df.columns.str.strip()
        df['เลขบัตรประชาชน'] = df['เลขบัตรประชาชน'].astype(str).str.strip()
        df['HN'] = df['HN'].apply(lambda x: str(int(float(x))) if pd.notna(x) else "").str.strip()
        df['ชื่อ-สกุล'] = df['ชื่อ-สกุล'].astype(str).str.strip()
        df['Year'] = df['Year'].astype(int)

        # ปรับค่าที่หาย / แทนที่ - หรือ None
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
    /* ปิด scrollbar เฉพาะ markdown ทุกตัว */
    div.stMarkdown {
        overflow: visible !important;
    }

    /* ปิด scrollbar บน container ที่ Streamlit ห่อให้ */
    section.main > div {
        overflow-y: visible !important;
    }

    /* บังคับไม่ให้ wrap scroll container */
    [data-testid="stVerticalBlock"] {
        overflow: visible !important;
    }

    /* ปิด scrollbar ที่ WebKit (Chrome/Safari) */
    ::-webkit-scrollbar {
        width: 0px;
        background: transparent;
    }

    /* ปิด scrollbar ของ container markdown ที่แสดงผลแนะนำ */
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
        hn_cleaned = str(int(hn.strip()))
        query = query[query["HN"] == hn_cleaned]
    if full_name.strip():
        query = query[query["ชื่อ-สกุล"].str.strip() == full_name.strip()]

    # 🧹 Reset ปุ่มที่เคยเลือกไว้ก่อนหน้าทุกครั้งที่ค้นหาใหม่
    st.session_state.pop("selected_index", None)
    
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

    selected_hn = results_df.iloc[0]["HN"]  # ดึง HN ของคนที่ค้นเจอ

    person_year_df = results_df[
        (results_df["Year"] == selected_year) &
        (results_df["HN"] == selected_hn)
    ]

    person_year_df = person_year_df.drop_duplicates(subset=["HN", "วันที่ตรวจ"])

    exam_dates = person_year_df["วันที่ตรวจ"].dropna().unique()
    
    if len(exam_dates) > 1:
        for idx, row in person_year_df.iterrows():
            label = str(row["วันที่ตรวจ"]).strip() if pd.notna(row["วันที่ตรวจ"]) else f"ครั้งที่ {idx+1}"
            if st.button(label, key=f"checkup_{idx}"):
                st.session_state["person_row"] = row.to_dict()
                st.session_state["selected_row_found"] = True
    elif len(person_year_df) == 1:
        st.session_state["person_row"] = person_year_df.iloc[0].to_dict()
        st.session_state["selected_row_found"] = True

# ========== ฟังก์ชันวิเคราะห์ค่าต่าง ๆ (ต้องอยู่ก่อนเรียกใช้) ==========
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
        return "-"

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
        return "-"

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
    except:
        pass

    try:
        hct_val = float(hct)
        hct_ref = 39 if sex == "ชาย" else 36
        if hct_val < hct_ref:
            advice_parts.append("ค่าฮีมาโตคริตต่ำ ควรตรวจหาภาวะเลือดจางและตรวจติดตาม")
    except:
        pass

    try:
        wbc_val = float(wbc)
        if wbc_val < 4000:
            advice_parts.append("เม็ดเลือดขาวต่ำ อาจเกิดจากภูมิคุ้มกันลด ควรติดตาม")
        elif wbc_val > 10000:
            advice_parts.append("เม็ดเลือดขาวสูง อาจมีการอักเสบ ติดเชื้อ หรือความผิดปกติ ควรพบแพทย์")
    except:
        pass

    try:
        plt_val = float(plt)
        if plt_val < 150000:
            advice_parts.append("เกล็ดเลือดต่ำ อาจมีภาวะเลือดออกง่าย ควรตรวจยืนยันซ้ำ")
        elif plt_val > 500000:
            advice_parts.append("เกล็ดเลือดสูง ควรพบแพทย์เพื่อตรวจหาสาเหตุเพิ่มเติม")
    except:
        pass

    return " ".join(advice_parts)

# === เพิ่มฟังก์ชันตรงนี้ ===
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
        font-size: 20px;
        font-weight: bold;
        font-family: "Segoe UI", sans-serif;
        border-radius: 8px;
        margin-top: 2rem;
        margin-bottom: 1rem;
    '>
        {full_title}
    </div>
    """
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

    # แปลงให้ไม่มีทศนิยม
    try:
        sbp_int = int(float(sbp))
        dbp_int = int(float(dbp))
        bp_val = f"{sbp_int}/{dbp_int} ม.ม.ปรอท"
    except:
        sbp_int = dbp_int = None
        bp_val = "-"
    
    if sbp_int is None or dbp_int is None:
        bp_desc = "-"
        bp_full = "-"
    else:
        bp_desc = interpret_bp(sbp, dbp)
        bp_full = f"{bp_val} - {bp_desc}" if bp_desc != "-" else bp_val

    # ดึงค่าและแปลงชีพจรให้เป็นจำนวนเต็ม ไม่มีทศนิยม
    try:
        pulse_val = int(float(person.get("pulse", 0)))
    except:
        pulse_val = None

    pulse = f"{pulse_val} ครั้ง/นาที" if pulse_val is not None else "-"
    weight = f"{weight} กก." if not is_empty(weight) else "-"
    height = f"{height} ซม." if not is_empty(height) else "-"
    waist = f"{waist} ซม." if not is_empty(waist) else "-"

    advice_text = combined_health_advice(bmi_val, sbp, dbp)
    summary_advice = html.escape(advice_text) if advice_text else ""
    
    # ===== แสดงผล =====
    st.markdown(f"""
    <div style="font-size: 20px; line-height: 1.8; color: inherit; padding: 24px 8px;">
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
            <div><b>น้ำหนัก:</b> {weight}</div>
            <div><b>ส่วนสูง:</b> {height}</div>
            <div><b>รอบเอว:</b> {waist}</div>
            <div><b>ความดันโลหิต:</b> {bp_full}</div>
            <div><b>ชีพจร:</b> {pulse}</div>
        </div>
        {f"<div style='margin-top: 16px; text-align: center;'><b>คำแนะนำ:</b> {summary_advice}</div>" if summary_advice else ""}
    </div>
    """, unsafe_allow_html=True)

if "person_row" in st.session_state:
    person = st.session_state["person_row"]
    sex = str(person.get("เพศ", "")).strip()

    if sex not in ["ชาย", "หญิง"]:
        st.warning("⚠️ เพศไม่ถูกต้องหรือไม่มีข้อมูล กำลังใช้ค่าอ้างอิงเริ่มต้น")
        sex = "ไม่ระบุ"

    if sex == "หญิง":
        hb_low = 12
        hct_low = 36
    elif sex == "ชาย":
        hb_low = 13
        hct_low = 39
    else: # Default for "ไม่ระบุ" or other cases
        hb_low = 12
        hct_low = 36

    cbc_config = [
        ("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None, False),
        ("ฮีมาโทคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None, False),
        ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000),
        ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70),
        ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44),
        ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9),
        ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9),
        ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3),
        ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000),
    ]

    cbc_rows = []
    for label, col, norm, low, high, *opt in cbc_config:
        higher = opt[0] if opt else False
        val = get_float(col, person)
        result, is_abn = flag(val, low, high, higher)
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

    def render_lab_section(title, subtitle, headers, rows):
        style = """
        <style>
            .lab-container {
                background-color: var(--background-color);  /* ใช้สีจากธีม */
                margin-top: 1rem;
            }
            .lab-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 16px;
                font-family: "Segoe UI", sans-serif;
                color: var(--text-color);  /* แทน white */
            }
            .lab-table thead th {
                background-color: var(--secondary-background-color);
                color: var(--text-color);
                padding: 2px 4px;
                text-align: center;
                font-weight: bold;
                border: 1px solid transparent;
            }
            .lab-table td {
                padding: 2px 1px;
                border: 1px solid transparent;
                text-align: center;
            }
            .lab-abn {
                background-color: rgba(255, 64, 64, 0.25); /* สีแดงโปร่งแสง */
            }
            .lab-row {
                background-color: rgba(255,255,255,0.02);
            }
        </style>
        """
        html = f"""
        <div style='
            background-color: #1b5e20;
            color: white;
            text-align: center;
            padding: 1rem 0.5rem;
            font-size: 20px;
            font-weight: bold;
            font-family: "Segoe UI", sans-serif;
            border-radius: 8px;
            margin-bottom: 1rem;
        '>
            {title}<br><span style='font-size: 18px; font-weight: normal;'>({subtitle})</span>
        </div>
        """
        
        html += "<div class='lab-container'><table class='lab-table'>"
        html += "<thead><tr>"
        for i, h in enumerate(headers):
            align = "left" if i in [0, 2] else "center"
            html += f"<th style='text-align: {align};'>{h}</th>"
        html += "</tr></thead><tbody>"
        
        for row in rows:
            # Check if any item in the row is abnormal (assuming it's at index 1 of the tuple)
            is_abn = any(item[1] for item in row if isinstance(item, tuple) and len(item) > 1)
            row_class = "lab-abn" if is_abn else "lab-row"
            
            html += f"<tr>"
            html += f"<td class='{row_class}' style='text-align: left;'>{row[0][0]}</td>"  # การตรวจ
            html += f"<td class='{row_class}'>{row[1][0]}</td>"  # ผล
            html += f"<td class='{row_class}' style='text-align: left;'>{row[2][0]}</td>"  # ค่าปกติ
            html += f"</tr>"
        html += "</tbody></table></div>"
        return style + html

    left_spacer, col1, col2, right_spacer = st.columns([1, 3, 3, 1])

    with col1:
        st.markdown(render_lab_section("ผลตรวจ CBC", "Complete Blood Count", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_lab_section("ผลตรวจเคมีเลือด", "Blood Chemistry", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

    # ==================== รวมคำแนะนำ ====================
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

    def merge_final_advice_grouped(messages):
        groups = {
            "FBS": [], "ไต": [], "ตับ": [], "ยูริค": [], "ไขมัน": [], "อื่นๆ": []
        }

        for msg in messages:
            if not msg or msg.strip() in ["-", ""]:
                continue
            if "น้ำตาล" in msg:
                groups["FBS"].append(msg)
            elif "ไต" in msg:
                groups["ไต"].append(msg)
            elif "ตับ" in msg:
                groups["ตับ"].append(msg)
            elif "พิวรีน" in msg or "ยูริค" in msg:
                groups["ยูริค"].append(msg)
            elif "ไขมัน" in msg:
                groups["ไขมัน"].append(msg)
            else:
                groups["อื่นๆ"].append(msg)
        output = []
        for title, msgs in groups.items():
            if msgs:
                unique_msgs = list(OrderedDict.fromkeys(msgs))
                output.append(f"<b>{title}:</b> {' '.join(unique_msgs)}")
        if not output:
            return "ไม่พบคำแนะนำเพิ่มเติมจากผลตรวจ"

        return "<div style='margin-bottom: 0.75rem;'>" + "</div><div style='margin-bottom: 0.75rem;'>".join(output) + "</div>"

    spacer_l, main_col, spacer_r = st.columns([1, 6, 1])

    with main_col:
        final_advice_html = merge_final_advice_grouped(advice_list)
        has_advice = "ไม่พบคำแนะนำเพิ่มเติม" not in final_advice_html
        background_color = (
            "rgba(255, 215, 0, 0.15)" if has_advice else "rgba(200, 255, 200, 0.15)"
        )
        text_color = "var(--text-color)"
        
        st.markdown(f"""
        <div style="
            background-color: {background_color};
            padding: 1rem 2.5rem;
            border-radius: 10px;
            font-size: 16px;
            line-height: 1.5;
            color: var(--text-color);
        ">
            <div style="font-size: 18px; font-weight: bold; margin-bottom: 0.5rem;">
                📋 คำแนะนำจากผลตรวจสุขภาพ
            </div>
            {final_advice_html}
        </div>
        """, unsafe_allow_html=True)

    # ==================== Urinalysis Section ====================
    # This render_section_header is a duplicate, but kept for context as it was in the original snippet
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
            font-size: 20px;
            font-weight: bold;
            font-family: "Segoe UI", sans-serif;
            border-radius: 8px;
            margin-top: 2rem;
            margin-bottom: 1rem;
        '>
            {full_title}
        </div>
        """
        
    def safe_value(val):
        val = str(val or "").strip()
        if val.lower() in ["", "nan", "none", "-"]:
            return "-"
        return val
        
    with st.container():
        left_spacer_ua, col_ua_left, col_ua_right, right_spacer_ua = st.columns([1, 3, 3, 1])
        
    if "person_row" in st.session_state:
        person = st.session_state["person_row"]
        sex = person.get("เพศ", "-").strip()
        year_selected = person.get("Year", "-")
        
        alb_raw = person.get("Alb", "-")
        sugar_raw = person.get("sugar", "-")
        rbc_raw = person.get("RBC1", "-")
        wbc_raw = person.get("WBC1", "-")
        
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
                return "พบน้ำตาลในปัสสาวะ"
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
        
        urine_data = [
            ("สี (Colour)", safe_value(person.get("Color", "-")), "Yellow, Pale Yellow"),
            ("น้ำตาล (Sugar)", safe_value(sugar_raw), "Negative"),
            ("โปรตีน (Albumin)", safe_value(alb_raw), "Negative, trace"),
            ("กรด-ด่าง (pH)", safe_value(person.get("pH", "-")), "5.0 - 8.0"),
            ("ความถ่วงจำเพาะ (Sp.gr)", safe_value(person.get("Spgr", "-")), "1.003 - 1.030"),
            ("เม็ดเลือดแดง (RBC)", safe_value(rbc_raw), "0 - 2 cell/HPF"),
            ("เม็ดเลือดขาว (WBC)", safe_value(wbc_raw), "0 - 5 cell/HPF"),
            ("เซลล์เยื่อบุผิว (Squam.epit.)", safe_value(person.get("SQ-epi", "-")), "0 - 10 cell/HPF"),
            ("อื่นๆ", safe_value(person.get("ORTER", "-")), "-"),
        ]
        
        st.markdown("""
        <style>
            .urine-table, .lab-table {
                width: 100%;
                table-layout: fixed;
            }
            .urine-table td, .lab-table td {
                overflow-wrap: break-word;
            }
            .stMarkdown {
                overflow-x: auto;
            }
        </style>
        """, unsafe_allow_html=True)
        
        with col_ua_left:
            st.markdown(render_section_header("ผลการตรวจปัสสาวะ", "Urinalysis"), unsafe_allow_html=True)
            df_urine = pd.DataFrame(urine_data, columns=["การตรวจ", "ผลตรวจ", "ค่าปกติ"])
        
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
                    return "พบ" in interpret_rbc(val).lower() and "ปกติ" not in interpret_rbc(val).lower()
        
                if test_name == "เม็ดเลือดขาว (WBC)":
                    return "พบ" in interpret_wbc(val).lower() and "ปกติ" not in interpret_wbc(val).lower()
        
                if test_name == "น้ำตาล (Sugar)":
                    return interpret_sugar(val).lower() != "ไม่พบ"
        
                if test_name == "โปรตีน (Albumin)":
                    return interpret_alb(val).lower() != "ไม่พบ"
        
                if test_name == "สี (Colour)":
                    # For color, we might want to be less strict or list specific "normal" colors
                    # For now, if it's not a common normal color, flag it
                    normal_colors = ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"]
                    return val not in normal_colors
        
                return False
        
            def render_urine_html_table(df):
                html_table = """
                <style>
                    .urine-table {
                        width: 100%;
                        border-collapse: collapse;
                        font-size: 16px;
                        font-family: "Segoe UI", sans-serif;
                        color: var(--text-color);
                        margin-top: 1rem;
                    }
                    .urine-table th {
                        background-color: var(--secondary-background-color);
                        color: var(--text-color);
                        padding: 8px 4px;
                        text-align: center;
                        font-weight: bold;
                        border: 1px solid transparent;
                    }
                    .urine-table td {
                        padding: 8px 4px;
                        border: 1px solid transparent;
                        text-align: center;
                        vertical-align: top;
                    }
                    .urine-abn {
                        background-color: rgba(255, 64, 64, 0.25); /* สีแดงโปร่งแสง */
                    }
                    .urine-row {
                        background-color: rgba(255,255,255,0.02);
                    }
                </style>
                <div class='urine-container'>
                <table class='urine-table'>
                    <thead>
                        <tr>
                            <th style='width: 35%; text-align: left;'>การตรวจ</th>
                            <th style='width: 30%;'>ผลตรวจ</th>
                            <th style='width: 35%; text-align: left;'>ค่าปกติ</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                for index, row in df.iterrows():
                    test_name = row["การตรวจ"]
                    value = row["ผลตรวจ"]
                    normal_range = row["ค่าปกติ"]
                    is_abnormal = is_urine_abnormal(test_name, value, normal_range)
                    row_class = "urine-abn" if is_abnormal else "urine-row"
                    
                    html_table += f"""
                    <tr>
                        <td class='{row_class}' style='text-align: left;'>{html.escape(str(test_name))}</td>
                        <td class='{row_class}'>{html.escape(str(value))}</td>
                        <td class='{row_class}' style='text-align: left;'>{html.escape(str(normal_range))}</td>
                    </tr>
                    """
                html_table += """
                    </tbody>
                </table>
                </div>
                """
                return html_table
            
            st.markdown(render_urine_html_table(df_urine), unsafe_allow_html=True)
            
        with col_ua_right:
            st.markdown(render_section_header("คำแนะนำผลตรวจปัสสาวะ", "Urinalysis Advice"), unsafe_allow_html=True)
            urine_advice_text = advice_urine(
                sex,
                safe_value(person.get("Alb", "-")),
                safe_value(person.get("sugar", "-")),
                safe_value(person.get("RBC1", "-")),
                safe_value(person.get("WBC1", "-"))
            )
            
            if not urine_advice_text or urine_advice_text == "ควรตรวจปัสสาวะซ้ำเพื่อติดตามผล":
                advice_bg_color = "rgba(200, 255, 200, 0.15)" # Greenish for normal/no specific advice
                display_advice = urine_advice_text if urine_advice_text else "ไม่พบคำแนะนำเพิ่มเติมสำหรับผลตรวจปัสสาวะนี้"
            else:
                advice_bg_color = "rgba(255, 215, 0, 0.15)" # Yellowish for advice needed
                display_advice = urine_advice_text
            
            st.markdown(f"""
            <div style="
                background-color: {advice_bg_color};
                padding: 1rem 1.5rem;
                border-radius: 10px;
                font-size: 16px;
                line-height: 1.5;
                color: var(--text-color);
                height: 100%; /* Ensure it fills the column height */
                display: flex;
                align-items: center;
                justify-content: center;
                text-align: center;
            ">
                {html.escape(display_advice)}
            </div>
            """, unsafe_allow_html=True)
