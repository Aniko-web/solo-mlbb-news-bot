import os
import io
import re
import urllib.request
from typing import Dict, Any, List, Optional, Union
from PIL import Image, ImageDraw, ImageFont

from app.utils.logger import logger
from app.media.templates.common import (
    load_font,
    FONT_ARIAL_BOLD,
    FONT_ARIAL_BLACK,
    FONT_IMPACT
)

# Paths to assets
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
HERO_CACHE_DIR = os.path.join(BASE_DIR, "assets", "heroes", "cache")
LOGOS_DIR = os.path.join(BASE_DIR, "assets", "logos")
MLBB_LOGO_PATH = os.path.join(LOGOS_DIR, "mlbb_logo.png")
MLBB_CREST_PATH = os.path.join(LOGOS_DIR, "mlbb_crest.png")
MUROD_LOGO_PATH = os.path.join(LOGOS_DIR, "murod_aliev_logo.png")
MUROD_ICON_PATH = os.path.join(LOGOS_DIR, "murod_aliev_icon.png")

os.makedirs(HERO_CACHE_DIR, exist_ok=True)


def _draw_blue_purple_splash(target: Image.Image, is_top_right: bool = True):
    """
    Render dynamic esports brush stroke accents in top-right and bottom-left
    using premium Electric Blue and Vivid Purple (Ko'k va Siyohrang) theme.
    """
    splash = Image.new("RGBA", (450, 280), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(splash)

    neon_purple = (147, 51, 234, 240)      # Vivid Purple / Violet
    deep_purple = (88, 28, 135, 210)       # Dark Violet
    electric_blue = (37, 99, 235, 240)     # Royal Blue
    cyan_glow = (56, 189, 248, 230)        # Bright Electric Cyan
    white = (255, 255, 255, 220)

    if is_top_right:
        sdraw.polygon([(60, 0), (450, 0), (450, 200), (290, 110), (160, 30)], fill=deep_purple)
        sdraw.polygon([(110, 0), (450, 0), (450, 150), (260, 70), (180, 15)], fill=neon_purple)
        sdraw.polygon([(180, 0), (450, 0), (450, 90), (300, 35)], fill=electric_blue)
        sdraw.polygon([(250, 0), (450, 0), (450, 50), (360, 15)], fill=cyan_glow)
        sdraw.line([(30, 0), (430, 230)], fill=neon_purple, width=14)
        sdraw.line([(80, 0), (450, 190)], fill=cyan_glow, width=7)
        sdraw.line([(140, 0), (450, 140)], fill=white, width=4)
        sdraw.ellipse([(140, 50), (165, 75)], fill=electric_blue)
        sdraw.ellipse([(220, 90), (238, 108)], fill=cyan_glow)
        target.paste(splash, (target.width - 450, 0), mask=splash)
    else:
        sdraw.polygon([(0, 80), (0, 280), (360, 280), (170, 170), (40, 110)], fill=deep_purple)
        sdraw.polygon([(0, 110), (0, 280), (300, 280), (140, 190), (60, 130)], fill=neon_purple)
        sdraw.polygon([(0, 160), (0, 280), (230, 280), (90, 220)], fill=electric_blue)
        sdraw.polygon([(0, 210), (0, 280), (160, 280), (60, 245)], fill=cyan_glow)
        sdraw.line([(0, 50), (370, 280)], fill=neon_purple, width=14)
        sdraw.line([(0, 80), (320, 280)], fill=cyan_glow, width=7)
        sdraw.line([(0, 130), (260, 280)], fill=white, width=4)
        sdraw.ellipse([(220, 200), (245, 225)], fill=electric_blue)
        target.paste(splash, (0, target.height - 280), mask=splash)


def _draw_badge_icon(draw_obj: ImageDraw.ImageDraw, cx: int, cy: int, category: str):
    """Draw circular category icon with sharp geometric vectors."""
    r = 20
    if category == "BUFF":
        color = (16, 185, 129)
        draw_obj.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
        draw_obj.polygon(
            [(cx, cy - 11), (cx - 8, cy - 1), (cx - 3, cy - 1), (cx - 3, cy + 10),
             (cx + 3, cy + 10), (cx + 3, cy - 1), (cx + 8, cy - 1)],
            fill=(255, 255, 255)
        )
    elif category == "NERF":
        color = (239, 68, 68)
        draw_obj.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
        draw_obj.polygon(
            [(cx, cy + 11), (cx - 8, cy + 1), (cx - 3, cy + 1), (cx - 3, cy - 10),
             (cx + 3, cy - 10), (cx + 3, cy + 1), (cx + 8, cy + 1)],
            fill=(255, 255, 255)
        )
    elif category == "ADJUSTMENT":
        color = (245, 158, 11)
        draw_obj.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
        draw_obj.arc((cx - 10, cy - 10, cx + 10, cy + 10), start=30, end=300, fill=(255, 255, 255), width=3)
        draw_obj.polygon([(cx + 6, cy - 12), (cx + 12, cy - 6), (cx + 4, cy - 4)], fill=(255, 255, 255))
    elif category == "REVAMP":
        color = (147, 51, 234)
        draw_obj.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
        draw_obj.line([(cx - 7, cy + 7), (cx + 5, cy - 5)], fill=(255, 255, 255), width=3)
        draw_obj.ellipse([(cx + 2, cy - 9), (cx + 9, cy - 2)], outline=(255, 255, 255), width=3)


def _render_avatar(name: str, avatar_url: Optional[str], size: int, ring_color: tuple) -> Image.Image:
    """Render circular hero portrait with 3px category-colored ring."""
    res = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    clean_name = re.sub(r"[^a-zA-Z0-9_-]", "", name.lower())
    cache_file = os.path.join(HERO_CACHE_DIR, f"{clean_name}.png")

    raw_bytes = None
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "rb") as f:
                raw_bytes = f.read()
        except Exception:
            pass

    if not raw_bytes and avatar_url:
        try:
            req = urllib.request.Request(avatar_url, headers={"User-Agent": "Mozilla/5.0"})
            raw_bytes = urllib.request.urlopen(req, timeout=3).read()
            # Save to disk cache
            with open(cache_file, "wb") as f:
                f.write(raw_bytes)
        except Exception:
            pass

    if raw_bytes:
        try:
            src_img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
        except Exception:
            src_img = None
    else:
        src_img = None

    if not src_img:
        # Fallback initial circle
        src_img = Image.new("RGBA", (size, size), (25, 32, 44, 255))
        sdraw = ImageDraw.Draw(src_img)
        sdraw.ellipse((4, 4, size - 4, size - 4), fill=(35, 45, 60))
        fallback_font = load_font(FONT_ARIAL_BLACK, int(size * 0.4))
        initial = name[:1].upper() if name else "?"
        bbox = sdraw.textbbox((0, 0), initial, font=fallback_font)
        iw = bbox[2] - bbox[0]
        ih = bbox[3] - bbox[1]
        sdraw.text(((size - iw) // 2, (size - ih) // 2 - 2), initial, fill=(200, 215, 230), font=fallback_font)

    # Circular mask
    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.ellipse((2, 2, size - 2, size - 2), fill=255)
    res.paste(src_img, (0, 0), mask=mask)

    # 3px colored ring border
    rdraw = ImageDraw.Draw(res)
    for i in range(3):
        rdraw.ellipse((i, i, size - 1 - i, size - 1 - i), outline=ring_color)

    return res


def render_patch_recap(patch_data: Dict[str, Any]) -> bytes:
    """
    Render professional MLBB Patch Notes Recap Infographic (Blue & Purple theme with Official MLBB logo).
    Features:
    - Official Mobile Legends: Bang Bang logo & flaming crest
    - Server badge (ORIGINAL SERVER / ADVANCED SERVER)
    - Patch Version subtitle in electric cyan
    - Categorized hero sections (BUFFS, NERFS, ADJUSTMENTS, REVAMP)
    - High-res circular hero avatars with colored rings
    - Dynamic Electric Blue & Vivid Purple energetic brush corner splashes
    - Official MLBB logo watermark in footer
    """
    server = str(patch_data.get("server", "ORIGINAL SERVER")).upper()
    version = str(patch_data.get("version", "2.2.16"))
    subtitle = f"PATCH NOTES {version} RECAP"

    # Normalize hero list dicts: [{"name": "...", "avatar": "..."}]
    def extract_list(key: str) -> List[Dict[str, Optional[str]]]:
        raw = patch_data.get(key, [])
        normalized = []
        for item in raw:
            if isinstance(item, str):
                normalized.append({"name": item, "avatar": None})
            elif isinstance(item, dict):
                normalized.append({
                    "name": item.get("name", "Unknown"),
                    "avatar": item.get("avatar") or item.get("image_url")
                })
        return normalized

    buffs = extract_list("buffs") or extract_list("BUFF")
    nerfs = extract_list("nerfs") or extract_list("NERF")
    adjustments = extract_list("adjustments") or extract_list("ADJUSTMENT")
    revamps = extract_list("revamps") or extract_list("REVAMP")

    # Calculate dynamic canvas height based on actual changes present
    has_buffs = len(buffs) > 0
    has_nerfs = len(nerfs) > 0
    has_adj = len(adjustments) > 0
    has_rev = len(revamps) > 0
    has_two_adj_rows = len(adjustments) > 5

    num_sections = sum([has_buffs, has_nerfs, (has_adj or has_rev)])
    if num_sections == 0:
        canvas_h = 600
    elif has_two_adj_rows:
        canvas_h = 960
    elif num_sections >= 3:
        canvas_h = 840
    elif num_sections == 2:
        canvas_h = 680
    else:
        canvas_h = 560
    canvas_w = 1080

    image = Image.new("RGB", (canvas_w, canvas_h), (8, 12, 22))
    draw = ImageDraw.Draw(image)

    # Dynamic Blue & Purple brush strokes in corners
    _draw_blue_purple_splash(image, is_top_right=True)
    _draw_blue_purple_splash(image, is_top_right=False)

    # Fonts
    font_title = load_font(FONT_ARIAL_BLACK, 34)
    font_subtitle = load_font(FONT_ARIAL_BOLD, 19)
    font_cat = load_font(FONT_ARIAL_BLACK, 24)
    font_name = load_font(FONT_ARIAL_BOLD, 13)

    # Header with Official MLBB Logo (Clean unified layout without extra M crest)
    hx, hy = 65, 42
    tx = hx
    if os.path.exists(MLBB_LOGO_PATH):
        try:
            logo_img = Image.open(MLBB_LOGO_PATH).convert("RGBA")
            l_h = 56
            l_w = int(logo_img.width * (l_h / logo_img.height))
            logo_scaled = logo_img.resize((l_w, l_h), Image.Resampling.LANCZOS)
            image.paste(logo_scaled, (hx, hy), mask=logo_scaled)
            tx = hx + l_w + 24
            # Subtle vertical accent divider line
            draw.line([(tx - 12, hy - 4), (tx - 12, hy + 62)], fill=(40, 65, 95), width=2)
        except Exception as e:
            logger.warning(f"Failed to paste MLBB logo: {e}")
            tx = hx

    draw.text((tx, hy), server, fill=(255, 255, 255), font=font_title)
    draw.text((tx, hy + 40), subtitle, fill=(56, 189, 248), font=font_subtitle)

    # Murod Aliev Brand Logo in Top-Right
    if os.path.exists(MUROD_LOGO_PATH):
        try:
            murod_img = Image.open(MUROD_LOGO_PATH).convert("RGBA")
            mh = 38
            mw = int(murod_img.width * (mh / murod_img.height))
            murod_scaled = murod_img.resize((mw, mh), Image.Resampling.LANCZOS)
            image.paste(murod_scaled, (canvas_w - mw - 70, 50), mask=murod_scaled)
        except Exception as e:
            logger.warning(f"Failed to paste Murod Aliev logo: {e}")

    avatar_size = 84
    sy = 150

    # 1. BUFFS Section (Only rendered if heroes exist)
    if has_buffs:
        _draw_badge_icon(draw, 85, sy + 18, "BUFF")
        draw.text((120, sy + 3), "BUFFS", fill=(255, 255, 255), font=font_cat)

        row_y = sy + 48
        col_w_buff = (canvas_w - 130) // max(min(len(buffs), 7), 1)
        for i, h in enumerate(buffs[:7]):
            av = _render_avatar(h["name"], h.get("avatar"), avatar_size, (16, 185, 129))
            cx = 65 + i * col_w_buff + (col_w_buff - avatar_size) // 2
            image.paste(av, (cx, row_y), mask=av)
            upper_name = h["name"].upper()
            bbox = draw.textbbox((0, 0), upper_name, font=font_name)
            nw = bbox[2] - bbox[0]
            draw.text((cx + (avatar_size - nw) // 2, row_y + 90), upper_name, fill=(240, 245, 255), font=font_name)
        sy = row_y + 128

    # 2. NERFS Section (Only rendered if heroes exist)
    if has_nerfs:
        _draw_badge_icon(draw, 85, sy + 18, "NERF")
        draw.text((120, sy + 3), "NERFS", fill=(255, 255, 255), font=font_cat)

        row_y = sy + 48
        col_w_nerf = (canvas_w - 130) // max(min(len(nerfs), 7), 1)
        for i, h in enumerate(nerfs[:7]):
            av = _render_avatar(h["name"], h.get("avatar"), avatar_size, (239, 68, 68))
            cx = 65 + i * col_w_nerf + (col_w_nerf - avatar_size) // 2
            image.paste(av, (cx, row_y), mask=av)
            upper_name = h["name"].upper()
            bbox = draw.textbbox((0, 0), upper_name, font=font_name)
            nw = bbox[2] - bbox[0]
            draw.text((cx + (avatar_size - nw) // 2, row_y + 90), upper_name, fill=(240, 245, 255), font=font_name)
        sy = row_y + 128

    # 3. ADJUSTMENTS & REVAMP Section (Only rendered if heroes exist)
    if has_adj or has_rev:
        row_y = sy + 48
        if has_adj and has_rev:
            _draw_badge_icon(draw, 85, sy + 18, "ADJUSTMENT")
            draw.text((120, sy + 3), "ADJUSTMENTS", fill=(255, 255, 255), font=font_cat)

            rx = 690
            _draw_badge_icon(draw, rx + 20, sy + 18, "REVAMP")
            draw.text((rx + 55, sy + 3), "REVAMP", fill=(255, 255, 255), font=font_cat)

            # Revamps (Right side)
            col_w_revamp = 110
            for i, h in enumerate(revamps[:3]):
                av = _render_avatar(h["name"], h.get("avatar"), avatar_size, (147, 51, 234))
                cx = rx + i * col_w_revamp + 10
                image.paste(av, (cx, row_y), mask=av)
                upper_name = h["name"].upper()
                bbox = draw.textbbox((0, 0), upper_name, font=font_name)
                nw = bbox[2] - bbox[0]
                draw.text((cx + (avatar_size - nw) // 2, row_y + 90), upper_name, fill=(240, 245, 255), font=font_name)

            # Adjustments Row 1 (Left 5 heroes)
            col_w_adj = 115
            for i, h in enumerate(adjustments[:5]):
                av = _render_avatar(h["name"], h.get("avatar"), avatar_size, (245, 158, 11))
                cx = 65 + i * col_w_adj
                image.paste(av, (cx, row_y), mask=av)
                upper_name = h["name"].upper()
                bbox = draw.textbbox((0, 0), upper_name, font=font_name)
                nw = bbox[2] - bbox[0]
                draw.text((cx + (avatar_size - nw) // 2, row_y + 90), upper_name, fill=(240, 245, 255), font=font_name)

            # Adjustments Row 2 (Remaining heroes)
            if has_two_adj_rows:
                row2_y = row_y + 118
                for i, h in enumerate(adjustments[5:10]):
                    av = _render_avatar(h["name"], h.get("avatar"), avatar_size, (245, 158, 11))
                    cx = 65 + i * col_w_adj
                    image.paste(av, (cx, row2_y), mask=av)
                    upper_name = h["name"].upper()
                    bbox = draw.textbbox((0, 0), upper_name, font=font_name)
                    nw = bbox[2] - bbox[0]
                    draw.text((cx + (avatar_size - nw) // 2, row2_y + 90), upper_name, fill=(240, 245, 255), font=font_name)
        elif has_adj:
            _draw_badge_icon(draw, 85, sy + 18, "ADJUSTMENT")
            draw.text((120, sy + 3), "ADJUSTMENTS", fill=(255, 255, 255), font=font_cat)
            col_w_adj = (canvas_w - 130) // max(min(len(adjustments), 7), 1)
            for i, h in enumerate(adjustments[:7]):
                av = _render_avatar(h["name"], h.get("avatar"), avatar_size, (245, 158, 11))
                cx = 65 + i * col_w_adj + (col_w_adj - avatar_size) // 2
                image.paste(av, (cx, row_y), mask=av)
                upper_name = h["name"].upper()
                bbox = draw.textbbox((0, 0), upper_name, font=font_name)
                nw = bbox[2] - bbox[0]
                draw.text((cx + (avatar_size - nw) // 2, row_y + 90), upper_name, fill=(240, 245, 255), font=font_name)
        elif has_rev:
            _draw_badge_icon(draw, 85, sy + 18, "REVAMP")
            draw.text((120, sy + 3), "REVAMP", fill=(255, 255, 255), font=font_cat)
            col_w_rev = (canvas_w - 130) // max(min(len(revamps), 7), 1)
            for i, h in enumerate(revamps[:7]):
                av = _render_avatar(h["name"], h.get("avatar"), avatar_size, (147, 51, 234))
                cx = 65 + i * col_w_rev + (col_w_rev - avatar_size) // 2
                image.paste(av, (cx, row_y), mask=av)
                upper_name = h["name"].upper()
                bbox = draw.textbbox((0, 0), upper_name, font=font_name)
                nw = bbox[2] - bbox[0]
                draw.text((cx + (avatar_size - nw) // 2, row_y + 90), upper_name, fill=(240, 245, 255), font=font_name)

    # 4. If no hero changes, render a clean official system update card
    if num_sections == 0:
        card_rect = [65, 180, canvas_w - 65, canvas_h - 100]
        draw.rounded_rectangle(card_rect, radius=16, fill=(16, 24, 38), outline=(37, 99, 235), width=2)
        font_empty_title = load_font(FONT_ARIAL_BLACK, 28)
        font_empty_sub = load_font(FONT_ARIAL_BOLD, 18)
        draw.text((100, 230), "TIZIM VA O'YIN MUVOZANATI YANGILANISHI", fill=(56, 189, 248), font=font_empty_title)
        draw.text((100, 290), "Ushbu versiyada o‘yin jarayoni, asbob-uskunalar (items) va jang maydoni", fill=(220, 230, 245), font=font_empty_sub)
        draw.text((100, 325), "mexanikasi optimallashtirildi hamda tarmoq barqarorligi yaxshilandi.", fill=(220, 230, 245), font=font_empty_sub)

    # Bottom Footer with MLBB Logo & Watermark
    if os.path.exists(MLBB_LOGO_PATH):
        try:
            logo_img = Image.open(MLBB_LOGO_PATH).convert("RGBA")
            b_h = 32
            b_w = int(logo_img.width * (b_h / logo_img.height))
            logo_footer = logo_img.resize((b_w, b_h), Image.Resampling.LANCZOS)
            image.paste(logo_footer, (canvas_w - b_w - 60, canvas_h - 48), mask=logo_footer)
        except Exception:
            pass

    fx = 65
    if os.path.exists(MUROD_ICON_PATH):
        try:
            icon_img = Image.open(MUROD_ICON_PATH).convert("RGBA")
            ih = 26
            iw = int(icon_img.width * (ih / icon_img.height))
            icon_scaled = icon_img.resize((iw, ih), Image.Resampling.LANCZOS)
            image.paste(icon_scaled, (fx, canvas_h - 43), mask=icon_scaled)
            fx += iw + 10
        except Exception:
            pass

    draw.text(
        (fx, canvas_h - 38),
        "MUROD ALIEV • MLBB RASMIY YANGILANISH RECAP",
        fill=(160, 190, 225),
        font=font_name
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
