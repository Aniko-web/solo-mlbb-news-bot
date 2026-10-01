import os
import io
import math
from typing import Optional, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont

from app.utils.logger import logger
from app.media.templates.common import (
    load_font,
    get_text_size,
    image_to_png_bytes,
    draw_shared_brand_badge,
    LOGOS_DIR,
    FONTS_DIR
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
HERO_PORTRAITS_DIR = os.path.join(BASE_DIR, "assets", "heroes", "portraits")
MLBB_LOGO_PATH = os.path.join(LOGOS_DIR, "mlbb_logo.png")
MLBB_CREST_PATH = os.path.join(LOGOS_DIR, "mlbb_crest.png")
MUROD_LOGO_PATH = os.path.join(LOGOS_DIR, "murod_aliev_logo.png")

TYPE_CONFIGS = {
    "FACT": {
        "badge_text": "💡 MLBB QIZIQARLI FAKT",
        "primary_color": (245, 158, 11),     # Amber / Gold
        "secondary_color": (6, 182, 212),    # Cyan
        "bg_glow": (245, 158, 11, 25),
        "quote_tag": "BILASIZMI?"
    },
    "JOKE": {
        "badge_text": "🎭 MLBB HAYOTIY HAZIL & MEM",
        "primary_color": (236, 72, 153),    # Hot Pink / Magenta
        "secondary_color": (168, 85, 247),   # Purple
        "bg_glow": (236, 72, 153, 25),
        "quote_tag": "HAYOTIY KADR"
    },
    "MEME": {
        "badge_text": "🎭 MLBB HAYOTIY HAZIL & MEM",
        "primary_color": (236, 72, 153),
        "secondary_color": (168, 85, 247),
        "bg_glow": (236, 72, 153, 25),
        "quote_tag": "HAYOTIY KADR"
    },
    "LORE": {
        "badge_text": "⚔️ LAND OF DAWN TARIXI & LORE",
        "primary_color": (59, 130, 246),     # Royal Blue
        "secondary_color": (147, 51, 234),   # Violet
        "bg_glow": (59, 130, 246, 25),
        "quote_tag": "QAHRAMON SIRLARI"
    },
    "TIP": {
        "badge_text": "🧠 PRO O'YINCHI MASLAHATI",
        "primary_color": (16, 185, 129),    # Emerald
        "secondary_color": (52, 211, 153),   # Mint
        "bg_glow": (16, 185, 129, 25),
        "quote_tag": "LAYFXAK"
    }
}


def _find_hero_portrait(hero_name: Optional[str]) -> Optional[str]:
    """Search for hero image in assets/heroes/portraits."""
    if not hero_name or not os.path.exists(HERO_PORTRAITS_DIR):
        return None

    clean = hero_name.lower().strip().replace(" ", "").replace("_", "").replace("-", "")
    for fname in os.listdir(HERO_PORTRAITS_DIR):
        cf = fname.lower().replace(".png", "").replace(".jpg", "").replace("_", "").replace("-", "")
        if clean == cf or clean in cf:
            return os.path.join(HERO_PORTRAITS_DIR, fname)
    return None


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Wrap text to fit within max_width pixels."""
    lines = []
    paragraphs = text.split("\n")
    for para in paragraphs:
        words = para.split(" ")
        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            w, _ = get_text_size(draw, test_line, font)
            if w <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
    return lines


def render_fun_card(
    topic_type: str = "FACT",
    title: str = "MLBB Qiziqarli Fakt",
    content: str = "",
    hero_name: Optional[str] = None,
    subtitle: Optional[str] = None
) -> bytes:
    """
    Render ultra-high quality 1200x675 esports graphic for MLBB Fun Facts, Jokes, Lore & Tips.
    Returns PNG image bytes.
    """
    W, H = 1200, 675
    im = Image.new("RGB", (W, H), color=(10, 11, 18))
    draw = ImageDraw.Draw(im)

    cfg = TYPE_CONFIGS.get(topic_type.upper(), TYPE_CONFIGS["FACT"])
    prim_color = cfg["primary_color"]
    sec_color = cfg["secondary_color"]

    # 1. Dark cyber esports gradient background
    for y in range(H):
        ratio = y / H
        r = int(10 + ratio * 15)
        g = int(11 + ratio * 12)
        b = int(18 + ratio * 28)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 2. Dynamic decorative geometric polygon accents
    bg_accent = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    acc_draw = ImageDraw.Draw(bg_accent)

    # Top-right angular chevrons
    acc_draw.polygon([(W - 320, 0), (W, 0), (W, 240), (W - 160, 110)], fill=(sec_color[0], sec_color[1], sec_color[2], 25))
    acc_draw.polygon([(W - 200, 0), (W, 0), (W, 140), (W - 100, 70)], fill=(prim_color[0], prim_color[1], prim_color[2], 40))
    acc_draw.line([(W - 340, 0), (W, 260)], fill=(prim_color[0], prim_color[1], prim_color[2], 90), width=4)

    # Bottom-left angular accents
    acc_draw.polygon([(0, H - 240), (220, H), (0, H)], fill=(prim_color[0], prim_color[1], prim_color[2], 22))
    acc_draw.line([(0, H - 260), (240, H)], fill=(sec_color[0], sec_color[1], sec_color[2], 80), width=4)

    # Center ambient soft radial glow
    for rad in range(350, 0, -25):
        alpha = int((1 - rad / 350) * 28)
        acc_draw.ellipse([W // 2 - rad, H // 2 - rad, W // 2 + rad, H // 2 + rad], fill=(prim_color[0], prim_color[1], prim_color[2], alpha))

    im.paste(bg_accent, (0, 0), bg_accent)
    draw = ImageDraw.Draw(im)

    # 3. Top Header Bar
    font_badge = load_font("Arial-Bold.ttf", 15)
    font_quote = load_font("Arial-Bold.ttf", 13)

    # Left: Official MLBB Crest / Logo
    logo_offset_x = 60
    if os.path.exists(MLBB_LOGO_PATH):
        try:
            l_img = Image.open(MLBB_LOGO_PATH).convert("RGBA")
            l_img.thumbnail((120, 52), Image.Resampling.LANCZOS)
            im.paste(l_img, (logo_offset_x, 32), l_img)
            logo_offset_x += l_img.width + 18
        except Exception:
            pass

    # Badge Pill (Category)
    badge_label = cfg["badge_text"]
    bw, bh = get_text_size(draw, badge_label, font_badge)
    pill_w = bw + 28
    pill_h = bh + 14
    pill_x = logo_offset_x
    pill_y = 36

    # Draw rounded badge pill
    draw.rounded_rectangle(
        [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
        radius=pill_h // 2,
        fill=(25, 28, 44),
        outline=prim_color,
        width=2
    )
    draw.text((pill_x + 14, pill_y + 7), badge_label, fill=(255, 255, 255), font=font_badge)

    # Right: Murod Aliev Brand Watermark
    if os.path.exists(MUROD_LOGO_PATH):
        try:
            m_img = Image.open(MUROD_LOGO_PATH).convert("RGBA")
            mh = 38
            mw = int(m_img.width * (mh / m_img.height))
            m_scaled = m_img.resize((mw, mh), Image.Resampling.LANCZOS)
            im.paste(m_scaled, (W - mw - 60, 36), mask=m_scaled)
        except Exception:
            draw_shared_brand_badge(im, W - 180, 40, theme="id")
    else:
        draw_shared_brand_badge(im, W - 180, 40, theme="id")

    # Separator Line
    draw.line([(60, 95), (W - 60, 95)], fill=(38, 43, 62), width=2)
    draw.line([(60, 95), (pill_x + pill_w, 95)], fill=prim_color, width=3)

    # 4. Main Body: Featured Hero Portrait & Content Card
    portrait_path = _find_hero_portrait(hero_name)
    has_hero_portrait = portrait_path is not None and os.path.exists(portrait_path)

    card_left = 60
    card_width = W - 120

    if has_hero_portrait:
        # Left side: Hero Frame
        hero_frame_w = 260
        hero_center_x = 60 + hero_frame_w // 2
        hero_center_y = 350
        card_left = 60 + hero_frame_w + 35
        card_width = W - card_left - 60

        try:
            h_img = Image.open(portrait_path).convert("RGBA")
            h_size = 210
            h_img = h_img.resize((h_size, h_size), Image.Resampling.LANCZOS)

            # Circular mask for hero portrait
            mask = Image.new("L", (h_size, h_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, h_size, h_size], fill=255)

            # Draw outer glowing ring
            for ring in range(h_size // 2 + 14, h_size // 2 + 2, -2):
                alpha = int((ring - (h_size // 2 + 2)) / 12 * 90)
                draw.ellipse(
                    [hero_center_x - ring, hero_center_y - ring, hero_center_x + ring, hero_center_y + ring],
                    outline=(prim_color[0], prim_color[1], prim_color[2], alpha),
                    width=2
                )

            # Solid neon ring
            draw.ellipse(
                [hero_center_x - h_size // 2 - 4, hero_center_y - h_size // 2 - 4,
                 hero_center_x + h_size // 2 + 4, hero_center_y + h_size // 2 + 4],
                outline=prim_color,
                width=4
            )

            im.paste(h_img, (hero_center_x - h_size // 2, hero_center_y - h_size // 2), mask=h_img)

            # Hero Name Tag Badge under portrait
            hero_display_name = (hero_name or "").upper()
            font_hero_name = load_font("Impact.ttf", 24)
            hn_w, hn_h = get_text_size(draw, hero_display_name, font_hero_name)
            tag_y = hero_center_y + h_size // 2 + 18
            draw.rounded_rectangle(
                [hero_center_x - hn_w // 2 - 16, tag_y, hero_center_x + hn_w // 2 + 16, tag_y + hn_h + 10],
                radius=10,
                fill=(20, 24, 38),
                outline=sec_color,
                width=2
            )
            draw.text((hero_center_x - hn_w // 2, tag_y + 4), hero_display_name, fill=(255, 255, 255), font=font_hero_name)
        except Exception as e:
            logger.warning(f"Failed to render hero portrait {portrait_path}: {e}")
            card_left = 60
            card_width = W - 120

    # Right side (or Full): Content Box
    box_y = 125
    box_h = 490

    # Draw Frosted Glass Content Container
    glass_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glass_layer)
    g_draw.rounded_rectangle(
        [card_left, box_y, card_left + card_width, box_y + box_h],
        radius=16,
        fill=(16, 20, 32, 220),
        outline=(50, 58, 85, 200),
        width=2
    )
    # Accent top border strip on container
    g_draw.rounded_rectangle(
        [card_left, box_y, card_left + card_width, box_y + 6],
        radius=3,
        fill=(prim_color[0], prim_color[1], prim_color[2], 255)
    )
    im.paste(glass_layer, (0, 0), mask=glass_layer)
    draw = ImageDraw.Draw(im)

    # Inner Content Text
    font_title = load_font("Arial-Black.ttf", 27)
    font_body = load_font("Arial-Bold.ttf", 20)
    font_footer = load_font("Arial-Bold.ttf", 13)

    pad_x = 35
    text_max_w = card_width - (pad_x * 2)
    cur_y = box_y + 30

    # Tag Quote (e.g. "BILASIZMI?" or "HAYOTIY KADR")
    tag_label = f"★ {cfg['quote_tag']}"
    draw.text((card_left + pad_x, cur_y), tag_label, fill=prim_color, font=font_quote)
    cur_y += 28

    # Title
    title_text = title.strip().upper()
    title_lines = _wrap_text(title_text, font_title, text_max_w, draw)
    for t_line in title_lines[:2]:
        draw.text((card_left + pad_x, cur_y), t_line, fill=(255, 255, 255), font=font_title)
        cur_y += 38
    cur_y += 10

    # Decorative mini divider inside box
    draw.line([(card_left + pad_x, cur_y), (card_left + pad_x + 90, cur_y)], fill=sec_color, width=3)
    cur_y += 20

    # Body Content Text
    content_lines = _wrap_text(content.strip(), font_body, text_max_w, draw)
    max_body_lines = 8 if has_hero_portrait else 9
    for b_line in content_lines[:max_body_lines]:
        draw.text((card_left + pad_x, cur_y), b_line, fill=(225, 232, 245), font=font_body)
        cur_y += 32

    # Card Footer inside box
    footer_y = box_y + box_h - 40
    draw.line([(card_left + pad_x, footer_y - 10), (card_left + card_width - pad_x, footer_y - 10)], fill=(35, 42, 60), width=1)
    draw.text((card_left + pad_x, footer_y), "#MLBB #MobileLegendsUz #murodalievgg", fill=(120, 135, 165), font=font_footer)

    badge_channel = "⭐️ @murodalievgg • TELEGRAM"
    bc_w, _ = get_text_size(draw, badge_channel, font_footer)
    draw.text((card_left + card_width - pad_x - bc_w, footer_y), badge_channel, fill=sec_color, font=font_footer)

    return image_to_png_bytes(im)
