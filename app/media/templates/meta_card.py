import os
import re
import urllib.request
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from app.media.templates.common import (
    load_font,
    get_text_size,
    load_team_logo,
    draw_shared_brand_badge,
    image_to_png_bytes,
    ASSETS_DIR,
    LOGOS_DIR
)

HEROES_PORTRAITS_DIR = os.path.join(ASSETS_DIR, "heroes", "portraits")
HEROES_CACHE_DIR = os.path.join(ASSETS_DIR, "heroes", "cache")
HEROES_ROOT_DIR = os.path.join(ASSETS_DIR, "heroes")

# Known alias map for hero naming variations between mlbb.io and local assets
HERO_ALIAS_MAP = {
    "helcurt": "helcurd",
    "helcurd": "helcurt",
    "minsitthar": "minsitthar",
    "bane": "bane",
    "yisunshin": "yisun-shin",
    "yisun-shin": "yisunshin",
    "yuzhong": "yu-zhong",
    "yu-zhong": "yuzhong",
    "luoyi": "louyi",
    "louyi": "luoyi",
    "chang_e": "change",
    "change": "change",
    "x_borg": "xborg",
    "xborg": "x-borg",
    "dyrroth": "diroth",
    "diroth": "dyrroth",
}


def normalize_hero_name(name: str) -> List[str]:
    """Generates all possible filename variants for a hero name."""
    raw = name.strip().lower()
    clean_strict = re.sub(r"[^a-z0-9]", "", raw)
    clean_snake = re.sub(r"[\s\-]+", "_", raw)
    clean_kebab = re.sub(r"[\s\_]+", "-", raw)
    clean_no_punct = re.sub(r"['\.]", "", raw)

    variants = [
        clean_strict,
        clean_snake,
        clean_kebab,
        re.sub(r"[^a-z0-9]", "", clean_no_punct),
        raw
    ]
    if clean_strict in HERO_ALIAS_MAP:
        variants.append(HERO_ALIAS_MAP[clean_strict])
    if raw in HERO_ALIAS_MAP:
        variants.append(HERO_ALIAS_MAP[raw])

    seen = set()
    res = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            res.append(v)
    return res


