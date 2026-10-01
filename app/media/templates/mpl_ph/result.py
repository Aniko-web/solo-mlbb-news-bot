import os
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont

from app.media.templates.common import (
    load_font,
    get_text_size,
    load_team_logo,
    draw_shared_brand_badge,
    draw_vector_star,
    image_to_png_bytes,
    LOGOS_DIR
)


def render_mpl_ph_result(match_data: Dict[str, Any]) -> bytes:
    """
    Render official MPL Philippines (MPL PH) Match Result Graphic in 1200x675 PNG.
    Visual direction:
      - Deep navy / midnight blue broadcast atmosphere (#050B16 to #0B172B)
      - Solar gold and marine cyan broadcast console aesthetic
      - Official horned & solar MPL PH emblem
      - Distinct wide broadcast card with layered depth
      - Radiant gold winner score highlight & MVP solar badge
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

    # Top-left marine cyan spotlight
    for rad in range(320, 0, -14):
        alpha = int((1 - rad / 320) * 45)
        fx_draw.ellipse([80 - rad, 80 - rad, 80 + rad, 80 + rad], fill=(14, 165, 233, alpha))

    # Center-bottom solar gold ambient glow
    for rad in range(280, 0, -14):
        alpha = int((1 - rad / 280) * 35)
        fx_draw.ellipse([W // 2 - rad, H - 120 - rad, W // 2 + rad, H - 120 + rad], fill=(245, 158, 11, alpha))

    im.paste(bg_fx, (0, 0), bg_fx)
    draw = ImageDraw.Draw(im)

    # 3. Main Floating Panoramic Broadcast Card
    # Dimensions: 1100 × 450 px, centered at y = 115
    card_x = 50
    card_y = 115
    card_w = 1100
    card_h = 450
    card_radius = 16

    # Draw card outer neon rim (Cyan to Gold horizontal gradient simulation)
    draw.rounded_rectangle([card_x - 2, card_y - 2, card_x + card_w + 2, card_y + card_h + 2], radius=card_radius + 2, fill=(14, 165, 233))
    draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h], radius=card_radius, fill=(9, 20, 42))

    # Inner subtle divider lines on card
    draw.line([(card_x + 320, card_y + 30), (card_x + 320, card_y + card_h - 30)], fill=(20, 40, 75), width=1)
    draw.line([(card_x + card_w - 320, card_y + 30), (card_x + card_w - 320, card_y + card_h - 30)], fill=(20, 40, 75), width=1)

    # 4. Top Header Section (Above card)
    font_league = load_font("Impact.ttf", 30)
    font_sub = load_font("Arial-Bold.ttf", 14)

    # Official Horned & Sun MPL PH Crest
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
    stage_text = str(match_data.get("stage") or "MATCH RESULTS").upper()
    sub_title = f"{season_text}   •   {stage_text}"
    draw.text((header_x, 62), sub_title, fill=(56, 189, 248), font=font_sub)

    # Top Right: Shared Channel Brand Badge
    draw_shared_brand_badge(im, W - 180, 36, theme="ph")

    # 5. Center Section: Teams & Solar Scoreboard
    team_a = str(match_data.get("team_a") or "TEAM A").upper()
    team_b = str(match_data.get("team_b") or "TEAM B").upper()
    score_a = match_data.get("score_a", 0)
    score_b = match_data.get("score_b", 0)

    win_a = score_a is not None and score_b is not None and score_a > score_b
    win_b = score_a is not None and score_b is not None and score_b > score_a

    center_y = card_y + 190

    # Team A (Left Console Wing)
    cx_a = card_x + 160
    logo_a = load_team_logo(team_a, match_data.get("team_a_logo"), max_size=(130, 130))
    if logo_a:
        # Subtle cyan back-circle for logo
        draw.ellipse([cx_a - 72, center_y - 85 - 72, cx_a + 72, center_y - 85 + 72], fill=(12, 32, 62), outline=(14, 165, 233), width=2)
        im.paste(logo_a, (cx_a - logo_a.width // 2, center_y - 85 - logo_a.height // 2), logo_a)

    font_team = load_font("Arial-Bold.ttf", 30)
    ta_w, ta_h = get_text_size(draw, team_a[:14], font_team)
    if win_a:
        draw.rounded_rectangle([cx_a - ta_w // 2 - 14, center_y + 16, cx_a + ta_w // 2 + 14, center_y + 16 + ta_h + 8], radius=6, fill=(245, 158, 11))
        draw.text((cx_a - ta_w // 2, center_y + 19), team_a[:14], fill=(15, 23, 42), font=font_team)
    else:
        draw.text((cx_a - ta_w // 2, center_y + 19), team_a[:14], fill=(241, 245, 249), font=font_team)

    # Team B (Right Console Wing)
    cx_b = card_x + card_w - 160
    logo_b = load_team_logo(team_b, match_data.get("team_b_logo"), max_size=(130, 130))
    if logo_b:
        draw.ellipse([cx_b - 72, center_y - 85 - 72, cx_b + 72, center_y - 85 + 72], fill=(12, 32, 62), outline=(14, 165, 233), width=2)
        im.paste(logo_b, (cx_b - logo_b.width // 2, center_y - 85 - logo_b.height // 2), logo_b)

    tb_w, tb_h = get_text_size(draw, team_b[:14], font_team)
    if win_b:
        draw.rounded_rectangle([cx_b - tb_w // 2 - 14, center_y + 16, cx_b + tb_w // 2 + 14, center_y + 16 + tb_h + 8], radius=6, fill=(245, 158, 11))
        draw.text((cx_b - tb_w // 2, center_y + 19), team_b[:14], fill=(15, 23, 42), font=font_team)
    else:
        draw.text((cx_b - tb_w // 2, center_y + 19), team_b[:14], fill=(241, 245, 249), font=font_team)

    # CENTER SCOREBOARD (Philippine Gold & Electric Cyan)
    font_score = load_font("Impact.ttf", 125)
    font_dash = load_font("Arial-Bold.ttf", 85)

    score_a_str = str(score_a if score_a is not None else "-")
    score_b_str = str(score_b if score_b is not None else "-")

    sa_w, sa_h = get_text_size(draw, score_a_str, font_score)
    sb_w, sb_h = get_text_size(draw, score_b_str, font_score)
    dash_w, dash_h = get_text_size(draw, "—", font_dash)

    score_gap = 42
    total_score_w = sa_w + score_gap + dash_w + score_gap + sb_w
    start_score_x = (W - total_score_w) // 2

    # Glass Score Plate (Deep Navy Glass with Gold Trim)
    plate_w = total_score_w + 50
    plate_h = 134
    plate_x = (W - plate_w) // 2
    plate_y = center_y - 105
    draw.rounded_rectangle([plate_x, plate_y, plate_x + plate_w, plate_y + plate_h], radius=12, fill=(11, 24, 52), outline=(14, 165, 233), width=1)
    draw.line([(plate_x + 14, plate_y), (plate_x + plate_w - 14, plate_y)], fill=(245, 158, 11), width=2)

    # Draw Score A
    color_sa = (252, 211, 77) if win_a else ((224, 242, 254) if score_a is not None else (148, 163, 184))
    draw.text((start_score_x, center_y - 95), score_a_str, fill=color_sa, font=font_score)

    # Dash
    dash_x = start_score_x + sa_w + score_gap
    draw.text((dash_x, center_y - 75), "—", fill=(14, 165, 233), font=font_dash)

    # Score B
    score_b_x = dash_x + dash_w + score_gap
    color_sb = (252, 211, 77) if win_b else ((224, 242, 254) if score_b is not None else (148, 163, 184))
    draw.text((score_b_x, center_y - 95), score_b_str, fill=color_sb, font=font_score)

    # Status Pill
    font_status = load_font("Arial-Bold.ttf", 15)
    status_raw = str(match_data.get("status") or "FINAL").upper()
    series_raw = str(match_data.get("series") or "BO3").upper()

    if "LIVE" in status_raw:
        status_label = f"● LIVE  •  {series_raw}"
        pill_bg = (14, 165, 233)
        pill_border = (56, 189, 248)
        text_color = (255, 255, 255)
    else:
        status_label = f"{series_raw}  •  FINAL" if series_raw else "FINAL"
        pill_bg = (14, 28, 54)
        pill_border = (245, 158, 11)
        text_color = (248, 250, 252)

    st_w, st_h = get_text_size(draw, status_label, font_status)
    pw, ph = st_w + 36, 32
    px, py = (W - pw) // 2, center_y + 44
    draw.rounded_rectangle([px, py, px + pw, py + ph], radius=16, fill=pill_bg, outline=pill_border, width=1)
    draw.text(((W - st_w) // 2, py + 7), status_label, fill=text_color, font=font_status)

    # MVP Section (Golden Solar Ribbon)
    mvp_name = match_data.get("mvp")
    if mvp_name and str(mvp_name).strip() and str(mvp_name).lower() not in ("unknown", "none", "null", ""):
        font_mvp = load_font("Impact.ttf", 22)
        mvp_clean = str(mvp_name).strip().upper()
        mvp_text = f"MVP: {mvp_clean}"
        mw, mh = get_text_size(draw, mvp_text, font_mvp)

        card_w = mw + 54
        card_h = 36
        card_x = (W - card_w) // 2
        card_y = py + ph + 16

        draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h], radius=8, fill=(15, 30, 60), outline=(245, 158, 11), width=1)
        draw_vector_star(draw, card_x + 18, card_y + 18, r_outer=8, r_inner=3.5, fill=(255, 215, 0))
        draw.text((card_x + 32, card_y + 6), mvp_text, fill=(253, 224, 71), font=font_mvp)

    # 6. Bottom Metadata Section
    font_meta = load_font("Arial-Bold.ttf", 15)
    week_val = match_data.get("week")
    week_str = f"WEEK {week_val}" if week_val else "MATCH RESULTS"
    date_val = str(match_data.get("date") or "SEPTEMBER 29").upper()
    left_meta = f"{week_str}   •   {date_val}"
    draw.text((card_x + 10, H - 48), left_meta, fill=(56, 189, 248), font=font_meta)

    right_meta = "GAME NA DITO   •   #MPLPH   •   PHILIPPINES ESPORTS"
    rm_w, rm_h = get_text_size(draw, right_meta, font_meta)
    draw.text((card_x + card_w - rm_w - 10, H - 48), right_meta, fill=(148, 163, 184), font=font_meta)

    return image_to_png_bytes(im)
