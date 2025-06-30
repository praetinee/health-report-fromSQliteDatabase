import streamlit as st
import sqlite3
import requests
import pandas as pd
import io
import tempfile
import html  # ใช้สำหรับ html.escape()
import numpy as np

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
            query = query[query["HN"].astype(float).apply(lambda x: np.isclose(x, hn_val))]
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

# ==================== เตรียมข้อมูลจาก SQLite ====================

if "person_row" in st.session_state:
    person = st.session_state["person_row"]
    sex = str(person.get("เพศ", "")).strip()

    def get_float(col):
        try:
            val = person.get(col, "")
            if val in [None, "-", ""]:
                return None
            return float(str(val).replace(",", "").strip())
        except:
            return None

    def flag(val, low=None, high=None, higher_is_better=False):
        if val is None:
            return "-", False
        if higher_is_better:
            return f"{val:.1f}", val < low
        if (low is not None and val < low) or (high is not None and val > high):
            return f"{val:.1f}", True
        return f"{val:.1f}", False

# ==================== ดึงค่าตรวจ CBC ====================
# ค่ามาตรฐานต่างเพศ
hb_low = 12 if sex == "หญิง" else 13
hct_low = 36 if sex == "หญิง" else 39

cbc_config = [
    ("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None),
    ("ฮีมาโทคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None),
    ("เม็ดเลือดขาว (WBC)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000),
    ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000),
]

cbc_rows = []
for label, col, norm, low, high in cbc_config:
    val = get_float(col)
    result, is_abn = flag(val, low, high)
    cbc_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])

# ==================== ตรวจเคมีเลือดทั่วไป (Blood Chemistry) ====================
blood_config = [
    ("FBS", "FBS", "74 - 106 mg/dl", 74, 106),
    ("Uric Acid", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2),
    ("ALK", "ALP", "30 - 120 U/L", 30, 120),
    ("SGOT", "SGOT", "< 37 U/L", None, 37),
    ("SGPT", "SGPT", "< 41 U/L", None, 41),
    ("CHOL", "CHOL", "150 - 200 mg/dl", 150, 200),
    ("TGL", "TGL", "35 - 150 mg/dl", 35, 150),
    ("HDL", "HDL", "> 40 mg/dl", 40, None, True),
    ("LDL", "LDL", "0 - 160 mg/dl", 0, 160),
    ("BUN", "BUN", "7.9 - 20 mg/dl", 7.9, 20),
    ("Cr", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17),
    ("GFR", "GFR", "> 60 mL/min", 60, None, True),
]

blood_rows = []
for label, col, norm, low, high, *opt in blood_config:
    higher = opt[0] if opt else False
    val = get_float(col)
    result, is_abn = flag(val, low, high, higher)
    blood_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])

# ==================== ตาราง Styled Result Table ====================
def styled_result_table(headers, rows):
    header_html = "".join([f"<th>{h}</th>" for h in headers])
    html_out = f"""
    <style>
        .styled-wrapper {{
            max-width: 820px; margin: 0 auto;
        }}
        .styled-result {{
            width: 100%; border-collapse: collapse;
        }}
        .styled-result th {{
            background-color: #111; color: white;
            padding: 6px 12px; text-align: center;
        }}
        .styled-result td {{
            padding: 6px 12px; vertical-align: middle;
        }}
        .styled-result td:nth-child(2) {{
            text-align: center;
        }}
        .abn {{
            background-color: rgba(255, 0, 0, 0.15);
        }}
    </style>
    <div class="styled-wrapper">
        <table class='styled-result'>
            <thead><tr>{header_html}</tr></thead>
            <tbody>
    """
    for row in rows:
        row_html = ""
        for cell, is_abn in row:
            css = " class='abn'" if is_abn else ""
            row_html += f"<td{css}>{cell}</td>"
        html_out += f"<tr>{row_html}</tr>"
    html_out += "</tbody></table></div>"
    return html_out

# ==================== แสดงผลบนหน้า Streamlit ====================
left_spacer, col1, col2, right_spacer = st.columns([1, 3, 3, 1])

with col1:
    st.markdown("<h4>ผลตรวจ CBC</h4>", unsafe_allow_html=True)
    st.markdown(styled_result_table(["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)

with col2:
    st.markdown("<h4>ผลตรวจเคมีเลือด</h4>", unsafe_allow_html=True)
    st.markdown(styled_result_table(["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

# ==================== วิเคราะห์ GFR → ไต ====================
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

# ==================== วิเคราะห์ FBS → น้ำตาล ====================
def fbs_advice(fbs_raw):
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

# ==================== วิเคราะห์ Liver Function (ALP, SGOT, SGPT) ====================
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

# ==================== วิเคราะห์ Uric Acid ====================
def uric_acid_advice(value_raw):
    try:
        value = float(value_raw)
        if value > 7.2:
            return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
        return ""
    except:
        return "-"

# ==================== วิเคราะห์ ไขมันในเลือด (CHOL, TGL, LDL) ====================
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

# ==================== คำแนะนำหมวด CBC ====================
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

# ==================== รวมคำแนะนำทั้งหมด ====================
sex = str(person.get("เพศ", "")).strip()  # ✅ ประกาศ sex ให้ใช้ได้ใน logic CBC
advice_list = []

# 🔍 ดึงค่าดิบ
gfr_raw = person.get("GFR", "")
fbs_raw = person.get("FBS", "")
alp_raw = person.get("ALP", "")
sgot_raw = person.get("SGOT", "")
sgpt_raw = person.get("SGPT", "")
uric_raw = person.get("Uric Acid", "")
chol_raw = person.get("CHOL", "")
tgl_raw = person.get("TGL", "")
ldl_raw = person.get("LDL", "")

# 📋 วิเคราะห์คำแนะนำ
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

# ==================== แสดงผลรวมคำแนะนำ ====================
from collections import OrderedDict

def merge_final_advice_grouped(messages):
    groups = {
        "FBS": [], "ไต": [], "ตับ": [], "ยูริค": [], "ไขมัน": [], "อื่นๆ": []
    }

    for msg in messages:
        if not msg or msg == "-" or msg.strip() == "":
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

    section_texts = []
    icon_map = {
        "FBS": "🍬", "ไต": "💧", "ตับ": "🫀",
        "ยูริค": "🦴", "ไขมัน": "🧈", "อื่นๆ": "📝"
    }
    for title, msgs in groups.items():
        if msgs:
            unique_msgs = list(OrderedDict.fromkeys(msgs))
            section_texts.append(f"<b>{icon_map.get(title)} {title}:</b> {' '.join(unique_msgs)}")

    if not section_texts:
        return "ไม่พบคำแนะนำเพิ่มเติมจากผลตรวจ"

    return "<div style='margin-bottom: 0.75rem;'>" + "</div><div style='margin-bottom: 0.75rem;'>".join(section_texts) + "</div>"

# แสดงผล
st.markdown(f"""
<div style="
    background-color: rgba(33, 150, 243, 0.15);
    padding: 2rem 2.5rem;
    border-radius: 10px;
    font-size: 16px;
    line-height: 1.5;
    color: inherit;
">
    <div style="font-size: 18px; font-weight: bold; margin-bottom: 1.5rem;">
        📋 คำแนะนำจากผลตรวจสุขภาพ
    </div>
    {merge_final_advice_grouped(advice_list)}
</div>
""", unsafe_allow_html=True)
