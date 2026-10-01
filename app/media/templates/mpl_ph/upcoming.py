import os
from typing import Dict, Any
from PIL import Image, ImageDraw, ImageFont

from app.media.templates.common import (
    load_font,
    get_text_size,
    load_team_logo,
    draw_shared_brand_badge,
    image_to_png_bytes,
    LOGOS_DIR
)


def render_mpl_ph_upcoming(match_data: Dict[str, Any]) -> bytes:
    """
    Render official MPL Philippines (MPL PH) Upcoming Match Graphic in 1200x675 PNG.
    Features:
      - Deep navy / midnight blue and solar gold broadcast console aesthetic
      - Electric cyan VS emblem with match time and date
      - Status pill: UPCOMING, POSTPONED, or CANCELLED
    """
    W, H = 1200, 675
    im = Image.new("RGB", (W, H), color=(6, 11, 22))
    draw = ImageDraw.Draw(im)

    # 1. Base deep midnight navy gradient
    for y in range(H):
        ratio = y / H
        r = int(5 + ratio * 6)
        g = int(9 + ratio * 14)
        b = int(18 + ratio * 25)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 2. Ambient lighting & broadcast solar glow
    bg_fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fx_draw = ImageDraw.Draw(bg_fx)

    for rad in range(320, 0, -14):
        alpha = int((1 - rad / 320) * 45)
        fx_draw.ellipse([80 - rad, 80 - rad, 80 + rad, 80 + rad], fill=(14, 165, 233, alpha))

    for rad in range(280, 0, -14):
        alpha = int((1 - rad / 280) * 35)
        fx_draw.ellipse([W // 2 - rad, H - 120 - rad, W // 2 + rad, H - 120 + rad], fill=(245, 158, 11, alpha))

    im.paste(bg_fx, (0, 0), bg_fx)
    draw = ImageDraw.Draw(im)

    # 3. Main Floating Panoramic Broadcast Card
    card_x = 50
    card_y = 115
    card_w = 1100
    card_h = 450
    card_radius = 16

    draw.rounded_rectangle([card_x - 2, card_y - 2, card_x + card_w + 2, card_y + card_h + 2], radius=card_radius + 2, fill=(14, 165, 233))
    draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h], radius=card_radius, fill=(9, 20, 42))

    draw.line([(card_x + 320, card_y + 30), (card_x + 320, card_y + card_h - 30)], fill=(20, 40, 75), width=1)
    draw.line([(card_x + card_w - 320, card_y + 30), (card_x + card_w - 320, card_y + card_h - 30)], fill=(20, 40, 75), width=1)

    # 4. Top Header Section
    font_league = load_font("Impact.ttf", 30)
    font_sub = load_font("Arial-Bold.ttf", 14)

    mpl_ph_logo = os.path.join(LOGOS_DIR, "mpl_ph.png")
    header_logo_w = 0
    if os.path.exists(mpl_ph_logo):
        try:
            l_img = Image.open(mpl_ph_logo).convert("RGBA")
            l_img.thumbnail((110, 72), Image.Resampling.LANCZOS)
            im.paste(l_img, (55, 24), l_img)
            header_logo_w = l_img.width + 16
        except Exception:
            pass

    header_x = 55 + header_logo_w
    draw.text((header_x, 26), "MPL PHILIPPINES", fill=(255, 255, 255), font=font_league)

    season_text = str(match_data.get("season") or "SEASON 14").upper()
    stage_text = str(match_data.get("stage") or "MATCH SCHEDULE").upper()
    sub_title = f"{season_text}   •   {stage_text}"
    draw.text((header_x, 62), sub_title, fill=(56, 189, 248), font=font_sub)

    draw_shared_brand_badge(im, W - 180, 36, theme="ph")

    # 5. Center Section: Teams & Upcoming Schedule
    team_a = str(match_data.get("team_a") or "TEAM A").upper()
    team_b = str(match_data.get("team_b") or "TEAM B").upper()
    time_str = str(match_data.get("time") or "17:00 PHT").upper()
    date_str = str(match_data.get("date") or "SEPTEMBER 29").upper()
    series_raw = str(match_data.get("series") or "BO3").upper()
    status_raw = str(match_data.get("status") or "UPCOMING").upper()

    center_y = card_y + 190

    # Team A (Left)
    cx_a = card_x + 160
    logo_a = load_team_logo(team_a, match_data.get("team_a_logo"), max_size=(130, 130))
    if logo_a:
        draw.ellipse([cx_a - 72, center_y - 85 - 72, cx_a + 72, center_y - 85 + 72], fill=(12, 32, 62), outline=(14, 165, 233), width=2)
        im.paste(logo_a, (cx_a - logo_a.width // 2, center_y - 85 - logo_a.height // 2), logo_a)

    font_team = load_font("Arial-Bold.ttf", 30)
    ta_w, ta_h = get_text_size(draw, team_a[:14], font_team)
    draw.text((cx_a - ta_w // 2, center_y + 19), team_a[:14], fill=(241, 245, 249), font=font_team)

    # Team B (Right)
    cx_b = card_x + card_w - 160
    logo_b = load_team_logo(team_b, match_data.get("team_b_logo"), max_size=(130, 130))
    if logo_b:
        draw.ellipse([cx_b - 72, center_y - 85 - 72, cx_b + 72, center_y - 85 + 72], fill=(12, 32, 62), outline=(14, 165, 233), width=2)
        im.paste(logo_b, (cx_b - logo_b.width // 2, center_y - 85 - logo_b.height // 2), logo_b)

    tb_w, tb_h = get_text_size(draw, team_b[:14], font_team)
    draw.text((cx_b - tb_w // 2, center_y + 19), team_b[:14], fill=(241, 245, 249), font=font_team)

    # Center VS & Time Display
    font_vs = load_font("Impact.ttf", 78)
    vw, vh = get_text_size(draw, "VS", font_vs)
    draw.text(((W - vw) // 2, center_y - 95), "VS", fill=(14, 165, 233), font=font_vs)

    # Match Time (Philippine Gold)
    font_time = load_font("Impact.ttf", 46)
    tw, th = get_text_size(draw, time_str, font_time)
    draw.text(((W - tw) // 2, center_y - 10), time_str, fill=(253, 224, 71), font=font_time)

    # Date & Series
    font_series = load_font("Arial-Bold.ttf", 17)
    date_series_text = f"{date_str}   •   {series_raw}"
    dw, dh = get_text_size(draw, date_series_text, font_series)
    draw.text(((W - dw) // 2, center_y + 44), date_series_text, fill=(224, 242, 254), font=font_series)

    # Status Pill
    font_status = load_font("Arial-Bold.ttf", 15)
    if "POSTPONED" in status_raw:
        pill_bg, pill_border = (60, 40, 15), (245, 158, 11)
    elif "CANCELLED" in status_raw:
        pill_bg, pill_border = (50, 15, 20), (239, 68, 68)
    else:
        pill_bg, pill_border = (14, 28, 54), (14, 165, 233)

    st_w, st_h = get_text_size(draw, status_raw, font_status)
    pw, ph = st_w + 34, 30
    px, py = (W - pw) // 2, center_y + 78
    draw.rounded_rectangle([px, py, px + pw, py + ph], radius=15, fill=pill_bg, outline=pill_border, width=1)
    draw.text(((W - st_w) // 2, py + 6), status_raw, fill=(248, 250, 252), font=font_status)

    # 6. Bottom Metadata
    font_meta = load_font("Arial-Bold.ttf", 15)
    week_val = match_data.get("week")
    week_str = f"WEEK {week_val}" if week_val else "MATCH SCHEDULE"
    left_meta = f"{week_str}   •   {date_str}"
    draw.text((card_x + 10, H - 48), left_meta, fill=(56, 189, 248), font=font_meta)

    right_meta = "GAME NA DITO   •   #MPLPH   •   PHILIPPINES ESPORTS"
    rm_w, rm_h = get_text_size(draw, right_meta, font_meta)
    draw.text((card_x + card_w - rm_w - 10, H - 48), right_meta, fill=(148, 163, 184), font=font_meta)

    return image_to_png_bytes(im)
