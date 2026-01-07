import streamlit as st
import pandas as pd
import io
import plotly.express as px
from datetime import datetime
from batch_print import render_batch_print_page
from print_performance_report import render_print_performance_report_page
from line_register import render_line_register_page

def render_admin_dashboard(df):
    """
    ฟังก์ชันหลักสำหรับแสดงหน้า Dashboard ของผู้ดูแลระบบ
    """
    st.markdown("""
    <style>
        .admin-header {
            color: #00B900;
            font-weight: bold;
            font-size: 24px;
            margin-bottom: 20px;
        }
        .stat-card {
            background-color: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #00B900;
        }
        .stat-label {
            font-size: 14px;
            color: #666;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 class='admin-header'>แผงควบคุมผู้ดูแลระบบ (Admin Dashboard)</h2>", unsafe_allow_html=True)
    
    # --- ส่วนสรุปข้อมูลสถิติ ---
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_records = len(df)
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{total_records:,}</div>
            <div class="stat-label">จำนวนระเบียนทั้งหมด</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        # นับจำนวนผู้รับบริการที่ไม่ซ้ำ (อ้างอิงจาก HN)
        unique_patients = df['HN'].nunique() if 'HN' in df.columns else 0
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{unique_patients:,}</div>
            <div class="stat-label">จำนวนผู้รับบริการ (คน)</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        # สรุปผลการประเมิน (ตัวอย่าง: นับจำนวนที่มีความเสี่ยง)
        # สมมติว่ามีคอลัมน์ 'CVD_Risk' หรือสรุปจากคอลัมน์อื่น
        risk_count = 0
        if 'ผลประเมิน' in df.columns:
             # นับเฉพาะที่มีคำว่า 'เสี่ยง' หรือ 'สูง'
            risk_count = df['ผลประเมิน'].astype(str).apply(lambda x: 1 if 'เสี่ยง' in x or 'สูง' in x else 0).sum()
            
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{risk_count:,}</div>
            <div class="stat-label">กลุ่มเสี่ยง/ผิดปกติ</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        # ข้อมูลล่าสุด
        last_update = "-"
        if 'วันที่ตรวจ' in df.columns:
            try:
                # แปลงวันที่ให้เป็น datetime เพื่อหาค่าล่าสุด
                dates = pd.to_datetime(df['วันที่ตรวจ'], errors='coerce')
                last_date = dates.max()
                if not pd.isna(last_date):
                    # แปลงเป็นปี พ.ศ.
                    thai_year = last_date.year + 543
                    last_update = last_date.strftime(f"%d/%m/{thai_year}")
            except:
                pass
                
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{last_update}</div>
            <div class="stat-label">อัปเดตข้อมูลล่าสุด</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")

    # --- เมนูการทำงาน ---
    tab1, tab2, tab3 = st.tabs(["📊 ภาพรวมข้อมูล", "🖨️ พิมพ์รายงานแบบกลุ่ม", "📑 รายงานสรุปผลการดำเนินงาน"])
    
    with tab1:
        st.subheader("ภาพรวมข้อมูลสุขภาพ")
        
        # ตัวอย่างกราฟ 1: การกระจายตัวของ BMI (ถ้ามีข้อมูล)
        if 'BMI' in df.columns:
            try:
                # แปลงข้อมูลเป็นตัวเลข
                df['BMI_Val'] = pd.to_numeric(df['BMI'], errors='coerce')
                fig_bmi = px.histogram(df, x='BMI_Val', nbins=20, title='การกระจายตัวของค่าดัชนีมวลกาย (BMI)',
                                      labels={'BMI_Val': 'ค่า BMI', 'count': 'จำนวนคน'},
                                      color_discrete_sequence=['#00B900'])
                st.plotly_chart(fig_bmi, use_container_width=True)
            except:
                st.info("ไม่สามารถแสดงกราฟ BMI ได้ เนื่องจากรูปแบบข้อมูลไม่ถูกต้อง")
        
        # ตัวอย่างกราฟ 2: แยกตามเพศ (ถ้ามีข้อมูล)
        if 'เพศ' in df.columns:
            gender_counts = df['เพศ'].value_counts().reset_index()
            gender_counts.columns = ['เพศ', 'จำนวน']
            fig_gender = px.pie(gender_counts, values='จำนวน', names='เพศ', title='สัดส่วนผู้รับบริการแยกตามเพศ',
                               color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig_gender, use_container_width=True)
            
        # ตารางข้อมูลดิบ (แสดง 100 แถวแรก)
        with st.expander("ดูข้อมูลดิบ (100 รายการล่าสุด)"):
            st.dataframe(df.head(100))
            
            # ปุ่มดาวน์โหลด CSV
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "ดาวน์โหลดข้อมูลทั้งหมดเป็น CSV",
                csv,
                "health_data_export.csv",
                "text/csv",
                key='download-csv'
            )

    with tab2:
        render_batch_print_page(df)

    with tab3:
        render_print_performance_report_page(df)
