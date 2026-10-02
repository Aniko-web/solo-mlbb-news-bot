import os
import math
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from app.media.templates.common import (
    load_font,
    get_text_size,
    load_team_logo,
    TEAM_IDENTITIES,
    draw_shared_brand_badge,
    draw_vector_star,
    image_to_png_bytes,
    LOGOS_DIR
)


def parse_card_time(raw_time: str) -> Tuple[str, str]:
    """
    Parses various match time formats into (primary_time, secondary_regional_time).
    Examples:
      '13:00 (UZ) / 15:00 (WIB)' -> ('13:00', '15:00 WIB')
      '14:00 (UZ) / 17:00 (PHT)' -> ('14:00', '17:00 PHT')
      '13:00 (Toshkent)' -> ('13:00', 'TOSHKENT')
      '15:00 WIB' -> ('15:00', 'WIB')
      '15:00' -> ('15:00', '')
    """
    raw = (raw_time or "15:00").strip()
    if " / " in raw:
        parts = raw.split(" / ")
        primary = parts[0].replace("(UZ)", "").replace("(uz)", "").replace("UZ", "").strip()
        secondary = parts[1].replace("(", "").replace(")", "").strip()
        return primary, secondary

    for token in ["(Toshkent)", "(TOSHKENT)", "(UZ)", "(uz)"]:
        if token in raw:
            return raw.replace(token, "").strip(), "TOSHKENT"

    if "WIB" in raw or "PHT" in raw:
        parts = raw.split()
        return parts[0], " ".join(parts[1:])

    return raw, ""


def get_team_color(team_name: str) -> tuple:
    upper = (team_name or "").upper()
    for key, (c, _) in sorted(TEAM_IDENTITIES.items(), key=lambda x: len(x[0]), reverse=True):
        if key in upper:
            # Safeguard contrast: ensure color is bright enough against dark background
            brightness = (c[0] * 299 + c[1] * 587 + c[2] * 114) / 1000
            if brightness < 110:
                factor = 145 / max(brightness, 1)
                return (min(255, int(c[0] * factor)), min(255, int(c[1] * factor)), min(255, int(c[2] * factor)))
            return c
    return (241, 245, 249)


