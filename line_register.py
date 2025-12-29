"""
Updated line_register.py
- This single-file replacement implements a Streamlit UI to register users (First name, Last name, LINE user ID, optional card ID)
  and saves the data to a Google Sheet via a Google Apps Script Web App endpoint (POST JSON).
- It includes robust helper functions to call the Web App and to read/write rows.
- Edit the WEB_APP_URL and SECRET constants to match your deployed Apps Script before running.
- Dependencies: streamlit, requests, pandas

Usage:
  pip install streamlit requests pandas
  streamlit run line_register.py
"""

import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import time

# --------------- CONFIG: Change these to your values ---------------
# LIFF_ID left as informational only; LIFF integration is not implemented here.
LIFF_ID = "2008725340-YHOiWxtj"

# The Web App URL you get after deploying the Google Apps Script (Code.gs).
# Example: "https://script.google.com/macros/s/XXXXX/exec"
WEB_APP_URL = "REPLACE_WITH_YOUR_APPS_SCRIPT_WEB_APP_URL"

# SECRET must match the SECRET in your Code.gs Apps Script to prevent unauthorized writes.
SECRET = "REPLACE_WITH_A_RANDOM_SECRET_STRING"
# -------------------------------------------------------------------

DEFAULT_TIMEOUT = 15  # seconds for HTTP requests

# --------------------- Helper functions for Apps Script ---------------------


def _post_to_web_app(payload: dict, timeout: int = DEFAULT_TIMEOUT):
    """
    POST JSON payload to the Google Apps Script Web App.
    Returns parsed JSON on success, or raises Exception on failure.
    Handles common error cases like Google redirect for auth/permission issues.
    """
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(WEB_APP_URL, json=payload, headers=headers, timeout=timeout, allow_redirects=True)
    except Exception as e:
        raise ConnectionError(f"Request failed: {e}")

    # If Google redirected to login, permissions are misconfigured
    if resp.url:
        from urllib.parse import urlparse
        parsed = urlparse(resp.url)
        # Check if we were redirected to Google's login page
        netloc_lower = parsed.netloc.lower()
        if netloc_lower == "accounts.google.com" or netloc_lower.endswith(".accounts.google.com"):
            raise PermissionError("Apps Script redirected to Google login — check 'Who has access' (should allow access to caller) or use appropriate auth.")

    if resp.status_code != 200:
        raise RuntimeError(f"Apps Script returned HTTP {resp.status_code}")

    # Try parse JSON
    try:
        data = resp.json()
    except json.JSONDecodeError:
        # Not JSON: maybe HTML describing an error or wrong URL
        raise ValueError("Response from Apps Script is not valid JSON. Check WEB_APP_URL and Apps Script deployment.")

    return data


def get_all_users_from_api():
    """
    Retrieve all rows from the Google Sheet via the Apps Script (action=read).
    Returns a list of dict rows. On error returns [].
    """
    try:
        payload = {"action": "read"}
        data = _post_to_web_app(payload)
        if isinstance(data, dict) and data.get("result") == "error":
            # Apps Script responded with an error structure
            st.error(f"Apps Script error (read): {data.get('message')}")
            return []
        if isinstance(data, list):
            return data
        # If Apps Script responded object with data in a key, try to handle common shapes
        if isinstance(data, dict) and "rows" in data and isinstance(data["rows"], list):
            return data["rows"]
        # Unknown shape
        st.warning("No data returned from Apps Script (unexpected shape).")
        return []
    except PermissionError as pe:
        st.error("Permission error while reading from Google Sheet. Make sure the Web App is deployed with correct access (Anyone with the link) or proper auth.")
        return []
    except Exception as e:
        st.error(f"Connection Error (Read): {e}")
        return []


