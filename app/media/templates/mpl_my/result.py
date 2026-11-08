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


def render_mpl_my_result(match_data: Dict[str, Any]) -> bytes:
    """
    Render official MPL Malaysia (MPL MY) Match Result Graphic in 1200x675 PNG.
    Visual direction:
      - Deep Royal Navy & Crimson broadcast atmosphere (#060D1F to #0F1D38)
      - Solar gold and electric amber console aesthetic
      - Official MPL Malaysia emblem
      - Distinct wide broadcast card with layered depth
      - Radiant gold winner score highlight & MVP badge
    """
    W, H = 1200, 675
    im = Image.new("RGB", (W, H), color=(6, 13, 31))
    draw = ImageDraw.Draw(im)

    # 1. Base deep royal navy gradient
    for y in range(H):
        ratio = y / H
        r = int(6 + ratio * 8)
        g = int(12 + ratio * 15)
        b = int(28 + ratio * 28)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 2. Ambient lighting & broadcast solar glow
    bg_fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fx_draw = ImageDraw.Draw(bg_fx)

    # Top-left solar gold spotlight
    for rad in range(320, 0, -14):
        alpha = int((1 - rad / 320) * 45)
        fx_draw.ellipse([80 - rad, 80 - rad, 80 + rad, 80 + rad], fill=(234, 179, 8, alpha))

    # Center-bottom ruby amber ambient glow
    for rad in range(280, 0, -14):
        alpha = int((1 - rad / 280) * 35)
        fx_draw.ellipse([W // 2 - rad, H - 120 - rad, W // 2 + rad, H - 120 + rad], fill=(225, 29, 72, alpha))

    im.paste(bg_fx, (0, 0), bg_fx)
    draw = ImageDraw.Draw(im)

    # 3. Main Floating Panoramic Broadcast Card
    card_x = 50
    card_y = 115
    card_w = 1100
    card_h = 450
    card_radius = 16

    # Draw card outer neon rim (Gold to Amber gradient simulation)
    draw.rounded_rectangle([card_x - 2, card_y - 2, card_x + card_w + 2, card_y + card_h + 2], radius=card_radius + 2, fill=(234, 179, 8))
    draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h], radius=card_radius, fill=(11, 22, 48))

    # Inner subtle divider lines on card
    draw.line([(card_x + 320, card_y + 30), (card_x + 320, card_y + card_h - 30)], fill=(24, 45, 85), width=1)
    draw.line([(card_x + card_w - 320, card_y + 30), (card_x + card_w - 320, card_y + card_h - 30)], fill=(24, 45, 85), width=1)

    # 4. Top Header Section (Above card)
    font_league = load_font("Impact.ttf", 30)
    font_sub = load_font("Arial-Bold.ttf", 14)

    mpl_my_logo = os.path.join(LOGOS_DIR, "mpl_my.png")
    header_logo_w = 0
    if os.path.exists(mpl_my_logo):
        try:
            l_img = Image.open(mpl_my_logo).convert("RGBA")
            l_img.thumbnail((110, 72), Image.Resampling.LANCZOS)
            im.paste(l_img, (55, 24), l_img)
            header_logo_w = l_img.width + 16
        except Exception:
            pass

    header_x = 55 + header_logo_w
    draw.text((header_x, 26), "MPL MALAYSIA", fill=(255, 255, 255), font=font_league)

    season_text = str(match_data.get("season") or "SEASON 16").upper()
    stage_text = str(match_data.get("stage") or "MATCH RESULTS").upper()
    sub_title = f"{season_text}   •   {stage_text}"
    draw.text((header_x, 62), sub_title, fill=(250, 204, 21), font=font_sub)

    # Top Right: Shared Channel Brand Badge
    draw_shared_brand_badge(im, W - 180, 36, theme="my")

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
        draw.ellipse([cx_a - 72, center_y - 85 - 72, cx_a + 72, center_y - 85 + 72], fill=(14, 28, 60), outline=(234, 179, 8), width=2)
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
        draw.ellipse([cx_b - 72, center_y - 85 - 72, cx_b + 72, center_y - 85 + 72], fill=(14, 28, 60), outline=(234, 179, 8), width=2)
        im.paste(logo_b, (cx_b - logo_b.width // 2, center_y - 85 - logo_b.height // 2), logo_b)

    tb_w, tb_h = get_text_size(draw, team_b[:14], font_team)
    if win_b:
        draw.rounded_rectangle([cx_b - tb_w // 2 - 14, center_y + 16, cx_b + tb_w // 2 + 14, center_y + 16 + tb_h + 8], radius=6, fill=(245, 158, 11))
        draw.text((cx_b - tb_w // 2, center_y + 19), team_b[:14], fill=(15, 23, 42), font=font_team)
    else:
        draw.text((cx_b - tb_w // 2, center_y + 19), team_b[:14], fill=(241, 245, 249), font=font_team)

    # CENTER SCOREBOARD (Malaysian Solar Gold & Cobalt)
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

    # Glass Score Plate
    plate_w = total_score_w + 50
    plate_h = 134
    plate_x = (W - plate_w) // 2
    plate_y = center_y - 105
    draw.rounded_rectangle([plate_x, plate_y, plate_x + plate_w, plate_y + plate_h], radius=12, fill=(13, 26, 56), outline=(234, 179, 8), width=1)
    draw.line([(plate_x + 14, plate_y), (plate_x + plate_w - 14, plate_y)], fill=(245, 158, 11), width=2)

    # Draw Score A
    color_sa = (252, 211, 77) if win_a else ((224, 242, 254) if score_a is not None else (148, 163, 184))
    draw.text((start_score_x, center_y - 95), score_a_str, fill=color_sa, font=font_score)

    # Dash
    dash_x = start_score_x + sa_w + score_gap
    draw.text((dash_x, center_y - 75), "—", fill=(234, 179, 8), font=font_dash)

    # Score B
    score_b_x = dash_x + dash_w + score_gap
    color_sb = (252, 211, 77) if win_b else ((224, 242, 254) if score_b is not None else (148, 163, 184))
    draw.text((score_b_x, center_y - 95), score_b_str, fill=color_sb, font=font_score)

    # Status Pill
    font_status = load_font("Arial-Bold.ttf", 15)
    status_raw = str(match_data.get("status") or "FINAL").upper()
    series_raw = str(match_data.get("series") or "BO3").upper()

    if "LIVE" in status_raw:
        pill_fill = (220, 38, 38)
        pill_text = f"● LIVE  |  {series_raw}"
    else:
        pill_fill = (245, 158, 11)
        pill_text = f"FINAL  |  {series_raw}"

    pw, ph = get_text_size(draw, pill_text, font_status)
    px = (W - pw) // 2
    py = center_y + 44
    draw.rounded_rectangle([px - 14, py - 4, px + pw + 14, py + ph + 6], radius=8, fill=pill_fill)
    text_c = (15, 23, 42) if "FINAL" in pill_text else (255, 255, 255)
    draw.text((px, py - 1), pill_text, fill=text_c, font=font_status)

    # 6. Center-Bottom MVP Spotlight
    mvp_name = match_data.get("mvp")
    has_valid_mvp = (
        mvp_name
        and str(mvp_name).strip()
        and str(mvp_name).lower() not in ("none", "null", "mavjud emas", "yo'q", "unknown", "")
    )

    if has_valid_mvp:
        mvp_box_y = card_y + card_h - 110
        mvp_label_font = load_font("Arial-Bold.ttf", 13)
        mvp_name_font = load_font("Impact.ttf", 26)

        label_txt = "MATCH MVP"
        name_txt = str(mvp_name).strip().upper()

        nw, nh = get_text_size(draw, name_txt, mvp_name_font)
        box_w = max(260, nw + 70)
        box_h = 58
        box_x = (W - box_w) // 2

        draw.rounded_rectangle([box_x, mvp_box_y, box_x + box_w, mvp_box_y + box_h], radius=10, fill=(13, 26, 56), outline=(245, 158, 11), width=1)
        draw.text((box_x + 18, mvp_box_y + 9), label_txt, fill=(245, 158, 11), font=mvp_label_font)
        draw.text((box_x + 18, mvp_box_y + 25), name_txt, fill=(255, 255, 255), font=mvp_name_font)

        star_cx = box_x + box_w - 32
        star_cy = mvp_box_y + box_h // 2
        draw_vector_star(draw, star_cx, star_cy, r_outer=12, r_inner=5, fill=(245, 158, 11))

    # 7. Bottom Metadata Strip
    draw.line([(50, H - 55), (W - 50, H - 55)], fill=(24, 45, 85), width=1)

    font_meta = load_font("Arial.ttf", 14)
    meta_parts = []
    week_str = match_data.get("week")
    if week_str:
        w_clean = f"WEEK {week_str}" if str(week_str).isdigit() else str(week_str).upper()
        meta_parts.append(w_clean)
    if match_data.get("date"):
        meta_parts.append(str(match_data.get("date")))
    if match_data.get("time"):
        meta_parts.append(str(match_data.get("time")))

    left_str = "   •   ".join(meta_parts) if meta_parts else "MPL MALAYSIA OFFICIAL"
    draw.text((55, H - 42), left_str, fill=(148, 163, 184), font=font_meta)

    right_str = "TELEGRAM: @MURODALIEVGG"
    rw, rh = get_text_size(draw, right_str, font_meta)
    draw.text((W - 55 - rw, H - 42), right_str, fill=(250, 204, 21), font=font_meta)

    return image_to_png_bytes(im)
