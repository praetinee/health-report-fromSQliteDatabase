# gsheet_api.py
# โมดูล client สำหรับเรียก Google Apps Script Web App (POST JSON)
# ใส่ WEB_APP_URL และ SECRET ให้ตรงกับที่ Deploy ใน Code.gs

import requests
import json
import time

# ตั้งค่า 2 ค่าต่อไปนี้ให้ตรงกับการ deploy của bạn
WEB_APP_URL = "REPLACE_WITH_YOUR_APPS_SCRIPT_WEB_APP_URL"  # ตัวอย่าง https://script.google.com/macros/s/XXXXX/exec
SECRET = "REPLACE_WITH_A_RANDOM_SECRET_STRING"  # ต้องตรงกับ SECRET ใน Code.gs

DEFAULT_TIMEOUT = 15

def get_all_users_from_api():
    """
    เรียก Web App ด้วย action=read
    คืนค่า: list ของ dict (แต่ละ dict คือแถวใน sheet) หรือ [] เมื่อผิดพลาด
    """
    try:
        # ส่งเป็น POST JSON เพื่อความปลอดภัย (Web App รองรับทั้ง GET/POST)
        payload = {"action": "read"}
        resp = requests.post(WEB_APP_URL, json=payload, timeout=DEFAULT_TIMEOUT)
        # Check if Google redirected us to login page
        if resp.url:
            from urllib.parse import urlparse
            parsed = urlparse(resp.url)
            # Check if we were redirected to Google's login page
            netloc_lower = parsed.netloc.lower()
            if netloc_lower == "accounts.google.com" or netloc_lower.endswith(".accounts.google.com"):
                # permission problem (sheet not shared / web app not set to anyone)
                raise PermissionError("Google Script permission error: check 'Who has access' or share settings.")
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")
        try:
            data = resp.json()
        except json.JSONDecodeError:
            # บางครั้ง Web app ส่งกลับเป็น text/html หาก URL ผิด
            raise ValueError("Response not JSON. Check WEB_APP_URL and access permissions.")
        # ถ้าเป็น dict ที่ประกอบด้วย result:error
        if isinstance(data, dict) and data.get("result") == "error":
            raise RuntimeError("Apps Script error: " + str(data.get("message")))
        return data if isinstance(data, list) else []
    except Exception as e:
        # แสดงข้อความ error แบบไม่หยุดโปรแกรม — ให้เรียกใช้ที่เรียกฟังก์ชันจัดการแสดงผลต่อเอง
        return []


def save_user_to_api(fname, lname, line_user_id, id_card=""):
    """
    ส่งข้อมูลไปบันทึกใน Google Sheet ผ่าน Web App
    คืนค่า dict เช่น {"ok": True} หรือ {"ok": False, "error": "..."}
    """
    try:
        payload = {
            "action": "write",
            "secret": SECRET,
            "fname": fname,
            "lname": lname,
            "line_id": line_user_id,
            "card_id": id_card
        }
        # ใช้ POST JSON
        resp = requests.post(WEB_APP_URL, json=payload, timeout=DEFAULT_TIMEOUT)
        # Check if Google redirected us to login page
        if resp.url:
            from urllib.parse import urlparse
            parsed = urlparse(resp.url)
            netloc_lower = parsed.netloc.lower()
            if netloc_lower == "accounts.google.com" or netloc_lower.endswith(".accounts.google.com"):
                return {"ok": False, "error": "Permission error: Apps Script requires 'Anyone with link' or proper auth."}
        if resp.status_code != 200:
            return {"ok": False, "error": f"HTTP {resp.status_code}"}
        try:
            data = resp.json()
        except json.JSONDecodeError:
            return {"ok": False, "error": "Response not JSON from Apps Script"}
        if isinstance(data, dict) and (data.get("result") == "ok" or data.get("status") == "ok"):
            return {"ok": True}
        else:
            # ถ้า Apps Script ส่ง {result:'error', message:...}
            return {"ok": False, "error": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}