def render_matchday_card(data: Dict[str, Any]) -> bytes:
    """
    Renders official 1200x675 Broadcast Matchday Schedule Graphic.
    Displays all matches scheduled for the day in a clean, high-impact multi-row layout,
    with custom team logos, times, VS emblems, and prominent 'MARKAZIY BAHS' (Match of the Day) highlighting.
    """
    W, H = 1200, 675
    league = str(data.get("league") or "MPL ID").upper()
    is_ph = "PH" in league

    # 1. Base Canvas & Dynamic Esports Stage Background
    im = Image.new("RGB", (W, H), color=(8, 10, 18))
    draw = ImageDraw.Draw(im)

    if is_ph:
        # Midnight navy & solar electric stadium gradient
        for y in range(H):
            ratio = y / H
            r = int(6 + ratio * 8)
            g = int(12 + ratio * 16)
            b = int(24 + ratio * 28)
            draw.line([(0, y), (W, y)], fill=(r, g, b))
    else:
        # Dark carbon & Indonesian crimson stadium gradient
        for y in range(H):
            ratio = y / H
            r = int(10 + ratio * 14)
            g = int(10 + ratio * 8)
            b = int(16 + ratio * 10)
            draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Ambient lighting & geometric chevrons
    bg_fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fx_draw = ImageDraw.Draw(bg_fx)

    accent_glow = (14, 165, 233) if is_ph else (220, 38, 38)
    gold_glow = (245, 158, 11)

    # Top-left and bottom-right glow
    for rad in range(300, 0, -15):
        alpha = int((1 - rad / 300) * 32)
        fx_draw.ellipse([80 - rad, 60 - rad, 80 + rad, 60 + rad], fill=(*accent_glow, alpha))
        fx_draw.ellipse([W - 100 - rad, H - 80 - rad, W - 100 + rad, H - 80 + rad], fill=(*gold_glow, alpha))

    # Angled stage light beams
    fx_draw.polygon([(-40, 0), (180, 0), (90, H), (-40, H)], fill=(*accent_glow, 12))
    fx_draw.polygon([(W - 140, 0), (W + 40, 0), (W + 40, H), (W - 60, H)], fill=(*gold_glow, 10))

    im.paste(bg_fx, (0, 0), bg_fx)
    draw = ImageDraw.Draw(im)

    # 2. Header Section
    font_league = load_font("Impact.ttf", 32)
    font_sub = load_font("Arial-Bold.ttf", 15)

    league_logo_file = "mpl_ph.png" if is_ph else "mpl_id.png"
    league_logo_path = os.path.join(LOGOS_DIR, league_logo_file)
    header_logo_w = 0

    if os.path.exists(league_logo_path):
        try:
            l_img = Image.open(league_logo_path).convert("RGBA")
            l_img.thumbnail((110, 68), Image.Resampling.LANCZOS)
            im.paste(l_img, (48, 20), l_img)
            header_logo_w = l_img.width + 16
        except Exception:
            pass

    header_x = 48 + header_logo_w
    league_title = "MPL PHILIPPINES" if is_ph else "MPL INDONESIA"
    draw.text((header_x, 22), league_title, fill=(255, 255, 255), font=font_league)

    date_display = str(data.get("date_display") or data.get("date") or "BUGUN").upper()
    season_text = str(data.get("season") or "SEASON 18").upper()
    subtitle_text = f"BUGUNGI O‘YINLAR DASTURI   •   {date_display}   •   {season_text}"
    draw.text((header_x, 58), subtitle_text, fill=(56, 189, 248) if is_ph else (239, 68, 68), font=font_sub)

    # Right branding
    draw_shared_brand_badge(im, W - 180, 32, theme="ph" if is_ph else "id")

    # Header separator rule
    draw.line([(48, 98), (W - 48, 98)], fill=(30, 41, 59), width=1)
    draw.line([(48, 98), (320, 98)], fill=accent_glow, width=3)

    # 3. Match Rows Construction
    matches: List[Dict[str, Any]] = data.get("matches", [])
    if not matches:
        matches = [
            {"team_a": "TEAM A", "team_b": "TEAM B", "time": "15:00", "series": "BO3", "is_motd": True}
        ]

    # Limit to at most 4 matches per card for optimal visual balance
    display_matches = matches[:4]
    n = len(display_matches)

    card_x = 48
    card_w = W - 96  # 1104 px

    if n == 1:
        row_h = 360
        gap = 0
        start_y = 160
        logo_size = (130, 130)
    elif n == 2:
        row_h = 210
        gap = 24
        start_y = 145
        logo_size = (96, 96)
    elif n == 3:
        row_h = 138
        gap = 16
        start_y = 130
        logo_size = (76, 76)
    else:  # n == 4
        row_h = 104
        gap = 12
        start_y = 120
        logo_size = (56, 56)

    font_match_num = load_font("Arial-Bold.ttf", 13 if n <= 2 else (11 if n == 3 else 10))
    font_time = load_font("Impact.ttf", 32 if n <= 2 else (26 if n == 3 else 20))
    font_sub_time = load_font("Arial-Bold.ttf", 12 if n <= 2 else (10 if n == 3 else 9))
    font_team = load_font("Arial-Bold.ttf", 24 if n <= 2 else (20 if n == 3 else 17))
    font_team_small = load_font("Arial-Bold.ttf", 20 if n <= 2 else (17 if n == 3 else 14))
    font_vs = load_font("Impact.ttf", 28 if n <= 2 else (22 if n == 3 else 18))
    font_bo3 = load_font("Arial-Bold.ttf", 12)
    font_motd = load_font("Arial-Bold.ttf", 12)

    sec_w = 156 if n <= 3 else 136
    x_div_left = card_x + sec_w
    x_div_right = card_x + card_w - sec_w
    center_x = (x_div_left + x_div_right) // 2  # exactly 600

    for i, match in enumerate(display_matches):
        ry = start_y + i * (row_h + gap)
        cy = ry + row_h // 2
        is_motd = bool(match.get("is_motd", False))
        team_a = str(match.get("team_a") or "TEAM A").upper()
        team_b = str(match.get("team_b") or "TEAM B").upper()
        raw_time = str(match.get("time") or "15:00")
        series = str(match.get("series") or "BO3").upper()
        status = str(match.get("status") or "UPCOMING").upper()

        primary_time, secondary_time = parse_card_time(raw_time)

        col_a = get_team_color(team_a)
        col_b = get_team_color(team_b)

        # Match Row Container
        if is_motd:
            draw.rounded_rectangle(
                [card_x - 2, ry - 2, card_x + card_w + 2, ry + row_h + 2],
                radius=14,
                fill=(245, 158, 11)
            )
            draw.rounded_rectangle(
                [card_x, ry, card_x + card_w, ry + row_h],
                radius=12,
                fill=(18, 20, 36)
            )
            motd_accent = Image.new("RGBA", (card_w, row_h), (0, 0, 0, 0))
            m_draw = ImageDraw.Draw(motd_accent)
            m_draw.ellipse([card_w // 2 - 140, -50, card_w // 2 + 140, row_h + 50], fill=(245, 158, 11, 24))
            im.paste(motd_accent, (card_x, ry), motd_accent)
            draw = ImageDraw.Draw(im)
        else:
            draw.rounded_rectangle(
                [card_x - 1, ry - 1, card_x + card_w + 1, ry + row_h + 1],
                radius=12,
                fill=(30, 41, 59)
            )
            draw.rounded_rectangle(
                [card_x, ry, card_x + card_w, ry + row_h],
                radius=11,
                fill=(13, 17, 28)
            )

        # Dividers
        draw.line([(x_div_left, ry + 12), (x_div_left, ry + row_h - 12)], fill=(40, 52, 75), width=1)
        draw.line([(x_div_right, ry + 12), (x_div_right, ry + row_h - 12)], fill=(40, 52, 75), width=1)

        # 4a. Left Badge: Match Number & Stacked Time
        m_num_str = f"O‘YIN #{i + 1}"
        mn_w, _ = get_text_size(draw, m_num_str, font_match_num)
        pt_w, _ = get_text_size(draw, primary_time, font_time)

        if secondary_time:
            st_w, _ = get_text_size(draw, secondary_time, font_sub_time)
            y_shift = 42 if n <= 2 else (30 if n == 3 else 23)
            draw.text((card_x + (sec_w - mn_w) // 2, cy - y_shift), m_num_str, fill=(148, 163, 184), font=font_match_num)
            draw.text((card_x + (sec_w - pt_w) // 2, cy - 14 if n <= 2 else (cy - 9 if n == 3 else cy - 7)), primary_time, fill=(255, 255, 255), font=font_time)
            sub_col = (56, 189, 248) if is_ph else (248, 113, 113)
            draw.text((card_x + (sec_w - st_w) // 2, cy + 24 if n <= 2 else (cy + 18 if n == 3 else cy + 14)), secondary_time, fill=sub_col, font=font_sub_time)
        else:
            draw.text((card_x + (sec_w - mn_w) // 2, cy - 20 if n <= 2 else cy - 14), m_num_str, fill=(148, 163, 184), font=font_match_num)
            draw.text((card_x + (sec_w - pt_w) // 2, cy + 2 if n <= 2 else cy), primary_time, fill=(255, 255, 255), font=font_time)

        # 4b. Center VS Emblem & Series Format
        vs_pill_w = 68 if n <= 3 else 56
        vs_pill_h = 34 if n <= 3 else 28
        vs_x = center_x - vs_pill_w // 2
        vs_y = cy - vs_pill_h // 2 - (6 if n <= 3 else 0)

        if is_motd:
            draw.rounded_rectangle(
                [vs_x, vs_y, vs_x + vs_pill_w, vs_y + vs_pill_h],
                radius=8,
                fill=(245, 158, 11)
            )
            vw, vh = get_text_size(draw, "VS", font_vs)
            draw.text((center_x - vw // 2, vs_y + (vs_pill_h - vh) // 2 - 1), "VS", fill=(15, 23, 42), font=font_vs)
        else:
            draw.rounded_rectangle(
                [vs_x, vs_y, vs_x + vs_pill_w, vs_y + vs_pill_h],
                radius=8,
                fill=(30, 41, 59)
            )
            vw, vh = get_text_size(draw, "VS", font_vs)
            draw.text((center_x - vw // 2, vs_y + (vs_pill_h - vh) // 2 - 1), "VS", fill=(241, 245, 249), font=font_vs)

        if n <= 3:
            bo3_w, _ = get_text_size(draw, series, font_bo3)
            draw.text((center_x - bo3_w // 2, vs_y + vs_pill_h + 3), series, fill=(100, 116, 139), font=font_bo3)

        # 4c. Team A (Left Side of VS): [Logo A] [Name A]
        team_a_area_w = vs_x - x_div_left
        logo_a = load_team_logo(team_a, max_size=logo_size)
        lw_a = logo_a.width if logo_a else logo_size[0]
        lh_a = logo_a.height if logo_a else logo_size[1]

        font_a = font_team
        ta_w, ta_h = get_text_size(draw, team_a[:16], font_a)
        if ta_w + 16 + lw_a > team_a_area_w - 20:
            font_a = font_team_small
            ta_w, ta_h = get_text_size(draw, team_a[:16], font_a)

        total_a_w = lw_a + 16 + ta_w
        pad_a = max(10, (team_a_area_w - total_a_w) // 2)
        logo_a_x = x_div_left + pad_a
        logo_a_y = cy - lh_a // 2
        if logo_a:
            im.paste(logo_a, (logo_a_x, logo_a_y), logo_a)

        name_a_x = logo_a_x + lw_a + 16
        name_a_y = cy - ta_h // 2
        draw.text((name_a_x, name_a_y), team_a[:16], fill=col_a, font=font_a)

        # 4d. Team B (Right Side of VS): [Name B] [Logo B]
        team_b_area_x = vs_x + vs_pill_w
        team_b_area_w = x_div_right - team_b_area_x
        logo_b = load_team_logo(team_b, max_size=logo_size)
        lw_b = logo_b.width if logo_b else logo_size[0]
        lh_b = logo_b.height if logo_b else logo_size[1]

        font_b = font_team
        tb_w, tb_h = get_text_size(draw, team_b[:16], font_b)
        if tb_w + 16 + lw_b > team_b_area_w - 20:
            font_b = font_team_small
            tb_w, tb_h = get_text_size(draw, team_b[:16], font_b)

        total_b_w = tb_w + 16 + lw_b
        pad_b = max(10, (team_b_area_w - total_b_w) // 2)
        name_b_x = team_b_area_x + pad_b
        name_b_y = cy - tb_h // 2
        draw.text((name_b_x, name_b_y), team_b[:16], fill=col_b, font=font_b)

        logo_b_x = name_b_x + tb_w + 16
        logo_b_y = cy - lh_b // 2
        if logo_b:
            im.paste(logo_b, (logo_b_x, logo_b_y), logo_b)

        # 4e. Right Status / Match of the Day Tag
        if is_motd:
            motd_badge_w = 120
            motd_badge_h = 28
            mb_x = x_div_right + (sec_w - motd_badge_w) // 2
            mb_y = cy - motd_badge_h // 2
            draw.rounded_rectangle([mb_x, mb_y, mb_x + motd_badge_w, mb_y + motd_badge_h], radius=6, fill=(245, 158, 11))
            draw_vector_star(draw, mb_x + 22, cy, r_outer=6.0, r_inner=2.8, fill=(15, 23, 42))
            draw.text((mb_x + 34, mb_y + (motd_badge_h - 11) // 2 - 1), "MARKAZIY", fill=(15, 23, 42), font=font_motd)
        else:
            status_text = "BO3" if n >= 4 else ("LIVE" if status == "LIVE" else ("FINAL" if status in ["FINISHED", "FINAL"] else "KUTILMOQDA"))
            badge_color = (239, 68, 68) if status_text == "LIVE" else ((100, 116, 139) if status_text == "FINAL" else (14, 165, 233))
            motd_badge_w = 112
            motd_badge_h = 26
            mb_x = x_div_right + (sec_w - motd_badge_w) // 2
            mb_y = cy - motd_badge_h // 2
            draw.rounded_rectangle([mb_x, mb_y, mb_x + motd_badge_w, mb_y + motd_badge_h], radius=6, outline=badge_color, fill=(15, 23, 42), width=1)
            sw, sh = get_text_size(draw, status_text, font_motd)
            draw.text((mb_x + (motd_badge_w - sw) // 2, mb_y + (motd_badge_h - sh) // 2 - 1), status_text, fill=badge_color, font=font_motd)

    # 5. Footer Line (clean text without unsupported emoji glyphs)
    footer_font = load_font("Arial-Bold.ttf", 13)
    footer_text = "Jonli translatsiyalar, tahlillar va tezkor natijalar   •   Telegram: @murodalievgg"
    fw, _ = get_text_size(draw, footer_text, footer_font)
    draw.text(((W - fw) // 2, H - 32), footer_text, fill=(100, 116, 139), font=footer_font)

    return image_to_png_bytes(im)
