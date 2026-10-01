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


def render_mpl_id_upcoming(match_data: Dict[str, Any]) -> bytes:
    """
    Render official MPL Indonesia (MPL ID) Upcoming Match Graphic in 1200x675 PNG.
    Features:
      - Indonesian red, white, and metallic carbon identity
      - Prominent VS emblem with match time and date countdown
      - Status badge: UPCOMING, POSTPONED, or CANCELLED
    """
    W, H = 1200, 675
    im = Image.new("RGB", (W, H), color=(9, 10, 14))
    draw = ImageDraw.Draw(im)

    # 1. Dark carbon gradient background
    for y in range(H):
        ratio = y / H
        r = int(9 + ratio * 8)
        g = int(10 + ratio * 9)
        b = int(14 + ratio * 12)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 2. Geometric background motifs (Red & Silver angled chevrons)
    bg_accent = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    accent_draw = ImageDraw.Draw(bg_accent)

    accent_draw.polygon([(-50, 0), (220, 0), (140, H), (-50, H)], fill=(220, 38, 38, 14))
    accent_draw.polygon([(140, 0), (165, 0), (85, H), (60, H)], fill=(220, 38, 38, 30))

    accent_draw.polygon([(W - 140, 0), (W + 50, 0), (W + 50, H), (W - 60, H)], fill=(148, 163, 184, 12))
    accent_draw.polygon([(W - 165, 0), (W - 140, 0), (W - 85, H), (W - 60, H)], fill=(241, 245, 249, 25))

    # Center ambient red glow
    for rad in range(260, 0, -12):
        alpha = int((1 - rad / 260) * 35)
        accent_draw.ellipse([W // 2 - rad, 320 - rad, W // 2 + rad, 320 + rad], fill=(185, 28, 28, alpha))

    im.paste(bg_accent, (0, 0), bg_accent)
    draw = ImageDraw.Draw(im)

    # 3. Top Header
    font_league = load_font("Impact.ttf", 32)
    font_sub = load_font("Arial-Bold.ttf", 15)

    mpl_id_logo = os.path.join(LOGOS_DIR, "mpl_id.png")
    header_logo_w = 0
    if os.path.exists(mpl_id_logo):
        try:
            l_img = Image.open(mpl_id_logo).convert("RGBA")
            l_img.thumbnail((120, 72), Image.Resampling.LANCZOS)
            im.paste(l_img, (50, 22), l_img)
            header_logo_w = l_img.width + 15
        except Exception:
            pass

    header_x = 50 + header_logo_w
    draw.text((header_x, 26), "MPL INDONESIA", fill=(255, 255, 255), font=font_league)

    season_text = str(match_data.get("season") or "SEASON 14").upper()
    stage_text = str(match_data.get("stage") or "MATCH SCHEDULE").upper()
    full_sub = f"{stage_text}  •  {season_text}"
    draw.text((header_x, 62), full_sub, fill=(220, 38, 38), font=font_sub)

    draw_shared_brand_badge(im, W - 180, 34, theme="id")

    draw.line([(50, 105), (W - 50, 105)], fill=(40, 45, 58), width=2)
    draw.line([(50, 105), (320, 105)], fill=(220, 38, 38), width=3)

    # 4. Center Section: Teams & Upcoming VS Schedule
    team_a = str(match_data.get("team_a") or "TEAM A").upper()
    team_b = str(match_data.get("team_b") or "TEAM B").upper()
    time_str = str(match_data.get("time") or "15:00 WIB").upper()
    date_str = str(match_data.get("date") or "29 SEPTEMBER").upper()
    series_raw = str(match_data.get("series") or "BO3").upper()
    status_raw = str(match_data.get("status") or "UPCOMING").upper()

    center_y = 310

    # Team A (Left)
    cx_a = 230
    logo_a = load_team_logo(team_a, match_data.get("team_a_logo"), max_size=(130, 130))
    if logo_a:
        im.paste(logo_a, (cx_a - logo_a.width // 2, center_y - 85 - logo_a.height // 2), logo_a)

    font_team = load_font("Arial-Bold.ttf", 32)
    ta_w, ta_h = get_text_size(draw, team_a[:14], font_team)
    draw.text((cx_a - ta_w // 2, center_y + 18), team_a[:14], fill=(241, 245, 249), font=font_team)

    # Team B (Right)
    cx_b = W - 230
    logo_b = load_team_logo(team_b, match_data.get("team_b_logo"), max_size=(130, 130))
    if logo_b:
        im.paste(logo_b, (cx_b - logo_b.width // 2, center_y - 85 - logo_b.height // 2), logo_b)

    tb_w, tb_h = get_text_size(draw, team_b[:14], font_team)
    draw.text((cx_b - tb_w // 2, center_y + 18), team_b[:14], fill=(241, 245, 249), font=font_team)

    # Center VS & Time Display
    font_vs = load_font("Impact.ttf", 78)
    vw, vh = get_text_size(draw, "VS", font_vs)
    draw.text(((W - vw) // 2, center_y - 95), "VS", fill=(220, 38, 38), font=font_vs)

    # Time Callout
    font_time = load_font("Impact.ttf", 46)
    tw, th = get_text_size(draw, time_str, font_time)
    draw.text(((W - tw) // 2, center_y - 10), time_str, fill=(255, 255, 255), font=font_time)

    # Date & Series
    font_series = load_font("Arial-Bold.ttf", 17)
    date_series_text = f"{date_str}   •   {series_raw}"
    dw, dh = get_text_size(draw, date_series_text, font_series)
    draw.text(((W - dw) // 2, center_y + 44), date_series_text, fill=(203, 213, 225), font=font_series)

    # Status Pill (UPCOMING, POSTPONED, CANCELLED)
    font_status = load_font("Arial-Bold.ttf", 15)
    if "POSTPONED" in status_raw:
        badge_bg, badge_border = (60, 40, 15), (245, 158, 11)
    elif "CANCELLED" in status_raw:
        badge_bg, badge_border = (50, 15, 20), (239, 68, 68)
    else:
        badge_bg, badge_border = (20, 24, 32), (220, 38, 38)

    st_w, st_h = get_text_size(draw, status_raw, font_status)
    bw, bh = st_w + 34, 30
    bx, by = (W - bw) // 2, center_y + 78
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=6, fill=badge_bg, outline=badge_border, width=1)
    draw.text(((W - st_w) // 2, by + 6), status_raw, fill=(241, 245, 249), font=font_status)

    # 5. Bottom Metadata
    draw.line([(50, H - 75), (W - 50, H - 75)], fill=(40, 45, 58), width=2)
    draw.line([(W - 320, H - 75), (W - 50, H - 75)], fill=(220, 38, 38), width=3)

    font_meta = load_font("Arial-Bold.ttf", 15)
    week_val = match_data.get("week")
    week_str = f"WEEK {week_val}" if week_val else "MATCH SCHEDULE"
    left_meta = f"{week_str}   •   {date_str}"
    draw.text((50, H - 50), left_meta, fill=(203, 213, 225), font=font_meta)

    right_meta = "INDONESIA ESPORTS   •   #MPLID"
    rm_w, rm_h = get_text_size(draw, right_meta, font_meta)
    draw.text((W - 50 - rm_w, H - 50), right_meta, fill=(148, 163, 184), font=font_meta)

    return image_to_png_bytes(im)
