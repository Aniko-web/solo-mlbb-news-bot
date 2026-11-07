import os
from typing import Dict, Any, List
from PIL import Image, ImageDraw

from app.media.templates.common import (
    load_font,
    get_text_size,
    load_team_logo,
    draw_shared_brand_badge,
    image_to_png_bytes,
    ASSETS_DIR,
    LOGOS_DIR
)

HEROES_DIR = os.path.join(ASSETS_DIR, "heroes")


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

            # Hero Avatar (try to load local hero image or circle fallback)
            hero_name = h.get("hero_name", "Hero")
            avatar_drawn = False
            if os.path.exists(HEROES_DIR):
                for ext in (".png", ".jpg", ".jpeg"):
                    candidate = os.path.join(HEROES_DIR, f"{hero_name.lower().replace(' ', '_')}{ext}")
                    if os.path.exists(candidate):
                        try:
                            ava = Image.open(candidate).convert("RGBA")
                            ava.thumbnail((48, 48), Image.Resampling.LANCZOS)
                            im.paste(ava, (cx + 20, hy + 8), ava)
                            avatar_drawn = True
                            break
                        except Exception:
                            pass

            if not avatar_drawn:
                # Stylish monogram circle
                draw.ellipse([cx + 20, hy + 8, cx + 64, hy + 52], fill=col["header_bg"], outline=col["border"], width=1)
                initial = hero_name[:2].upper()
                font_init = load_font("Impact.ttf", 18)
                iw, ih = get_text_size(draw, initial, font_init)
                draw.text((cx + 42 - iw // 2, hy + 30 - ih // 2), initial, fill=(245, 245, 245), font=font_init)

            # Hero Name & Info
            draw.text((cx + 74, hy + 12), hero_name[:16], fill=(245, 245, 250), font=font_hero_name)

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

            draw.text((cx + 74, hy + 34), info_line, fill=(148, 163, 184), font=font_hero_info)

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