def load_and_enhance_hero_avatar(
    hero_name: str,
    img_src: Optional[str] = None,
    target_size: int = 50,
    border_color: tuple = (16, 185, 129)
) -> Optional[Image.Image]:
    """
    Loads hero portrait image from local assets (portraits or cache),
    or downloads high-res image from mlbb.io youngjoygame CDN if missing.
    Applies sharpness and contrast enhancements, anti-aliased circular cropping,
    and a crisp outer neon glow ring for broadcast clarity (tiniqlik).
    """
    variants = normalize_hero_name(hero_name)
    found_path = None

    search_dirs = [HEROES_PORTRAITS_DIR, HEROES_CACHE_DIR, HEROES_ROOT_DIR]
    for v in variants:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            for d in search_dirs:
                p = os.path.join(d, f"{v}{ext}")
                if os.path.exists(p):
                    found_path = p
                    break
            if found_path:
                break
        if found_path:
            break

    # If not found locally and img_src is available, download and cache
    if not found_path and img_src:
        try:
            os.makedirs(HEROES_CACHE_DIR, exist_ok=True)
            clean = re.sub(r"[^a-z0-9]", "", hero_name.lower())
            cache_file = os.path.join(HEROES_CACHE_DIR, f"{clean}.png")
            req = urllib.request.Request(
                img_src,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                with open(cache_file, "wb") as f:
                    f.write(data)
            found_path = cache_file
        except Exception:
            pass

    if not found_path or not os.path.exists(found_path):
        return None

    try:
        raw_img = Image.open(found_path).convert("RGBA")

        # 1. Enhance clarity (Sharpness + Contrast + Saturation) for high definition
        sharp = ImageEnhance.Sharpness(raw_img).enhance(1.4)
        contrast = ImageEnhance.Contrast(sharp).enhance(1.08)
        color = ImageEnhance.Color(contrast).enhance(1.05)

        # 2. Resize with high-quality LANCZOS resampling (work at 2x resolution for AA)
        upscale_size = target_size * 2
        thumb = color.resize((upscale_size, upscale_size), Image.Resampling.LANCZOS)

        # 3. Supersampled Circular Mask (anti-aliasing)
        mask = Image.new("L", (upscale_size, upscale_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, upscale_size - 1, upscale_size - 1], fill=255)

        # Circular cropped avatar at 2x
        avatar_2x = Image.new("RGBA", (upscale_size, upscale_size), (0, 0, 0, 0))
        avatar_2x.paste(thumb, (0, 0), mask)

        # 4. Draw outer border ring directly at 2x for razor-sharp stroke
        ring_draw = ImageDraw.Draw(avatar_2x)
        ring_color = border_color + (240,) if len(border_color) == 3 else border_color
        ring_draw.ellipse([1, 1, upscale_size - 2, upscale_size - 2], outline=ring_color, width=4)

        # 5. Downsample to target_size using LANCZOS for super crisp finish
        final_avatar = avatar_2x.resize((target_size, target_size), Image.Resampling.LANCZOS)
        return final_avatar
    except Exception:
        return None


def render_meta_tier_card(data: Dict[str, List[Dict[str, Any]]]) -> bytes:
    """
    Renders high-impact 1200x675 broadcast infographic card for MLBB Meta Tier List:
    Columns:
      1. Strong & Spammed (Gold / Emerald)
      2. Traps to Avoid (Crimson / Red)
      3. Hidden Gems (Electric Violet / Cyan)
    """
    W, H = 1200, 675
    im = Image.new("RGB", (W, H), color=(10, 12, 18))
    draw = ImageDraw.Draw(im)

    # 1. Dark background gradient
    for y in range(H):
        ratio = y / H
        r = int(10 + ratio * 8)
        g = int(12 + ratio * 8)
        b = int(18 + ratio * 14)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 2. Subtle ambient glows
    bg_glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(bg_glow)

    # Left emerald glow
    for rad in range(250, 0, -15):
        alpha = int((1 - rad / 250) * 30)
        g_draw.ellipse([200 - rad, 350 - rad, 200 + rad, 350 + rad], fill=(16, 185, 129, alpha))

    # Center red glow
    for rad in range(220, 0, -15):
        alpha = int((1 - rad / 220) * 25)
        g_draw.ellipse([600 - rad, 380 - rad, 600 + rad, 380 + rad], fill=(239, 68, 68, alpha))

    # Right violet glow
    for rad in range(250, 0, -15):
        alpha = int((1 - rad / 250) * 35)
        g_draw.ellipse([1000 - rad, 350 - rad, 1000 + rad, 350 + rad], fill=(168, 85, 247, alpha))

    im.paste(bg_glow, (0, 0), bg_glow)
    draw = ImageDraw.Draw(im)

    # 3. Top Header
    font_title = load_font("Impact.ttf", 34)
    font_sub = load_font("Arial-Bold.ttf", 15)

    draw.text((50, 26), "MLBB HERO META TIER LIST", fill=(255, 255, 255), font=font_title)
    draw.text((50, 66), "LIVE META INSIGHTS  •  SOLO RANK WINRATE & BAN ANALYSIS", fill=(56, 189, 248), font=font_sub)

    draw_shared_brand_badge(im, W - 180, 32, theme="id")

    # Header divider
    draw.line([(50, 102), (W - 50, 102)], fill=(35, 42, 58), width=2)
    draw.line([(50, 102), (380, 102)], fill=(56, 189, 248), width=3)

    # 4. Three Cards Columns Layout
    col_w = 345
    col_gap = 25
    start_x = 55
    card_y = 125
    card_h = 475

    strong_heroes = data.get("strong_spammed", [])[:5]
    trap_heroes = data.get("traps", [])[:5]
    gem_heroes = data.get("hidden_gems", [])[:5]

    columns_config = [
        {
            "title": "🔥 STRONG & SPAMMED",
            "sub": "Metani yondirayotgan OP qahramonlar",
            "border": (16, 185, 129),
            "header_bg": (15, 35, 28),
            "text_color": (52, 211, 153),
            "heroes": strong_heroes,
            "badge_color": (16, 185, 129),
            "badge_tag": "OP / SS"
        },
        {
            "title": "⚠️ TRAPS TO AVOID",
            "sub": "Tuzoq piklar — aslo olmang!",
            "border": (239, 68, 68),
            "header_bg": (38, 18, 22),
            "text_color": (248, 113, 113),
            "heroes": trap_heroes,
            "badge_color": (239, 68, 68),
            "badge_tag": "AVOID / D"
        },
        {
            "title": "💎 HIDDEN GEMS",
            "sub": "Kam ban, lekin dahshat yutadi",
            "border": (168, 85, 247),
            "header_bg": (32, 18, 48),
            "text_color": (192, 132, 252),
            "heroes": gem_heroes,
            "badge_color": (168, 85, 247),
            "badge_tag": "SECRET GEM"
        }
    ]

    font_col_title = load_font("Arial-Bold.ttf", 18)
    font_col_sub = load_font("Arial.ttf", 12)
    font_hero_name = load_font("Arial-Bold.ttf", 16)
    font_hero_info = load_font("Arial.ttf", 12)
    font_tag = load_font("Arial-Bold.ttf", 11)

    for i, col in enumerate(columns_config):
        cx = start_x + i * (col_w + col_gap)

        # Card container box
        draw.rounded_rectangle(
            [cx, card_y, cx + col_w, card_y + card_h],
            radius=12,
            fill=(14, 18, 28),
            outline=col["border"],
            width=2
        )

        # Header bar of card
        draw.rounded_rectangle(
            [cx + 1, card_y + 1, cx + col_w - 1, card_y + 60],
            radius=10,
            fill=col["header_bg"]
        )

        draw.text((cx + 16, card_y + 12), col["title"], fill=col["text_color"], font=font_col_title)
        draw.text((cx + 16, card_y + 36), col["sub"], fill=(156, 163, 175), font=font_col_sub)

        # Draw list of heroes
        hero_start_y = card_y + 75
        item_h = 75

        for j, h in enumerate(col["heroes"]):
            hy = hero_start_y + j * item_h

            # Sub-item container
            draw.rounded_rectangle(
                [cx + 12, hy, cx + col_w - 12, hy + item_h - 10],
                radius=8,
                fill=(20, 26, 40),
                outline=(35, 45, 65),
                width=1
            )

            # Hero Avatar (Load local assets / cache / mlbb.io CDN with high clarity)
            hero_name = h.get("hero_name", "Hero")
            img_src = h.get("img_src")
            ava = load_and_enhance_hero_avatar(
                hero_name=hero_name,
                img_src=img_src,
                target_size=50,
                border_color=col["border"]
            )

            if ava:
                im.paste(ava, (cx + 20, hy + 7), ava)
            else:
                # Monogram circle fallback if image unavailable
                draw.ellipse([cx + 20, hy + 7, cx + 70, hy + 57], fill=col["header_bg"], outline=col["border"], width=2)
                initial = hero_name[:2].upper()
                font_init = load_font("Impact.ttf", 18)
                iw, ih = get_text_size(draw, initial, font_init)
                draw.text((cx + 45 - iw // 2, hy + 32 - ih // 2), initial, fill=(245, 245, 245), font=font_init)

            # Hero Name & Info
            draw.text((cx + 78, hy + 12), hero_name[:16], fill=(245, 245, 250), font=font_hero_name)

            role_str = h.get("lane", []) or h.get("role", [])
            if isinstance(role_str, list):
                role_text = role_str[0] if role_str else "All Lanes"
            else:
                role_text = str(role_str)

            ban_val = h.get("ban_rate", 0)
            score_val = h.get("score", 0)
            if "STRONG" in col["title"]:
                info_line = f"{role_text} • Ban: {ban_val:.1f}%"
            elif "TRAP" in col["title"]:
                info_line = f"{role_text} • Zaif meta"
            else:
                info_line = f"{role_text} • Ban: {ban_val:.1f}%"

            draw.text((cx + 78, hy + 35), info_line, fill=(148, 163, 184), font=font_hero_info)

            # Tier Pill
            tier_val = h.get("tier", "S")
            font_pill = load_font("Arial-Bold.ttf", 11)
            pill_text = f"T-{tier_val}"
            pw, ph = get_text_size(draw, pill_text, font_pill)
            px = cx + col_w - 24 - pw - 10
            py = hy + 18
            draw.rounded_rectangle([px, py, px + pw + 10, py + ph + 6], radius=4, fill=col["header_bg"], outline=col["border"], width=1)
            draw.text((px + 5, py + 3), pill_text, fill=col["text_color"], font=font_pill)

    # 5. Bottom Metadata Footer
    draw.line([(50, H - 55), (W - 50, H - 55)], fill=(35, 42, 58), width=1)

    font_bottom = load_font("Arial.ttf", 13)
    left_brand = "MANBA: MLBB.IO • MOBILE LEGENDS HERO TIER LIST & ITEM BUILD GUIDE"
    draw.text((55, H - 38), left_brand, fill=(148, 163, 184), font=font_bottom)

    right_brand = "TELEGRAM: @MURODALIEVGG"
    rw, rh = get_text_size(draw, right_brand, font_bottom)
    draw.text((W - 55 - rw, H - 38), right_brand, fill=(56, 189, 248), font=font_bottom)

    return image_to_png_bytes(im)
