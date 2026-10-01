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


def render_mpl_id_result(match_data: Dict[str, Any]) -> bytes:
    """
    Render official MPL Indonesia (MPL ID) Match Result Graphic in 1200x675 PNG.
    Visual direction:
      - Dark obsidian / carbon background (#090A0E to #12141C)
      - Sharp geometric cuts, red and silver/white accents inspired by Indonesian esports
      - Official winged MPL ID trophy logo
      - High contrast, massive readable score (Score is the strongest visual element)
      - Sleek MVP card when available
    """
    W, H = 1200, 675
    im = Image.new("RGB", (W, H), color=(9, 10, 14))
    draw = ImageDraw.Draw(im)

    # 1. Base dark background gradient (Carbon / Dark Slate)
    for y in range(H):
        ratio = y / H
        r = int(9 + ratio * 8)
        g = int(10 + ratio * 9)
        b = int(14 + ratio * 12)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 2. Geometric background motifs (Red & Silver Indonesian esports angle slashes)
    bg_accent = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    accent_draw = ImageDraw.Draw(bg_accent)

    # Left-side sharp red blade accent
    accent_draw.polygon([(-50, 0), (220, 0), (140, H), (-50, H)], fill=(220, 38, 38, 14))
    accent_draw.polygon([(140, 0), (165, 0), (85, H), (60, H)], fill=(220, 38, 38, 30))

    # Right-side silver blade accent
    accent_draw.polygon([(W - 140, 0), (W + 50, 0), (W + 50, H), (W - 60, H)], fill=(148, 163, 184, 12))
    accent_draw.polygon([(W - 165, 0), (W - 140, 0), (W - 85, H), (W - 60, H)], fill=(241, 245, 249, 25))

    # Subtle radial glow behind score center
    for rad in range(240, 0, -12):
        alpha = int((1 - rad / 240) * 35)
        accent_draw.ellipse([W // 2 - rad, 320 - rad, W // 2 + rad, 320 + rad], fill=(185, 28, 28, alpha))

    im.paste(bg_accent, (0, 0), bg_accent)
    draw = ImageDraw.Draw(im)

    # 3. Top Header
    font_league = load_font("Impact.ttf", 32)
    font_sub = load_font("Arial-Bold.ttf", 15)

    # Official Winged MPL ID Crest
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

    # Header texts
    header_x = 50 + header_logo_w
    draw.text((header_x, 26), "MPL INDONESIA", fill=(255, 255, 255), font=font_league)

    # Season and Stage subtitle
    season_text = str(match_data.get("season") or "SEASON 14").upper()
    stage_text = str(match_data.get("stage") or "REGULAR SEASON").upper()
    full_sub = f"{stage_text}  •  {season_text}"
    draw.text((header_x, 62), full_sub, fill=(220, 38, 38), font=font_sub)

    # Top Right: Shared Channel Brand Badge
    draw_shared_brand_badge(im, W - 180, 34, theme="id")

    # Header sharp red dividing rule
    draw.line([(50, 105), (W - 50, 105)], fill=(40, 45, 58), width=2)
    draw.line([(50, 105), (320, 105)], fill=(220, 38, 38), width=3)

    # 4. Center Section: Teams & High Contrast Dominant Score
    team_a = str(match_data.get("team_a") or "TEAM A").upper()
    team_b = str(match_data.get("team_b") or "TEAM B").upper()
    score_a = match_data.get("score_a", 0)
    score_b = match_data.get("score_b", 0)

    # Status handling (FINAL, LIVE, etc.)
    status_raw = str(match_data.get("status") or "FINAL").upper()
    series_raw = str(match_data.get("series") or "BO3").upper()

    win_a = score_a is not None and score_b is not None and score_a > score_b
    win_b = score_a is not None and score_b is not None and score_b > score_a

    # Layout coordinates
    center_y = 310

    # Team A Area (Left)
    cx_a = 230
    logo_a = load_team_logo(team_a, match_data.get("team_a_logo"), max_size=(130, 130))
    if logo_a:
        im.paste(logo_a, (cx_a - logo_a.width // 2, center_y - 85 - logo_a.height // 2), logo_a)

    font_team = load_font("Arial-Bold.ttf", 32)
    ta_w, ta_h = get_text_size(draw, team_a[:14], font_team)
    # Winner highlight pill or clean white
    if win_a:
        draw.rounded_rectangle([cx_a - ta_w // 2 - 14, center_y + 15, cx_a + ta_w // 2 + 14, center_y + 15 + ta_h + 8], radius=6, fill=(220, 38, 38))
        draw.text((cx_a - ta_w // 2, center_y + 18), team_a[:14], fill=(255, 255, 255), font=font_team)
    else:
        draw.text((cx_a - ta_w // 2, center_y + 18), team_a[:14], fill=(226, 232, 240), font=font_team)

    # Team B Area (Right)
    cx_b = W - 230
    logo_b = load_team_logo(team_b, match_data.get("team_b_logo"), max_size=(130, 130))
    if logo_b:
        im.paste(logo_b, (cx_b - logo_b.width // 2, center_y - 85 - logo_b.height // 2), logo_b)

    tb_w, tb_h = get_text_size(draw, team_b[:14], font_team)
    if win_b:
        draw.rounded_rectangle([cx_b - tb_w // 2 - 14, center_y + 15, cx_b + tb_w // 2 + 14, center_y + 15 + tb_h + 8], radius=6, fill=(220, 38, 38))
        draw.text((cx_b - tb_w // 2, center_y + 18), team_b[:14], fill=(255, 255, 255), font=font_team)
    else:
        draw.text((cx_b - tb_w // 2, center_y + 18), team_b[:14], fill=(226, 232, 240), font=font_team)

    # CENTER SCOREBOARD (Highest Visual Weight)
    font_score = load_font("Impact.ttf", 130)
    font_dash = load_font("Arial-Bold.ttf", 90)

    score_a_str = str(score_a if score_a is not None else "-")
    score_b_str = str(score_b if score_b is not None else "-")

    sa_w, sa_h = get_text_size(draw, score_a_str, font_score)
    sb_w, sb_h = get_text_size(draw, score_b_str, font_score)
    dash_w, dash_h = get_text_size(draw, "—", font_dash)

    score_gap = 45
    total_score_w = sa_w + score_gap + dash_w + score_gap + sb_w
    start_score_x = (W - total_score_w) // 2

    # Score Backing Plate (Sharp Gunmetal & Red)
    plate_w = total_score_w + 54
    plate_h = 136
    plate_x = (W - plate_w) // 2
    plate_y = center_y - 106
    draw.rounded_rectangle([plate_x, plate_y, plate_x + plate_w, plate_y + plate_h], radius=8, fill=(13, 15, 20), outline=(38, 44, 58), width=1)
    draw.line([(plate_x + 14, plate_y), (plate_x + plate_w - 14, plate_y)], fill=(220, 38, 38), width=2)
    draw.line([(plate_x + 14, plate_y + plate_h), (plate_x + plate_w - 14, plate_y + plate_h)], fill=(220, 38, 38), width=2)

    # Draw Score A
    color_sa = (255, 255, 255) if win_a else ((203, 213, 225) if score_a is not None else (148, 163, 184))
    draw.text((start_score_x, center_y - 95), score_a_str, fill=color_sa, font=font_score)

    # Draw Dash
    dash_x = start_score_x + sa_w + score_gap
    draw.text((dash_x, center_y - 75), "—", fill=(220, 38, 38), font=font_dash)

    # Draw Score B
    score_b_x = dash_x + dash_w + score_gap
    color_sb = (255, 255, 255) if win_b else ((203, 213, 225) if score_b is not None else (148, 163, 184))
    draw.text((score_b_x, center_y - 95), score_b_str, fill=color_sb, font=font_score)

    # Status Badge (FINAL or LIVE)
    font_status = load_font("Arial-Bold.ttf", 16)
    if "LIVE" in status_raw:
        status_label = f"● LIVE  •  {series_raw}"
        badge_bg = (185, 28, 28)
        badge_border = (239, 68, 68)
        text_color = (255, 255, 255)
    else:
        status_label = f"{series_raw}  •  FINAL" if series_raw else "FINAL"
        badge_bg = (24, 28, 38)
        badge_border = (220, 38, 38)
        text_color = (241, 245, 249)

    st_w, st_h = get_text_size(draw, status_label, font_status)
    badge_w = st_w + 36
    badge_h = 32
    badge_x = (W - badge_w) // 2
    badge_y = center_y + 45
    draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], radius=6, fill=badge_bg, outline=badge_border, width=1)
    draw.text(((W - st_w) // 2, badge_y + 7), status_label, fill=text_color, font=font_status)

    # MVP Card Section (Cleanly omitted if not present)
    mvp_name = match_data.get("mvp")
    if mvp_name and str(mvp_name).strip() and str(mvp_name).lower() not in ("unknown", "none", "null", ""):
        font_mvp = load_font("Impact.ttf", 22)
        mvp_clean = str(mvp_name).strip().upper()
        mvp_text = f"MVP: {mvp_clean}"
        mw, mh = get_text_size(draw, mvp_text, font_mvp)

        card_w = mw + 54
        card_h = 36
        card_x = (W - card_w) // 2
        card_y = badge_y + badge_h + 16

        draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h], radius=6, fill=(18, 22, 30), outline=(212, 175, 55), width=1)
        draw_vector_star(draw, card_x + 18, card_y + 18, r_outer=8, r_inner=3.5, fill=(255, 215, 0))
        draw.text((card_x + 32, card_y + 6), mvp_text, fill=(255, 215, 0), font=font_mvp)

    # 5. Bottom Metadata Section
    draw.line([(50, H - 75), (W - 50, H - 75)], fill=(40, 45, 58), width=2)
    draw.line([(W - 320, H - 75), (W - 50, H - 75)], fill=(220, 38, 38), width=3)

    font_meta = load_font("Arial-Bold.ttf", 15)
    week_val = match_data.get("week")
    week_str = f"WEEK {week_val}" if week_val else "MATCH RESULTS"
    date_val = str(match_data.get("date") or "29 SEPTEMBER 2026").upper()
    left_meta = f"{week_str}   •   {date_val}"
    draw.text((50, H - 50), left_meta, fill=(203, 213, 225), font=font_meta)

    right_meta = "INDONESIA ESPORTS   •   #MPLID"
    rm_w, rm_h = get_text_size(draw, right_meta, font_meta)
    draw.text((W - 50 - rm_w, H - 50), right_meta, fill=(148, 163, 184), font=font_meta)

    return image_to_png_bytes(im)
