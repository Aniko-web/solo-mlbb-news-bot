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


def render_mpl_my_upcoming(match_data: Dict[str, Any]) -> bytes:
    """
    Render official MPL Malaysia (MPL MY) Upcoming Match Graphic in 1200x675 PNG.
    Features:
      - Deep Royal Navy & Crimson broadcast aesthetic
      - Dual-tone Win-Rate progress bar
      - AI predicted score capsule
      - Match time (UZ / MYT) and countdown info
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

    for rad in range(320, 0, -14):
        alpha = int((1 - rad / 320) * 45)
        fx_draw.ellipse([80 - rad, 80 - rad, 80 + rad, 80 + rad], fill=(234, 179, 8, alpha))

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

    draw.rounded_rectangle([card_x - 2, card_y - 2, card_x + card_w + 2, card_y + card_h + 2], radius=card_radius + 2, fill=(234, 179, 8))
    draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h], radius=card_radius, fill=(11, 22, 48))

    draw.line([(card_x + 320, card_y + 30), (card_x + 320, card_y + card_h - 30)], fill=(24, 45, 85), width=1)
    draw.line([(card_x + card_w - 320, card_y + 30), (card_x + card_w - 320, card_y + card_h - 30)], fill=(24, 45, 85), width=1)

    # 4. Top Header Section
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
    stage_text = str(match_data.get("stage") or "MATCH SCHEDULE").upper()
    sub_title = f"{season_text}   •   {stage_text}"
    draw.text((header_x, 62), sub_title, fill=(250, 204, 21), font=font_sub)

    draw_shared_brand_badge(im, W - 180, 36, theme="my")

    # 5. Center Section: Teams & VS Emblem
    team_a = str(match_data.get("team_a") or "TEAM A").upper()
    team_b = str(match_data.get("team_b") or "TEAM B").upper()

    center_y = card_y + 190

    # Team A (Left)
    cx_a = card_x + 160
    logo_a = load_team_logo(team_a, match_data.get("team_a_logo"), max_size=(130, 130))
    if logo_a:
        draw.ellipse([cx_a - 72, center_y - 85 - 72, cx_a + 72, center_y - 85 + 72], fill=(14, 28, 60), outline=(234, 179, 8), width=2)
        im.paste(logo_a, (cx_a - logo_a.width // 2, center_y - 85 - logo_a.height // 2), logo_a)

    font_team = load_font("Arial-Bold.ttf", 30)
    ta_w, ta_h = get_text_size(draw, team_a[:14], font_team)
    draw.text((cx_a - ta_w // 2, center_y + 19), team_a[:14], fill=(241, 245, 249), font=font_team)

    # Team B (Right)
    cx_b = card_x + card_w - 160
    logo_b = load_team_logo(team_b, match_data.get("team_b_logo"), max_size=(130, 130))
    if logo_b:
        draw.ellipse([cx_b - 72, center_y - 85 - 72, cx_b + 72, center_y - 85 + 72], fill=(14, 28, 60), outline=(234, 179, 8), width=2)
        im.paste(logo_b, (cx_b - logo_b.width // 2, center_y - 85 - logo_b.height // 2), logo_b)

    tb_w, tb_h = get_text_size(draw, team_b[:14], font_team)
    draw.text((cx_b - tb_w // 2, center_y + 19), team_b[:14], fill=(241, 245, 249), font=font_team)

    # CENTER CONSOLE: Match Date / Time + VS
    font_vs = load_font("Impact.ttf", 74)
    vw, vh = get_text_size(draw, "VS", font_vs)

    vs_box_w = 260
    vs_box_h = 134
    vs_box_x = (W - vs_box_w) // 2
    vs_box_y = center_y - 105

    draw.rounded_rectangle([vs_box_x, vs_box_y, vs_box_x + vs_box_w, vs_box_y + vs_box_h], radius=12, fill=(13, 26, 56), outline=(234, 179, 8), width=1)
    draw.line([(vs_box_x + 14, vs_box_y), (vs_box_x + vs_box_w - 14, vs_box_y)], fill=(245, 158, 11), width=2)

    # Draw "VS"
    draw.text(((W - vw) // 2, vs_box_y + 10), "VS", fill=(250, 204, 21), font=font_vs)

    # Scheduled Time inside VS box
    font_time = load_font("Arial-Bold.ttf", 16)
    time_str = str(match_data.get("time") or "15:00")
    tw, th = get_text_size(draw, time_str, font_time)
    draw.text(((W - tw) // 2, vs_box_y + 92), time_str, fill=(241, 245, 249), font=font_time)

    # Status / Countdown Pill
    font_status = load_font("Arial-Bold.ttf", 14)
    countdown_str = match_data.get("countdown_str")
    series_raw = str(match_data.get("series") or "BO3").upper()

    if countdown_str and countdown_str != "Tugagan":
        pill_text = f"⏳ {countdown_str.upper()}  |  {series_raw}"
        pill_fill = (245, 158, 11)
        text_color = (15, 23, 42)
    else:
        status_raw = str(match_data.get("status") or "UPCOMING").upper()
        pill_text = f"UPCOMING  |  {series_raw}"
        pill_fill = (225, 29, 72)
        text_color = (255, 255, 255)

    pw, ph = get_text_size(draw, pill_text, font_status)
    px = (W - pw) // 2
    py = center_y + 44
    draw.rounded_rectangle([px - 14, py - 4, px + pw + 14, py + ph + 6], radius=8, fill=pill_fill)
    draw.text((px, py - 1), pill_text, fill=text_color, font=font_status)

    # 6. Modern Win-Rate Progress Bar & AI Predicted Score Capsule
    ai_pred = match_data.get("ai_prediction") or {}
    pred_score_a = match_data.get("predicted_score_a") or ai_pred.get("predicted_score_a")
    pred_score_b = match_data.get("predicted_score_b") or ai_pred.get("predicted_score_b")
    prob_a = int(ai_pred.get("prob_a", 50))
    prob_b = int(ai_pred.get("prob_b", 50))

    if pred_score_a is not None and pred_score_b is not None:
        pred_box_y = card_y + card_h - 110
        font_pred = load_font("Arial-Bold.ttf", 14)
        pred_txt = f"AI PREDICTED: {team_a[:9]} {pred_score_a} — {pred_score_b} {team_b[:9]}"
        pred_w, pred_h = get_text_size(draw, pred_txt, font_pred)

        capsule_w = pred_w + 32
        capsule_x = (W - capsule_w) // 2
        draw.rounded_rectangle([capsule_x, pred_box_y, capsule_x + capsule_w, pred_box_y + 26], radius=13, fill=(13, 26, 56), outline=(245, 158, 11), width=1)
        draw.text((capsule_x + 16, pred_box_y + 4), pred_txt, fill=(250, 204, 21), font=font_pred)

        bar_y = pred_box_y + 34
        bar_w = 420
        bar_h = 10
        bar_x = (W - bar_w) // 2

        draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=5, fill=(18, 32, 64))
        fill_w = int(bar_w * (prob_a / 100.0))
        if fill_w > 0:
            draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=5, fill=(234, 179, 8))
        if fill_w < bar_w:
            draw.rounded_rectangle([bar_x + fill_w, bar_y, bar_x + bar_w, bar_y + bar_h], radius=5, fill=(225, 29, 72))

        font_percent = load_font("Arial-Bold.ttf", 12)
        draw.text((bar_x - 38, bar_y - 2), f"{prob_a}%", fill=(250, 204, 21), font=font_percent)
        draw.text((bar_x + bar_w + 8, bar_y - 2), f"{prob_b}%", fill=(244, 63, 94), font=font_percent)
    else:
        # Date & format banner fallback
        date_box_y = card_y + card_h - 90
        font_date = load_font("Arial-Bold.ttf", 16)
        match_date_str = str(match_data.get("date_display") or match_data.get("date") or "TODAY")
        dw, dh = get_text_size(draw, match_date_str, font_date)
        draw.text(((W - dw) // 2, date_box_y), match_date_str, fill=(148, 163, 184), font=font_date)

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

