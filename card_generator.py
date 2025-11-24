from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
from io import BytesIO
import streamlit as st

@st.cache_data
def get_font(url):
    """Downloads a font file and caches it."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BytesIO(response.content)
    except requests.exceptions.RequestException as e:
        st.error(f"Font download failed: {e}")
        return None

# --- Icon Drawing Functions ---
def draw_mask_icon(draw, center_x, y, size=72, color="#333333"):
    """Draws the custom mask icon using Pillow with standardized stroke width."""
    offset_x = center_x - size / 2
    offset_y = y
    stroke_width = 3 # Standardized stroke width
    s = size / 24 # Scale factor from 24x24 viewBox

    def p(px, py):
        return (px * s + offset_x, py * s + offset_y)
    
    # Replicate the drawing based on the standardized SVG paths
    draw.line([p(4, 9), p(12, 4), p(20, 9)], fill=color, width=int(stroke_width))
    draw.line([p(20, 9), p(21, 14), p(20, 18)], fill=color, width=int(stroke_width))
    draw.line([p(20, 18), p(12, 22), p(4, 18)], fill=color, width=int(stroke_width))
    draw.line([p(4, 18), p(3, 14), p(4, 9)], fill=color, width=int(stroke_width))

    draw.line([p(4, 11), p(0, 13), p(4, 16)], fill=color, width=int(stroke_width))
    draw.line([p(20, 11), p(24, 13), p(20, 16)], fill=color, width=int(stroke_width))
    
    fold_width = int(stroke_width) - 1 if stroke_width > 1 else 1
    draw.line([p(6, 11), p(12, 9.5), p(18, 11)], fill=color, width=fold_width)
    draw.line([p(6, 14), p(12, 12.5), p(18, 14)], fill=color, width=fold_width)
    draw.line([p(6, 17), p(12, 15.5), p(18, 17)], fill=color, width=fold_width)


def draw_activity_icon(draw, center_x, y, size=72, color="#333333"):
    """Draws the custom bicycle icon using Pillow with standardized stroke width."""
    offset_x = center_x - size / 2
    offset_y = y
    stroke_width = 3 # Standardized stroke width
    s = size / 24 # Scale factor from 24x24 viewBox

    def p(px, py):
        return (px * s + offset_x, py * s + offset_y)
    
    # Wheels
    r = 3 * s
    draw.ellipse([(p(6.75-3, 16.5-3)), (p(6.75+3, 16.5+3))], outline=color, width=int(stroke_width))
    draw.ellipse([(p(17.25-3, 16.5-3)), (p(17.25+3, 16.5+3))], outline=color, width=int(stroke_width))
    
    # Frame
    draw.polygon([p(6.75, 16.5), p(11.25, 12), p(15, 16.5)], outline=color, width=int(stroke_width))
    
    # Seat and handle
    draw.line([p(11.25, 12), p(11.25, 9)], fill=color, width=int(stroke_width))
    draw.line([p(10.5, 9), p(12.75, 9)], fill=color, width=int(stroke_width))
    draw.line([p(15, 16.5), p(16.5, 11.25), p(19.5, 10.5)], fill=color, width=int(stroke_width))


def draw_indoors_icon(draw, center_x, y, size=72, color="#333333"):
    """Draws the house icon using Pillow."""
    s = size / 24 
    w = 3 # Standardized stroke width
    offset_x = center_x - size / 2
    offset_y = y
    
    house_outline = [
        (3*s + offset_x, 9*s + offset_y),
        (12*s + offset_x, 2*s + offset_y),
        (21*s + offset_x, 9*s + offset_y),
        (21*s + offset_x, 22*s + offset_y),
        (3*s + offset_x, 22*s + offset_y),
        (3*s + offset_x, 9*s + offset_y)
    ]
    draw.line(house_outline, fill=color, width=int(w))

    door = [
        (9*s + offset_x, 22*s + offset_y),
        (9*s + offset_x, 12*s + offset_y),
        (15*s + offset_x, 12*s + offset_y),
        (15*s + offset_x, 22*s + offset_y)
    ]
    draw.line(door, fill=color, width=int(w))


def generate_report_card(latest_pm25, level, color_hex, emoji, advice_details, date_str, lang, t):
    """Generates a new, modern, and clean report card image."""
    # --- Font Handling ---
    font_url_reg = "https://github.com/google/fonts/raw/main/ofl/sarabun/Sarabun-Regular.ttf"
    font_url_bold = "https://github.com/google/fonts/raw/main/ofl/sarabun/Sarabun-Bold.ttf"
    font_url_light = "https://github.com/google/fonts/raw/main/ofl/sarabun/Sarabun-Light.ttf"

    font_reg_bytes = get_font(font_url_reg)
    font_bold_bytes = get_font(font_url_bold)
    font_light_bytes = get_font(font_url_light)

    if not all([font_reg_bytes, font_bold_bytes, font_light_bytes]):
        return None
    
    def create_font(font_bytes, size):
        font_bytes.seek(0)
        return ImageFont.truetype(font_bytes, size)

    font_header = create_font(font_bold_bytes, 38)
    font_date = create_font(font_reg_bytes, 26)
    font_pm_value = create_font(font_bold_bytes, 150)
    font_unit = create_font(font_reg_bytes, 32)
    font_level = create_font(font_bold_bytes, 44)
    font_advice_header = create_font(font_bold_bytes, 28) 
    font_advice = create_font(font_reg_bytes, 24) 
    font_advice_risk = create_font(font_bold_bytes, 36) # Significantly bigger and Bold
    font_footer = create_font(font_light_bytes, 18)
    
    width, height = 800, 1000
    base_color = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    img = Image.new('RGB', (width, height), color=base_color)
    draw = ImageDraw.Draw(img)

    header_title = t[lang]['page_title']
    draw.text((width/2, 60), header_title, font=font_header, anchor="ms", fill="#FFFFFF")
    draw.text((width/2, 110), date_str, font=font_date, anchor="ms", fill=(255, 255, 255, 200))

    box_y_start = 150
    draw.rounded_rectangle([(20, box_y_start), (width - 20, height - 20)], radius=20, fill="#FFFFFF")
    
    pm_y_pos = box_y_start + 130 
    draw.text((width/2, pm_y_pos), f"{latest_pm25:.1f}", font=font_pm_value, anchor="ms", fill="#111111")
    draw.text((width/2, pm_y_pos + 85), "μg/m³", font=font_unit, anchor="ms", fill="#555555")
    draw.text((width/2, pm_y_pos + 135), level, font=font_level, anchor="ms", fill="#111111")
    
    advice_y_start = pm_y_pos + 200 # Moved up
    draw.line([(60, advice_y_start-20), (width - 60, advice_y_start-20)], fill="#EEEEEE", width=2)
    
    # --- Advice with Icons ---
    advice_items = [
        ('mask', t[lang]['advice_cat_mask'], draw_mask_icon),
        ('activity', t[lang]['advice_cat_activity'], draw_activity_icon),
        ('indoors', t[lang]['advice_cat_indoors'], draw_indoors_icon)
    ]

    item_width = width / len(advice_items)
    for i, (key, title, icon_func) in enumerate(advice_items):
        center_x = (item_width * i) + (item_width / 2)
        
        icon_func(draw, center_x, advice_y_start) 
        
        text_y = advice_y_start + 100 
        draw.text((center_x, text_y), title, font=font_advice_header, anchor="ms", fill="#333333")
        draw.text((center_x, text_y + 40), advice_details[key], font=font_advice, anchor="ms", fill="#555555", align="center")

    risk_y_start = advice_y_start + 190 
    draw.line([(60, risk_y_start), (width - 60, risk_y_start)], fill="#EEEEEE", width=2)
    risk_text = f"{t[lang]['risk_group']}: {advice_details['risk_group']}"
    draw.text((width/2, risk_y_start + 50), risk_text, font=font_advice_risk, anchor="ms", fill="#333333")

    # --- AQI Bar ---
    bar_y = height - 150
    bar_height = 60 
    colors_map = {
        '#0099FF': (t[lang]['aqi_level_1'], "0-15"),
        '#2ECC71': (t[lang]['aqi_level_2'], "15-25"),
        '#F1C40F': (t[lang]['aqi_level_3'], "25-37.5"),
        '#E67E22': (t[lang]['aqi_level_4_short'], "37.5-75"),
        '#E74C3C': (t[lang]['aqi_level_5_short'], ">75")
    }
    num_segments = len(colors_map)
    segment_width = (width - 80) / num_segments
    font_bar = create_font(font_bold_bytes, 22) 
    
    for i, (bar_color, (bar_level, bar_range)) in enumerate(colors_map.items()):
        x0 = 40 + i * segment_width
        x1 = x0 + segment_width
        text_color = "black" if bar_color == "#F1C40F" else "white"
        draw.rectangle([(x0, bar_y), (x1, bar_y + bar_height)], fill=bar_color)
        
        text_center_y = bar_y + bar_height / 2
        
        draw.text((x0 + segment_width/2, text_center_y), f"{bar_level}\n{bar_range}", font=font_bar, anchor="mm", fill=text_color, align="center")

    footer_text = t[lang]['report_card_footer']
    draw.text((width - 40, height - 40), footer_text, font=font_footer, anchor="rs", fill="#AAAAAA")
    
    # --- Round corners ---
    mask = Image.new('L', (width, height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), (width, height)], radius=30, fill=255)
    img.putalpha(mask)

    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