def save_user_to_api(fname: str, lname: str, line_user_id: str, id_card: str = "") -> (bool, str):
    """
    Send the user record to Apps Script (action=write).
    Returns (True, '') on success or (False, error_message) on failure.
    """
    try:
        payload = {
            "action": "write",
            "secret": SECRET,
            "fname": fname,
            "lname": lname,
            "line_id": line_user_id,
            "card_id": id_card,
        }
        data = _post_to_web_app(payload)
        # Accept different success shapes:
        if isinstance(data, dict) and (data.get("result") == "ok" or data.get("status") == "ok" or data.get("result") is None):
            return True, ""
        # If specific error returned
        if isinstance(data, dict) and data.get("result") == "error":
            return False, str(data.get("message", "Unknown error"))
        # Unknown but no error
        return True, ""
    except PermissionError as pe:
        return False, "Permission error: Apps Script requires appropriate access (check Who has access on deployment)."
    except Exception as e:
        return False, str(e)


# --------------------- Streamlit UI ---------------------

st.set_page_config(page_title="LINE Register", layout="centered")
st.title("LINE Registration to Google Sheet")
st.markdown(
    """
กรุณากรอกข้อมูลด้านล่างเพื่อลงทะเบียน: ชื่อ, นามสกุล และ LINE user ID
ข้อมูลจะถูกบันทึกลง Google Sheet ผ่าน Google Apps Script Web App.
"""
)

# Show warning if WEB_APP_URL/SECRET not set
if "REPLACE_WITH" in WEB_APP_URL or "REPLACE_WITH" in SECRET:
    st.warning("ยังไม่ได้ตั้งค่า WEB_APP_URL หรือ SECRET ในไฟล์นี้ — กรุณาแก้ค่าตามคำแนะนำก่อนทดสอบ")

# Registration form
with st.form("register_form"):
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("ชื่อ (First name)", max_chars=100)
    with col2:
        last_name = st.text_input("นามสกุล (Last name)", max_chars=100)
    line_user_id = st.text_input("LINE user ID (ตัวอย่าง: Uxxxxxxxxxxxxxx)")
    id_card = st.text_input("ID Card (optional)")
    submitted = st.form_submit_button("Submit")

if submitted:
    # Basic validation
    errors = []
    if not first_name.strip():
        errors.append("กรุณากรอกชื่อ")
    if not last_name.strip():
        errors.append("กรุณากรอกนามสกุล")
    if not line_user_id.strip():
        errors.append("กรุณากรอก LINE user ID")
    if errors:
        for e in errors:
            st.error(e)
    else:
        st.info("กำลังบันทึกข้อมูล...")
        ok, msg = save_user_to_api(first_name.strip(), last_name.strip(), line_user_id.strip(), id_card.strip())
        if ok:
            st.success("บันทึกข้อมูลเรียบร้อยแล้ว ✅")
            # small delay then refresh displayed data
            time.sleep(0.5)
        else:
            st.error(f"ไม่สามารถบันทึกข้อมูลได้: {msg}")

st.markdown("---")
st.subheader("รายการผู้ที่ลงทะเบียนแล้ว (จาก Google Sheet)")

# Show fetched users
with st.spinner("กำลังโหลดข้อมูลจาก Google Sheet..."):
    rows = get_all_users_from_api()
    # If rows is list of dicts with header names: make a DataFrame
    df = None
    if isinstance(rows, list) and len(rows) > 0:
        if isinstance(rows[0], dict):
            # Normalize keys: sometimes keys are header names (Timestamp, FirstName,...)
            df = pd.DataFrame(rows)
        else:
            # If rows are lists, convert to dataframe with generic columns
            try:
                df = pd.DataFrame(rows)
            except Exception:
                df = None
    if df is None or df.empty:
        st.info("ยังไม่มีข้อมูลลงทะเบียน หรือไม่สามารถอ่านข้อมูลได้")
    else:
        st.dataframe(df)

# Helpful debug block (collapsed)
with st.expander("Debug / Info (แสดงคอนฟิกและตัวอย่าง payload)"):
    st.write("WEB_APP_URL:", WEB_APP_URL)
    st.write("SECRET set:", bool(SECRET and "REPLACE_WITH" not in SECRET))
    st.write("Example POST payload for write:")
    st.code(json.dumps({
        "action": "write",
        "secret": SECRET,
        "fname": "สมชาย",
        "lname": "ใจดี",
        "line_id": "U1234567890",
        "card_id": ""
    }, ensure_ascii=False, indent=2))

# End of file
