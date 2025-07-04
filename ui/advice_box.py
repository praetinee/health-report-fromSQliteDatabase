import streamlit as st
from collections import OrderedDict

def merge_advice_by_group(messages: list[str]) -> str:
    """รวมคำแนะนำเป็นหมวดหมู่ เช่น ไต, น้ำตาล, ไขมัน ฯลฯ"""
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

def render_advice_box(advice: str | list[str]):
    """แสดงกล่องคำแนะนำ จากข้อความหรือ list ของข้อความ"""
    if isinstance(advice, list):
        final_html = merge_advice_by_group(advice)
        has_advice = "ไม่พบคำแนะนำเพิ่มเติม" not in final_html
    else:
        final_html = str(advice).strip()
        has_advice = final_html != ""

    background_color = (
        "rgba(255, 215, 0, 0.15)" if has_advice else "rgba(200, 255, 200, 0.15)"
    )

    st.markdown(
        f"""
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
            {final_html}
        </div>
        """,
        unsafe_allow_html=True
    )
