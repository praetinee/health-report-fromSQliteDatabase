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

    # ==================== เตรียมข้อมูลจาก SQLite ====================

# ฟังก์ชันช่วยประเมินค่าตรวจทางห้องแล็บ (ใช้ได้ทุกกลุ่ม)
def get_float(col, person_data):
    try:
        val = person_data.get(col, "")
        if is_empty(val):
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

    def is_empty(val):
        return str(val).strip().lower() in ["", "-", "none", "nan"]
    
    pulse = f"{pulse} ครั้ง/นาที" if not is_empty(pulse) else "-"
    weight = f"{weight} กก." if not is_empty(weight) else "-"
    height = f"{height} ซม." if not is_empty(height) else "-"
    waist = f"{waist} ซม." if not is_empty(waist) else "-"

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

# ฟังก์ชันช่วยประเมินค่าตรวจทางห้องแล็บ (ใช้ได้ทุกกลุ่ม)
def get_float(col, person_data):
    try:
        val = person_data.get(col, "")
        if is_empty(val):
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
    else:
        hb_low = 12
        hct_low = 36

    cbc_config = [
        ("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None),
        ("ฮีมาโทคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None),
        ("เม็ดเลือดขาว (WBC)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000),
        ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000),
    ]

    cbc_rows = []
    for label, col, norm, low, high in cbc_config:
        val = get_float(col, person)
        result, is_abn = flag(val, low, high)
        cbc_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])

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
        val = get_float(col, person)
        result, is_abn = flag(val, low, high, higher)
        blood_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])

    def render_lab_section(title, subtitle, headers, rows):
        style = """
        <style>
            .lab-container {
                background-color: #111;
                margin-top: 1rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.4);
            }
            .lab-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 16px;
                font-family: "Segoe UI", sans-serif;
            }
            .lab-table thead th {
                background-color: #1c1c1c;
                color: white;
                padding: 12px;
                text-align: center;
                font-weight: bold;
            }
            .lab-table td {
                padding: 12px;
                border: 1px solid #333;
                text-align: center;
                color: white;
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
        html += "<thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead><tbody>"
    
        for row in rows:
            is_abn = any(flag for _, flag in row)
            row_class = "lab-abn" if is_abn else "lab-row"
            html += "<tr>" + "".join(f"<td class='{row_class}'>{cell}</td>" for cell, _ in row) + "</tr>"
    
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

    from collections import OrderedDict

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

        icon_map = {
            "FBS": "🍬", "ไต": "💧", "ตับ": "🫀",
            "ยูริค": "🦴", "ไขมัน": "🧈", "อื่นๆ": "📝"
        }

        output = []
        for title, msgs in groups.items():
            if msgs:
                unique_msgs = list(OrderedDict.fromkeys(msgs))
                output.append(f"<b>{icon_map.get(title)} {title}:</b> {' '.join(unique_msgs)}")

        if not output:
            return "ไม่พบคำแนะนำเพิ่มเติมจากผลตรวจ"

        return "<div style='margin-bottom: 0.75rem;'>" + "</div><div style='margin-bottom: 0.75rem;'>".join(output) + "</div>"

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

    # ==================== Urinalysis Section ====================

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
    
        def interpret_rbc(value):
            val = str(value).strip().lower()
            if val in ["0-1", "negative", "1-2", "2-3", "3-5"]:
                return "ปกติ"
            elif val in ["5-10", "10-20"]:
                return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
            elif val not in ["-", "none", "nan", ""]:
                return "พบเม็ดเลือดแดงในปัสสาวะ"
            return "-"
    
        def interpret_wbc(value):
            val = str(value).strip().lower()
            if val in ["0-1", "negative", "1-2", "2-3", "3-5"]:
                return "ปกติ"
            elif val in ["5-10", "10-20"]:
                return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
            elif val not in ["-", "none", "nan", ""]:
                return "พบเม็ดเลือดขาวในปัสสาวะ"
            return "-"
    
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
            ("สี (Colour)", person.get("Color", "-"), "Yellow, Pale Yellow"),
            ("น้ำตาล (Sugar)", sugar_raw, "Negative"),
            ("โปรตีน (Albumin)", alb_raw, "Negative, trace"),
            ("กรด-ด่าง (pH)", person.get("pH", "-"), "5.0 - 8.0"),
            ("ความถ่วงจำเพาะ (Sp.gr)", person.get("Spgr", "-"), "1.003 - 1.030"),
            ("เม็ดเลือดแดง (RBC)", rbc_raw, "0 - 2 cell/HPF"),
            ("เม็ดเลือดขาว (WBC)", wbc_raw, "0 - 5 cell/HPF"),
            ("เซลล์เยื่อบุผิว (Squam.epit.)", person.get("SQ-epi", "-"), "0 - 10 cell/HPF"),
            ("อื่นๆ", person.get("ORTER", "-"), "-"),
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

        df_urine = pd.DataFrame(urine_data, columns=["ชื่อการตรวจ", "ผลตรวจ", "ค่าปกติ"])
    
        def render_urine_html_table(df):
            style = """
            <style>
                .urine-container {
                    background-color: #111;
                    margin-top: 1rem;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.4);
                }
                .urine-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 16px;
                    font-family: "Segoe UI", sans-serif;
                }
                .urine-table thead th {
                    background-color: #1c1c1c;
                    color: white;
                    padding: 12px;
                    text-align: center;
                    font-weight: bold;
                }
                .urine-table td {
                    padding: 12px;
                    border: 1px solid #333;
                    text-align: center;
                    color: white;
                }
                .urine-abn {
                    background-color: rgba(255, 64, 64, 0.25); /* สีแดงโปร่งแสง */
                }
                .urine-row {
                    background-color: rgba(255,255,255,0.02);
                }
            </style>
            """
            html = "<div class='urine-container'><table class='urine-table'>"
            html += "<thead><tr><th>ชื่อการตรวจ</th><th>ผลตรวจ</th><th>ค่าปกติ</th></tr></thead><tbody>"
    
            for _, row in df.iterrows():
                val = str(row["ผลตรวจ"]).strip().lower()
                is_abnormal = val not in [
                    "-", "negative", "trace", "0", "none", "yellow", "pale yellow",
                    "0-1", "0-2", "1.01", "1.015", "1.02", "1.025", "1.03"
                ]
                css_class = "urine-abn" if is_abnormal else "urine-row"
                html += f"<tr class='{css_class}'><td>{row['ชื่อการตรวจ']}</td><td>{row['ผลตรวจ']}</td><td>{row['ค่าปกติ']}</td></tr>"
    
            html += "</tbody></table></div>"
            return style + html
    
        st.markdown(render_urine_html_table(df_urine), unsafe_allow_html=True)
    
        summary = advice_urine(sex, alb_raw, sugar_raw, rbc_raw, wbc_raw)
        if summary:
            st.markdown(f"""
            <div style='
                background-color: rgba(255, 215, 0, 0.2);
                padding: 1rem;
                border-radius: 6px;
                margin-top: 1rem;
                font-size: 16px;
            '>
                <b>📌 คำแนะนำจากผลตรวจปัสสาวะ ปี {year_selected}:</b><br>{summary}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.success("ผลตรวจปัสสาวะอยู่ในเกณฑ์ปกติ ไม่มีคำแนะนำเพิ่มเติม")

    # ==================== Stool Section ====================
    def render_section_header(title, subtitle=None):
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
            {title}{'<br><span style="font-size: 18px; font-weight: normal;">(' + subtitle + ')</span>' if subtitle else ''}
        </div>
        """
    
    def interpret_stool_exam(val):
        val = str(val or "").strip().lower()
        if val in ["", "-", "none", "nan"]:
            return "-"
        elif val == "normal":
            return "ไม่พบเม็ดเลือดขาวในอุจจาระ ถือว่าปกติ"
        elif "wbc" in val or "เม็ดเลือดขาว" in val:
            return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
        return val
    
    def interpret_stool_cs(value):
        value = str(value or "").strip()
        if value in ["", "-", "none", "nan"]:
            return "-"
        if "ไม่พบ" in value or "ปกติ" in value:
            return "ไม่พบการติดเชื้อ"
        return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"
    
    # ✅ ดึงค่าดิบจากฐานข้อมูล
    stool_exam_raw = person.get("Stool exam", "")
    stool_cs_raw = person.get("Stool C/S", "")
    
    exam_text = interpret_stool_exam(stool_exam_raw)
    cs_text = interpret_stool_cs(stool_cs_raw)
    
    # ✅ แสดงหัวตาราง
    st.markdown(render_section_header("ผลตรวจอุจจาระ", "Stool Examination"), unsafe_allow_html=True)
    
    # ✅ แสดงผล
    st.markdown(f"""
    <div style='
        font-size: 16px;
        line-height: 1.7;
        margin-bottom: 1rem;
        background-color: #111;
        padding: 1rem;
        border-radius: 6px;
        color: white;
    '>
        <table style='width: 100%; border-collapse: collapse;'>
            <tr>
                <td style='padding: 8px; border: 1px solid #333;'><b>ผลตรวจอุจจาระทั่วไป</b></td>
                <td style='padding: 8px; border: 1px solid #333;'>{exam_text if exam_text != "-" else "ไม่ได้เข้ารับการตรวจ"}</td>
            </tr>
            <tr>
                <td style='padding: 8px; border: 1px solid #333;'><b>ผลตรวจอุจจาระเพาะเชื้อ</b></td>
                <td style='padding: 8px; border: 1px solid #333;'>{cs_text if cs_text != "-" else "ไม่ได้เข้ารับการตรวจ"}</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    with col_ua_right:
        # ============ X-ray Section ============
        
        # ✅ หัวตารางเอกซเรย์
        st.markdown(render_section_header("ผลเอกซเรย์", "Chest X-ray"), unsafe_allow_html=True)
    
        # ✅ ตรวจว่าเป็นค่าว่างหรือไม่
        def is_empty(val):
            return str(val).strip().lower() in ["", "-", "none", "nan"]
    
        # ✅ ฟังก์ชันแปลผลเอกซเรย์
        def interpret_cxr(val):
            val = str(val or "").strip()
            if is_empty(val):
                return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
            if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]):
                return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
            return val
    
        # ✅ ดึงชื่อคอลัมน์ CXR ตามปี
        selected_year_int = int(selected_year)
        cxr_col = "CXR" if selected_year_int == 2568 else f"CXR{str(selected_year_int)[-2:]}"
        cxr_raw = person.get(cxr_col, "")
        cxr_result = interpret_cxr(cxr_raw)
    
        # ✅ แสดงผล
        st.markdown(f"""
        <div style='
            background-color: #111;
            color: white;
            font-size: 16px;
            line-height: 1.6;
            padding: 1.25rem;
            border-radius: 6px;
            margin-bottom: 1.5rem;
        '>
            <b>ผลการตรวจ:</b> {cxr_result}
        </div>
        """, unsafe_allow_html=True)
