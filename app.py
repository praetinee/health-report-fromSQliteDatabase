import streamlit as st
import sqlite3
import requests
import pandas as pd
import io
import tempfile
import html  # Used for html.escape()
import numpy as np
from collections import OrderedDict
from datetime import datetime
import re

def is_empty(val):
    return str(val).strip().lower() in ["", "-", "none", "nan", "null"]

# --- Global Helper Functions: START ---

# Define Thai month mappings (global to these functions)
THAI_MONTHS_GLOBAL = {
    1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน",
    5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม",
    9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"
}
THAI_MONTH_ABBR_TO_NUM_GLOBAL = {
    "ม.ค.": 1, "ม.ค": 1, "มกราคม": 1,
    "ก.พ.": 2, "ก.พ": 2, "กพ": 2, "กุมภาพันธ์": 2,
    "มี.ค.": 3, "มี.ค": 3, "มีนาคม": 3,
    "เม.ย.": 4, "เม.ย": 4, "เมษายน": 4,
    "พ.ค.": 5, "พ.ค": 5, "พฤษภาคม": 5,
    "มิ.ย.": 6, "มิ.ย": 6, "มิถุนายน": 6,
    "ก.ค.": 7, "ก.ค": 7, "กรกฎาคม": 7,
    "ส.ค.": 8, "ส.ค": 8, "สิงหาคม": 8,
    "ก.ย.": 9, "ก.ย": 9, "กันยายน": 9,
    "ต.ค.": 10, "ต.ค": 10, "ตุลาคม": 10,
    "พ.ย.": 11, "พ.ย": 11, "พฤศจิกายน": 11,
    "ธ.ค.": 12, "ธ.ค": 12, "ธันวาคม": 12
}

# Function to normalize and convert Thai dates
def normalize_thai_date(date_str):
    if is_empty(date_str):
        return "-"
    
    s = str(date_str).strip().replace("พ.ศ.", "").replace("พศ.", "").strip()

    if s.lower() in ["ไม่ตรวจ", "นัดที่หลัง", "ไม่ได้เข้ารับการตรวจ", ""]:
        return s

    try:
        # Format: DD/MM/YYYY (e.g., 29/04/2565)
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', s):
            day, month, year = map(int, s.split('/'))
            if year > 2500: # Assume Thai Buddhist year if year > 2500
                year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}".replace('.', '')

        # Format: DD-MM-YYYY (e.g., 29-04-2565)
        if re.match(r'^\d{1,2}-\d{1,2}-\d{4}$', s):
            day, month, year = map(int, s.split('-'))
            if year > 2500: # Assume Thai Buddhist year if year > 2500
                year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}".replace('.', '')

        # Format: DD MonthNameYYYY (e.g., 8 เมษายน 2565) or DD-DD MonthNameYYYY (e.g., 15-16 กรกฎาคม 2564)
        match_thai_text_date = re.match(r'^(?P<day1>\d{1,2})(?:-\d{1,2})?\s*(?P<month_str>[ก-ฮ]+\.?)\s*(?P<year>\d{4})$', s)
        if match_thai_text_date:
            day = int(match_thai_text_date.group('day1'))
            month_str = match_thai_text_date.group('month_str').strip().replace('.', '')
            year = int(match_thai_text_date.group('year'))
            
            month_num = THAI_MONTH_ABBR_TO_NUM_GLOBAL.get(month_str)
            if month_num:
                try:
                    dt = datetime(year - 543, month_num, day)
                    return f"{day} {THAI_MONTHS_GLOBAL[dt.month]} {year}".replace('.', '')
                except ValueError:
                    pass

    except Exception:
        pass

    # Fallback to pandas for robust parsing if other specific regex fail
    try:
        parsed_dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if pd.notna(parsed_dt):
            current_ce_year = datetime.now().year
            if parsed_dt.year > current_ce_year + 50 and parsed_dt.year - 543 > 1900:
                parsed_dt = parsed_dt.replace(year=parsed_dt.year - 543)
            return f"{parsed_dt.day} {THAI_MONTHS_GLOBAL[parsed_dt.month]} {parsed_dt.year + 543}".replace('.', '')
    except Exception:
        pass

    return s

# (ฟังก์ชันเดิมทั้งหมดถูกคงไว้เหมือนเดิม...)

# ... [ย่อส่วน helper functions เดิม, อ่านรายละเอียดในไฟล์ต้นฉบับที่ผู้ใช้ส่งมา] ...

# ... [โค้ดจัดการ UI, Sidebar, Form, การค้นหา ฯลฯ ...เหมือนเดิม] ...

# ==================== Display Health Report (Main Content) ====================
if "person_row" in st.session_state and st.session_state.get("selected_row_found", False):
    # ... [ส่วนรายงานหลัก, สรุปความเห็นแพทย์, ตาราง ฯลฯ ...เหมือนเดิม] ...

    # === ปุ่ม "พิมพ์รายงาน" ===
    st.markdown("""
        <style>
        .print-button {
            display: flex;
            justify-content: flex-end;
            margin-top: 24px;
            margin-bottom: 24px;
        }
        .print-button button {
            background: #1b5e20;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 0.6rem 2rem;
            font-size: 1rem;
            cursor: pointer;
            transition: background 0.2s;
            font-family: 'Sarabun', sans-serif;
        }
        .print-button button:hover {
            background: #388e3c;
        }
        @media print {
            .print-button { display: none !important; }
            footer, header { display: none !important; }
        }
        </style>
        <div class="print-button">
            <button onclick="window.print()">🖨️ พิมพ์รายงาน</button>
        </div>
    """, unsafe_allow_html=True)
