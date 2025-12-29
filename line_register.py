import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests # ใช้ requests แทน gspread
from datetime import datetime
import json
import os
import time

# --- Constants ---
LIFF_ID = "2008725340-YHOiWxtj"

# ✅ URL ของ Google Apps Script Web App (ใส่ให้แล้วครับ)
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbw0Dq-kZ2EfQtMSed-qbvt-2u2p4xASbKDVOa96sVAOBYbvLHIR7nKoMw8NSWWNIodb/exec"

# --- API Helper Functions ---
# ฟังก์ชันคุยกับ Google Apps Script แทนการต่อ GSheet ตรงๆ

def get_all_users_from_api():
    """ดึงข้อมูล User ทั้งหมดผ่าน Web App URL"""
    try:
        # เรียกข้อมูลด้วย GET request
        response = requests.get(WEB_APP_URL, params={"action": "read"}, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            # ตรวจสอบว่า API ส่ง Error กลับมาหรือไม่
            if isinstance(data, dict) and data.get("result") == "error":
                st.error(f"Google Script Error: {data.get('message')}")
                return []
            return data # คืนค่าเป็น List of Dicts
        else:
            st.error(f"API HTTP Error: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        st.error(f"Connection Error (Read): {e}")
        return []

def save_user_to_api(fname, lname, line_user_id, id_card=""):
    """ส่งข้อมูลไปบันทึกผ่าน Web App URL"""
    try:
        payload = {
            "action": "write",
            "fname": fname,
            "lname": lname,
            "line_id": line_user_id,
            "card_id": id_card
        }
        # ใช้ POST request เพื่อส่งข้อมูล
        response = requests.post(WEB_APP_URL, params=payload, timeout=15)
        
        if response.status_code == 200:
            res_json = response.json()
            if res_json.get("result") == "success":
                return True, "บันทึกข้อมูลเรียบร้อยแล้ว"
            else:
                return False, f"Script Error: {res_json.get('message')}"
        else:
            return False, f"HTTP Error: {response.status_code}"
    except Exception as e:
        return False, f"Write Error: {e}"


# --- User Management (Updated to use API) ---
def check_if_user_registered(line_user_id):
    try:
        users = get_all_users_from_api()
        # ถ้าไม่มีข้อมูล หรือ API error ให้ return False
        if not users: return False, None
        
        df = pd.DataFrame(users)
        
        if df.empty: return False, None
        
        target_col = "LINE User ID"
        # Normalize Column Names (เผื่อ Google Sheet ส่งมาไม่ตรงเป๊ะ)
        # ลองหา key ที่มีคำว่า 'Line' และ 'ID'
        actual_cols = df.columns.tolist()
        for col in actual_cols:
             if "line" in str(col).lower() and "id" in str(col).lower():
                 target_col = col
                 break
        
        if target_col in df.columns:
            # ใช้ str() และ strip() เพื่อความชัวร์ในการเปรียบเทียบ
            match = df[df[target_col].astype(str).str.strip() == str(line_user_id).strip()]
            if not match.empty:
                r = match.iloc[0]
                # รับค่าจาก key ที่อาจจะเป็นภาษาไทยหรืออังกฤษ
                fname = r.get("ชื่อ") or r.get("fname") or ""
                lname = r.get("นามสกุล") or r.get("lname") or ""
                return True, {"first_name": str(fname), "last_name": str(lname), "line_id": str(line_user_id)}
        return False, None
    except Exception as e: 
        st.error(f"Check Logic Error: {e}")
        return False, None

# --- Helpers ---
def clean_string(val): return str(val).strip() if not pd.isna(val) else ""
def normalize_db_name_field(s): 
    parts = clean_string(s).split()
    return (parts[0], " ".join(parts[1:])) if len(parts)>=2 else (parts[0], "") if parts else ("","")

def check_registration_logic(df, f, l, i):
    f, l, i = clean_string(f), clean_string(l), clean_string(i)
    if not f or not l or not i: return False, "กรอกข้อมูลให้ครบ", None
    if len(i.replace("-","")) != 13: return False, "เลขบัตรต้องมี 13 หลัก", None
    
    try:
        # Check SQLite Database
        match = df[df['เลขบัตรประชาชน'].astype(str).str.strip().str.replace("-","") == i.replace("-","")]
        if match.empty: return False, "ไม่พบข้อมูลในระบบ", None
        for _, row in match.iterrows():
            db_f, db_l = normalize_db_name_field(row['ชื่อ-สกุล'])
            if db_f == f and db_l.replace(" ","") == l.replace(" ",""): return True, "OK", row.to_dict()
        return False, "ชื่อ-นามสกุลไม่ตรง", None
    except Exception as e: return False, f"System Error: {e}", None

# --- LIFF ---
def liff_initializer_component():
    # ถ้ามี Line User ID อยู่แล้ว ไม่ต้องโหลด LIFF ซ้ำ
    if "line_user_id" in st.session_state or st.query_params.get("userid"): return
    
    # ถ้าทำงานใน Localhost หรือไม่มี LIFF ID อาจจะข้าม LIFF ไปเลยเพื่อทดสอบ
    js = f"""<script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <script>
    async function main() {{
        try {{ await liff.init({{ liffId: "{LIFF_ID}" }});
            if(!liff.isLoggedIn()){{ liff.login(); return; }}
            const p = await liff.getProfile();
            const url = new URL(window.top.location.href);
            if(!url.searchParams.has("userid")){{
                url.searchParams.set("userid", p.userId);
                window.top.location.href = url.toString();
            }}
        }} catch(e) {{ 
            console.log("LIFF Init Error (Ignore if Localhost): " + e);
        }}
    }}
    main();
    </script>
    <div id="msg" style="text-align:center;padding:10px;font-size:12px;color:gray;">...Checking LINE Login...</div>"""
    components.html(js, height=50)

def render_admin_line_manager(): st.error("Disabled")

# --- UI ---
def render_registration_page(df):
    st.markdown("""<style>.reg-container {padding: 2rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 500px; margin: auto; background-color: white;} .stButton>button {background-color: #00B900 !important; color: white !important;}</style>""", unsafe_allow_html=True)
    
    qp = st.query_params.get("userid")
    if qp: st.session_state["line_user_id"] = qp
    
    # Debug / Mock UI (สำหรับทดสอบเมื่อไม่มี LIFF)
    if "line_user_id" not in st.session_state and not st.session_state.get('authenticated'):
        liff_initializer_component()
        
        # ส่วนนี้เอาไว้ Debug ตอน Localhost ได้ครับ
        # with st.expander("🛠️ Developer / Debug Options"):
        #     st.write("ถ้า LIFF ไม่ทำงาน ให้ใส่ Mock User ID ตรงนี้:")
        #     mock_uid = st.text_input("Mock LINE User ID", "U_MOCK_12345")
        #     if st.button("Set Mock User ID"):
        #         st.session_state["line_user_id"] = mock_uid
        #         st.rerun()
        
        if "line_user_id" not in st.session_state:
            return 

    uid = st.session_state["line_user_id"]
    is_reg, info = check_if_user_registered(uid)
    
    # --- Logic ป้องกัน Auto-Login ---
    # ถ้าเคยลงทะเบียนแล้ว
    if is_reg and not st.session_state.get('force_re_register', False):
        found = df[df['ชื่อ-สกุล'].str.contains(info['first_name'], na=False)]
        user = None
        for _, r in found.iterrows():
            dbf, dbl = normalize_db_name_field(r['ชื่อ-สกุล'])
            if dbf == info['first_name'] and dbl == info['last_name']: user = r; break
        
        if user is not None:
            st.info(f"ยินดีต้อนรับกลับ คุณ {user['ชื่อ-สกุล']}")
            col_conf1, col_conf2 = st.columns(2)
            with col_conf1:
                if st.button("เข้าใช้งานทันที (Login)", type="primary", use_container_width=True):
                    st.session_state.update({'authenticated': True, 'pdpa_accepted': True, 'user_hn': user['HN'], 'user_name': user['ชื่อ-สกุล'], 'is_line_login': True})
                    st.rerun()
            with col_conf2:
                if st.button("ไม่ใช่ฉัน / ลงทะเบียนใหม่", use_container_width=True):
                    st.session_state['force_re_register'] = True
                    st.rerun()
            return
        else: 
            st.warning(f"พบ LINE ID ({info['first_name']}) แต่ไม่พบข้อมูลสุขภาพในระบบ")
            if st.button("ลงทะเบียนใหม่"):
                st.session_state['force_re_register'] = True
                st.rerun()
            return

    if st.session_state.get('line_register_success'):
        st.success("✅ ลงทะเบียนสำเร็จ!"); 
        if st.button("ดูผลตรวจ"): st.rerun()
        return

    with st.container():
        title_text = "ลงทะเบียนใหม่ (LINE)" if st.session_state.get('force_re_register') else "ลงทะเบียน (LINE)"
        st.markdown(f"<div class='reg-container'><h3 style='text-align:center;'>{title_text}</h3>", unsafe_allow_html=True)
        with st.form("reg_form"):
            c1, c2 = st.columns(2)
            f = c1.text_input("ชื่อ")
            l = c2.text_input("นามสกุล")
            i = st.text_input("เลขบัตรประชาชน (13 หลัก)", max_chars=13)
            
            st.markdown("---")
            st.markdown("**ข้อตกลงและเงื่อนไข (PDPA)**")
            pdpa = st.checkbox("ข้าพเจ้ายอมรับข้อตกลงและเงื่อนไข")
            
            sub = st.form_submit_button("ยืนยันข้อมูล", use_container_width=True)
        
        if sub:
            if not pdpa: st.warning("กรุณายอมรับ PDPA")
            else:
                suc, msg, row = check_registration_logic(df, f, l, i)
                if suc:
                    with st.spinner("⏳ กำลังบันทึกข้อมูลไปยัง Google Sheets..."):
                        sv_suc, sv_msg = save_user_to_api(clean_string(f), clean_string(l), uid, clean_string(i))
                    
                    if sv_suc:
                        st.success(f"✅ {sv_msg}") 
                        st.session_state['line_saved'] = True
                        st.session_state['line_register_success'] = True
                        st.session_state['authenticated'] = True
                        st.session_state['pdpa_accepted'] = True
                        st.session_state['user_hn'] = row['HN']
                        st.session_state['user_name'] = row['ชื่อ-สกุล']
                        if 'force_re_register' in st.session_state: del st.session_state['force_re_register']
                        time.sleep(2)
                        st.rerun()
                    else: 
                        st.error(f"❌ บันทึกไม่สำเร็จ: {sv_msg}")
                else: 
                    st.error(f"❌ {msg}")
        st.markdown("</div>", unsafe_allow_html=True)
