import streamlit as st

from ui.style import inject_global_styles
from data_loader import load_sqlite_data
from utils import get_float, bp_advice_text
from ui.search_form import render_search_form
from ui.section_header import render_section_header
from ui.advice_box import render_advice_box
from ui.report_header import render_report_header

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
    inject_global_styles()

    df = load_sqlite_data()
    person = render_search_form(df)
    if person is None or person.empty:
        st.stop()

    # 🔹 ส่วนหัวรายงาน
    render_report_header(person)

    # 🔹 ความดัน + ชีพจร
    sbp = get_float("SBP", person)
    dbp = get_float("DBP", person)
    pulse = get_float("ชีพจร", person)

    bp_text = f"{int(sbp)}/{int(dbp)}" if sbp and dbp else "-"
    pulse_text = f"{int(pulse)} ครั้ง/นาที" if pulse else "-"

    st.markdown(f"""
    <div style='text-align: center; font-size: 1.1rem; margin-top: 1rem;'>
        <b>ความดันโลหิต:</b> {bp_text} &nbsp;&nbsp; <b>ชีพจร:</b> {pulse_text}
    </div>
    """, unsafe_allow_html=True)

    # 🔹 กล่องคำแนะนำความดัน (ถ้ามี)
    bp_advice = bp_advice_text(sbp, dbp)
    if bp_advice:
        render_advice_box(bp_advice)

    # 🔬 ผลตรวจต่าง ๆ
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

    render_section_header("ผลคลื่นไฟฟ้าหัวใจ")
    render_ekg_section(person)

    render_section_header("ผลตรวจไวรัสตับอักเสบ")
    render_hepatitis_section(person)

    render_section_header("สรุปโดยแพทย์")
    render_doctor_summary(person)


if __name__ == "__main__":
    main()
