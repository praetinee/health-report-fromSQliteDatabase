import pandas as pd
from performance_tests import interpret_audiogram, interpret_lung_capacity

# ==============================================================================
# Module: print_performance_report.py
# Purpose: Contains functions to generate HTML for performance test reports
# (Vision, Hearing, Lung) for the printable version.
# ==============================================================================


# --- Helper & Data Availability Functions ---

def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def has_vision_data(person_data):
    """Check for any vision test data."""
    detailed_keys = [
        'ป.การรวมภาพ', 'ผ.การรวมภาพ', 'ป.ความชัดของภาพระยะไกล', 
        'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)', 'ป.การจำแนกสี'
    ]
    return any(not is_empty(person_data.get(key)) for key in detailed_keys)

def has_hearing_data(person_data):
    """Check for detailed hearing (audiogram) data."""
    hearing_keys = ['R500', 'L500', 'R1k', 'L1k', 'R4k', 'L4k']
    return any(not is_empty(person_data.get(key)) for key in hearing_keys)

def has_lung_data(person_data):
    """Check for lung capacity test data."""
    key_indicators = ['FVC เปอร์เซ็นต์', 'FEV1เปอร์เซ็นต์', 'FEV1/FVC%']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)


# --- HTML Rendering Functions ---

def render_section_header(title, subtitle=None, is_sub_header=False):
    bg_color = "#555" if is_sub_header else "#333"
    font_size = "10px" if is_sub_header else "11px"
    margin_top = "0.8rem" if is_sub_header else "1.5rem"
    
    full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
    return f"""
    <div style='
        background-color: {bg_color};
        color: white;
        text-align: center;
        padding: 0.2rem 0.4rem;
        font-weight: bold;
        border-radius: 6px;
        margin-top: {margin_top};
        margin-bottom: 0.5rem;
        font-size: {font_size};
    '>
        {full_title}
    </div>
    """

def render_print_vision(person_data):
    vision_advice = person_data.get('สรุปเหมาะสมกับงาน', 'ไม่มีข้อมูลสรุป')
    
    tests = [
        {'d': 'การมองด้วย 2 ตา', 'c': 'ป.การรวมภาพ', 'nk': ['ปกติ']},
        {'d': 'การมองภาพ 3 มิติ', 'c': 'ป.การกะระยะและมองความชัดลึกของภาพ', 'nk': ['ปกติ']},
        {'d': 'การมองจำแนกสี', 'c': 'ป.การจำแนกสี', 'nk': ['ปกติ']},
        {'d': 'การมองไกล (ตาขวา)', 'c': 'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)', 'nk': ['ชัดเจน', 'ปกติ']},
        {'d': 'การมองไกล (ตาซ้าย)', 'c': 'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)', 'nk': ['ชัดเจน', 'ปกติ']},
        {'d': 'การมองใกล้ (ตาขวา)', 'c': 'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)', 'nk': ['ชัดเจน', 'ปกติ']},
        {'d': 'การมองใกล้ (ตาซ้าย)', 'c': 'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)', 'nk': ['ชัดเจน', 'ปกติ']},
    ]
    
    rows_html = ""
    for test in tests:
        val = str(person_data.get(test['c'], '')).strip()
        status = "ไม่ได้ตรวจ"
        status_class = "status-nt"
        if not is_empty(val):
            if any(k.lower() in val.lower() for k in test['nk']):
                status = "ปกติ"
                status_class = "status-ok"
            else:
                status = "ผิดปกติ"
                status_class = "status-abn"
        rows_html += f"<tr><td>{test['d']}</td><td class='{status_class}'>{status}</td></tr>"

    return f"""
    <div class="perf-section">
        {render_section_header("ผลการตรวจสมรรถภาพการมองเห็น (Vision)", is_sub_header=True)}
        <div class="perf-columns">
            <div class="perf-col-summary">
                <b>สรุปความเหมาะสมกับงาน:</b>
                <div class="summary-box">{vision_advice}</div>
            </div>
            <div class="perf-col-details">
                <table class="perf-table">
                    <thead><tr><th>รายการตรวจ</th><th>ผล</th></tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
        </div>
    </div>
    """

def render_print_hearing(person_data):
    results = interpret_audiogram(person_data) # No history needed for basic print
    if results['summary'].get('overall') == "ไม่ได้เข้ารับการตรวจ": return ""

    summary_r = person_data.get('ผลตรวจการได้ยินหูขวา', 'N/A')
    summary_l = person_data.get('ผลตรวจการได้ยินหูซ้าย', 'N/A')
    advice = results.get('advice', 'ไม่มีคำแนะนำ')

    raw_data = results.get('raw_values', {})
    rows_html = ""
    for freq, values in raw_data.items():
        r_val = values.get('right', '-')
        l_val = values.get('left', '-')
        rows_html += f"<tr><td>{freq}</td><td>{r_val}</td><td>{l_val}</td></tr>"

    return f"""
    <div class="perf-section">
        {render_section_header("ผลการตรวจสมรรถภาพการได้ยิน (Hearing)", is_sub_header=True)}
        <div class="perf-columns">
            <div class="perf-col-summary">
                <b>สรุปผล:</b>
                <div class="summary-box">
                    <b>หูขวา:</b> {summary_r}<br>
                    <b>หูซ้าย:</b> {summary_l}
                </div>
                <b>คำแนะนำ:</b>
                <div class="summary-box">{advice}</div>
            </div>
            <div class="perf-col-details">
                <table class="perf-table">
                    <thead><tr><th>ความถี่ (Hz)</th><th>หูขวา (dB)</th><th>หูซ้าย (dB)</th></tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
        </div>
    </div>
    """

def render_print_lung(person_data):
    summary, advice, raw = interpret_lung_capacity(person_data)
    if summary == "ไม่ได้เข้ารับการตรวจ": return ""

    def format_val(key):
        val = raw.get(key)
        return f"{val:.1f}" if val is not None else "-"

    return f"""
    <div class="perf-section">
        {render_section_header("ผลการตรวจสมรรถภาพปอด (Lung Function)", is_sub_header=True)}
        <table class="info-table lung-table">
            <tr>
                <th>FVC (% Pred)</th><th>FEV1 (% Pred)</th><th>FEV1/FVC Ratio (%)</th>
            </tr>
            <tr>
                <td>{format_val('FVC %')}</td><td>{format_val('FEV1 %')}</td><td>{format_val('FEV1/FVC %')}</td>
            </tr>
        </table>
        <div class="perf-columns" style="margin-top: 0.5rem;">
             <div class="perf-col-summary">
                <b>สรุปผล:</b>
                <div class="summary-box">{summary}</div>
            </div>
             <div class="perf-col-summary">
                <b>คำแนะนำ:</b>
                <div class="summary-box">{advice}</div>
            </div>
        </div>
    </div>
    """

def generate_performance_report_html(person):
    """
    Checks for available performance tests and generates the combined HTML.
    """
    performance_html_parts = []
    if has_vision_data(person):
        performance_html_parts.append(render_print_vision(person))
    if has_hearing_data(person):
        performance_html_parts.append(render_print_hearing(person))
    if has_lung_data(person):
        performance_html_parts.append(render_print_lung(person))
    
    if not performance_html_parts:
        return ""
        
    return (
        render_section_header("ผลการตรวจสมรรถภาพพิเศษ (Performance Tests)") +
        "".join(performance_html_parts)
    )
