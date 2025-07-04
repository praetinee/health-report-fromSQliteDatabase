import streamlit as st

from data_loader import load_sqlite_data
from utils import get_float, flag  # ถ้ามีใช้ใน future
from ui.search_form import render_search_form
from ui.section_header import render_section_header
from ui.overview_section import render_overview
from ui.advice_box import render_advice_box

from analysis.cbc import render_cbc_section
from analysis.chemistry import render_chemistry_section
from analysis.urine import render_urine_section
from analysis.stool import render_stool_section
from analysis.cxr import render_cxr_section
from analysis.ekg import render_ekg_section
from analysis.hepatitis import render_hepatitis_section

from summary.doctor_summary import render_doctor_summary


def main():
    st.set_page_config(layout="wide", page_title="Health Report", page_icon="🧬")

    df = load_sqlite_data()
    person = render_search_form(df)
    if not person:
        st.stop()

    render_section_header("ข้อมูลทั่วไป")
    render_overview(person)

    render_section_header("ผลตรวจ CBC")
    render_cbc_section(person)

    render_section_header("ผลตรวจเคมีในเลือด")
    render_chemistry_section(person)

    render_section_header("ผลตรวจปัสสาวะ")
    render_urine_section(person)

    render_section_header("ผลตรวจอุจจาระ")
    render_stool_section(person)

    render_section_header("ผล X-ray")
    render_cxr_section(person)
    
    render_section_header("ผล EKG")
    render_cxr_ekg_section(person)

    render_section_header("ผลตรวจไวรัสตับอักเสบ")
    render_hepatitis_section(person)

    render_section_header("สรุปโดยแพทย์")
    render_doctor_summary(person)


if __name__ == "__main__":
    main()
