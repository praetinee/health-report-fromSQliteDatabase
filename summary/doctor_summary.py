import streamlit as st

def render_doctor_summary(person):
    st.subheader("สรุปผลตรวจโดยแพทย์")

    fields = [
        "สรุปความดัน", "สรุปน้ำตาล", "สรุปไขมัน", "สรุปตับ", "สรุปยูริค", "สรุปไต",
        "สรุป HB HCT", "สรุปwbc", "สรุปplt",
        "สรุปAlb.UA", "สรุปSugar.UA", "สรุปRBC.UA", "สรุปWBC.UA",
        "สรุปปัญหาอื่น", "DOCTER suggest"
    ]

    for key in fields:
        value = person.get(key, "")
        if value and str(value).strip():
            st.markdown(f"**{key}:** {value}")
