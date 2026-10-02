import os
import io
import math
from typing import Tuple, Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont

from app.utils.logger import logger

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
LOGOS_DIR = os.path.join(ASSETS_DIR, "logos")

FONT_IMPACT = os.path.join(FONTS_DIR, "Impact.ttf")
FONT_ANTON = os.path.join(FONTS_DIR, "Anton-Regular.ttf")
FONT_ARIAL_BOLD = os.path.join(FONTS_DIR, "Arial-Bold.ttf")
FONT_ARIAL_BLACK = os.path.join(FONTS_DIR, "Arial-Black.ttf")

# Known MLBB team color identities and abbreviations
TEAM_IDENTITIES: Dict[str, Tuple[Tuple[int, int, int], str]] = {
    # MPL ID
    "RRQ": ((243, 112, 33), "RRQ"),
    "ONIC": ((255, 210, 0), "ONIC"),
    "ONIC ID": ((255, 210, 0), "ONIC"),
    "FNATIC ONIC": ((255, 210, 0), "ONIC"),
    "EVOS": ((30, 144, 255), "EVOS"),
    "BTR": ((227, 27, 35), "BTR"),
    "BIGETRON": ((227, 27, 35), "BTR"),
    "GEEK": ((210, 30, 30), "GEEK"),
    "AE": ((180, 20, 20), "AE"),
    "ALTER EGO": ((180, 20, 20), "AE"),
    "DEWA": ((212, 160, 23), "DEWA"),
    "TLID": ((56, 189, 248), "TLID"),
    "LIQUID ID": ((56, 189, 248), "TLID"),
    "TEAM LIQUID": ((56, 189, 248), "TLID"),
    "NAVI": ((255, 230, 0), "NAVI"),
    "NATUS VINCERE": ((255, 230, 0), "NAVI"),
    "RBL": ((50, 120, 220), "RBL"),
    "REBELLION": ((50, 120, 220), "RBL"),
    # MPL PH
    "APBR": ((212, 175, 55), "APBR"),
    "AP.BREN": ((212, 175, 55), "APBR"),
    "BREN": ((212, 175, 55), "APBR"),
    "FALCONS": ((1, 191, 110), "FLCN"),
    "TEAM FALCONS": ((1, 191, 110), "FLCN"),
    "FLCN": ((1, 191, 110), "FLCN"),
    "ONIC PH": ((255, 210, 0), "ONPH"),
    "FNATIC ONIC PH": ((255, 210, 0), "ONPH"),
    "ONPH": ((255, 210, 0), "ONPH"),
    "FNOP": ((255, 210, 0), "ONIC"),
    "TLPH": ((0, 191, 178), "TLPH"),
    "LIQUID": ((56, 189, 248), "TLPH"),
    "BLCK": ((226, 232, 240), "BLCK"),
    "BLACKLIST": ((226, 232, 240), "BLCK"),
    "OMG": ((52, 211, 153), "OMG"),
    "OMEGA": ((52, 211, 153), "OMG"),
    "SMART OMEGA": ((52, 211, 153), "OMG"),
    "RSG": ((230, 50, 50), "RSG"),
    "TNC": ((255, 102, 0), "TNC"),
    "AURORA": ((14, 198, 186), "RORA"),
    "AURORA PH": ((14, 198, 186), "RORA"),
    "RORA": ((14, 198, 186), "RORA"),
    "TWIS": ((235, 70, 125), "TWIS")
}


def load_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    """Load TTF font with fallback to bundled fonts or system default."""
    target_path = os.path.join(FONTS_DIR, font_name)
    if os.path.exists(target_path):
        try:
            return ImageFont.truetype(target_path, size)
        except Exception:
            pass

    for fallback in [
        FONT_IMPACT,
        FONT_ANTON,
        FONT_ARIAL_BOLD,
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]:
        if os.path.exists(fallback):
            try:
                return ImageFont.truetype(fallback, size)
            except Exception:
                pass
    return ImageFont.load_default()


def get_text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
    """Return width and height of rendered text."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])


def draw_vector_star(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    r_outer: float = 10.0,
    r_inner: float = 4.5,
    fill: Tuple[int, int, int] = (255, 215, 0)
):
    """Draw a geometric 5-pointed golden star vector."""
    points = []
    for i in range(10):
        r = r_outer if i % 2 == 0 else r_inner
        angle = i * math.pi / 5 - math.pi / 2
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=fill)


def load_team_logo(
    team_name: str,
    logo_path_or_url: Optional[str] = None,
    max_size: Tuple[int, int] = (130, 130)
) -> Image.Image:
    """
    Load team logo from file or generate a sharp vector esports insignia.
    Always returns a clean RGBA Image sized within max_size.
    """
    upper = (team_name or "").upper().strip()

    # 1. Custom path
    if logo_path_or_url and os.path.exists(logo_path_or_url):
        try:
            img = Image.open(logo_path_or_url).convert("RGBA")
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            return img
        except Exception as e:
            logger.warning(f"Failed to open logo from {logo_path_or_url}: {e}")

    # 2. Bundled logos in assets/logos
    team_candidates_map = {
        # MPL ID
        "TEAM LIQUID ID": ["tlid.png", "team_liquid_id.png", "team_liquid.png", "liquid_id.png"],
        "BIGETRON ALPHA": ["btr.png", "bigetron.png"],
        "NATUS VINCERE": ["navi.png", "na_vi.png", "natus_vincere.png"],
        "REBELLION ESPORTS": ["rebellion.png", "rbl.png"],
        "DEWA UNITED": ["dewa.png", "dewa_united.png", "dewa united.png"],
        "ALTER EGO": ["alter_ego.png", "ae.png", "alter ego.png"],
        "EVOS GLORY": ["evos.png", "evos_glory.png"],
        "ONIC ID": ["onic_id.png", "onic.png"],
        "FNATIC ONIC ID": ["onic.png"],
        "RRQ HOSHI": ["rrq.png", "rrq_hoshi.png"],
        "GEEK FAM": ["geek.png", "geek_fam.png", "geek fam.png"],
        "BIGETRON": ["btr.png", "bigetron.png"],
        "REBELLION": ["rebellion.png", "rbl.png"],
        "TL ID": ["tlid.png", "team_liquid_id.png", "team_liquid.png", "liquid_id.png"],
        "TLID": ["tlid.png", "team_liquid_id.png", "team_liquid.png", "liquid_id.png"],
        "NAVI": ["navi.png", "na_vi.png", "natus_vincere.png"],
        "DEWA": ["dewa.png", "dewa_united.png", "dewa united.png"],
        "EVOS": ["evos.png", "evos_glory.png"],
        "GEEK": ["geek.png", "geek_fam.png", "geek fam.png"],
        "BTR": ["btr.png", "bigetron.png"],
        "RRQ": ["rrq.png", "rrq_hoshi.png"],
        "RBL": ["rbl.png", "rebellion.png"],
        "AE": ["alter_ego.png", "ae.png", "alter ego.png"],
        # MPL PH
        "FNATIC ONIC PH": ["onic_ph.png", "fnatic_onic_ph.png", "onph.png"],
        "ONIC PHILIPPINES": ["onic_ph.png", "fnatic_onic_ph.png", "onph.png"],
        "ONIC PH": ["onic_ph.png", "fnatic_onic_ph.png", "onph.png"],
        "ONPH": ["onic_ph.png", "fnatic_onic_ph.png", "onph.png"],
        "TEAM FALCONS": ["team_falcons.png", "falcons.png", "flcn.png"],
        "FALCONS": ["falcons.png", "team_falcons.png", "flcn.png"],
        "FLCN": ["flcn.png", "falcons.png", "team_falcons.png"],
        "FALCONS AP.BREN": ["apbr.png", "ap_bren.png", "bren.png"],
        "AP.BREN": ["apbr.png", "ap_bren.png", "bren.png"],
        "APBR": ["apbr.png", "ap_bren.png", "bren.png"],
        "BREN": ["apbr.png", "ap_bren.png", "bren.png"],
        "AURORA GAMING": ["aurora.png", "aurora_gaming.png", "rora.png"],
        "AURORA PH": ["aurora_ph.png", "aurora.png", "rora.png"],
        "AURORA": ["aurora.png", "rora.png"],
        "RORA": ["rora.png", "aurora.png"],
        "SMART OMEGA": ["smart_omega.png", "omega.png", "omg.png"],
        "OMEGA": ["smart_omega.png", "omega.png", "omg.png"],
        "OMG": ["omg.png", "smart_omega.png", "omega.png"],
        "TWISTED MINDS PH": ["twisted_minds_ph.png", "twph.png", "twisted_minds.png", "twis.png"],
        "TWISTED MINDS": ["twisted_minds.png", "twis.png", "twisted_minds_ph.png", "twph.png"],
        "TWPH": ["twph.png", "twisted_minds_ph.png", "twisted_minds.png"],
        "TWIS": ["twis.png", "twisted_minds.png"],
        "TEAM LIQUID PH": ["team_liquid_ph.png", "tlph.png", "team_liquid.png", "liquid.png"],
        "TEAM LIQUID": ["team_liquid.png", "liquid.png", "team_liquid_ph.png", "tlph.png"],
        "LIQUID": ["liquid.png", "team_liquid.png", "tlph.png", "tlid.png"],
        "TLPH": ["tlph.png", "team_liquid_ph.png", "team_liquid.png"],
        "BLACKLIST INT.": ["blck.png", "blacklist.png"],
        "BLACKLIST": ["blck.png", "blacklist.png"],
        "BLCK": ["blck.png", "blacklist.png"],
        "TNC PRO TEAM": ["tnc_pro_team.png", "tnc.png"],
        "TNC": ["tnc.png", "tnc_pro_team.png"],
        "RSG": ["rsg.png"],
        # Generic ONIC (ID)
        "ONIC": ["onic.png"],
        "FNOP": ["onic.png"],
    }

    # Match longest keys first so "ONIC PH" or "TEAM FALCONS" matches before "ONIC"
    for key, filenames in sorted(team_candidates_map.items(), key=lambda x: len(x[0]), reverse=True):
        if key in upper:
            for fname in filenames:
                candidate = os.path.join(LOGOS_DIR, fname)
                if os.path.exists(candidate):
                    try:
                        img = Image.open(candidate).convert("RGBA")
                        img.thumbnail(max_size, Image.Resampling.LANCZOS)
                        return img
                    except Exception:
                        pass

    for key in TEAM_IDENTITIES:
        if key in upper:
            for fname in [f"{key.lower()}.png", f"{key.lower().replace(' ', '_')}.png"]:
                candidate = os.path.join(LOGOS_DIR, fname)
                if os.path.exists(candidate):
                    try:
                        img = Image.open(candidate).convert("RGBA")
                        img.thumbnail(max_size, Image.Resampling.LANCZOS)
                        return img
                    except Exception:
                        pass

    # 3. Dedicated vector insignia
    return create_vector_team_crest(team_name, max_size)


def create_vector_team_crest(team_name: str, size: Tuple[int, int]) -> Image.Image:
    """Draw a vector esports shield with distinctive team symbols."""
    upper = (team_name or "TEAM").upper().strip()
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx = w // 2
    cy = h // 2
    r = min(w, h) // 2 - 4

    font_bold = load_font("Impact.ttf", 26)
    font_sub = load_font("Arial-Bold.ttf", 14)

    if "RRQ" in upper:
        # King's Crown in orange/gold
        poly_crown = [
            (cx - 36, cy + 24),
            (cx - 32, cy - 18),
            (cx - 16, cy + 2),
            (cx, cy - 28),
            (cx + 16, cy + 2),
            (cx + 32, cy - 18),
            (cx + 36, cy + 24)
        ]
        draw.polygon(poly_crown, fill=(245, 115, 30), outline=(255, 185, 50), width=2)
        draw.text((cx - 20, cy + 2), "RRQ", fill=(255, 255, 255), font=font_sub)
        return img

    if "EVOS" in upper:
        # Royal blue shield with white roaring tiger mark
        poly_evos = [(cx, cy - 36), (cx + 34, cy - 18), (cx + 26, cy + 26), (cx, cy + 38), (cx - 26, cy + 26), (cx - 34, cy - 18)]
        draw.polygon(poly_evos, fill=(0, 95, 175), outline=(0, 190, 255), width=2)
        draw.text((cx - 22, cy - 14), "EVO", fill=(255, 255, 255), font=font_bold)
        return img

    if "APBR" in upper or "BREN" in upper or "FALCON" in upper:
        # Golden shield with falcon wings
        poly_bren = [(cx, cy - 38), (cx + 34, cy - 22), (cx + 28, cy + 22), (cx, cy + 40), (cx - 28, cy + 22), (cx - 34, cy - 22)]
        draw.polygon(poly_bren, fill=(212, 175, 55), outline=(255, 235, 130), width=2)
        poly_in = [(cx, cy - 32), (cx + 28, cy - 18), (cx + 22, cy + 18), (cx, cy + 34), (cx - 22, cy + 18), (cx - 28, cy - 18)]
        draw.polygon(poly_in, fill=(18, 18, 22))
        draw.text((cx - 18, cy - 12), "AP", fill=(255, 220, 80), font=font_bold)
        return img

    if "BTR" in upper or "BIGETRON" in upper:
        # Crimson robotic eye
        draw.ellipse([cx - 36, cy - 36, cx + 36, cy + 36], fill=(220, 25, 35), outline=(255, 255, 255), width=3)
        draw.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=(255, 255, 255))
        draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(20, 20, 20))
        return img

    if "OMG" in upper or "OMEGA" in upper:
        # Emerald green Omega ring
        draw.ellipse([cx - 36, cy - 36, cx + 36, cy + 36], outline=(0, 210, 130), width=5)
        draw.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=(10, 32, 24))
        draw.arc([cx - 20, cy - 20, cx + 20, cy + 20], start=45, end=135, fill=(0, 240, 150), width=5)
        draw.line([(cx - 20, cy + 12), (cx - 10, cy + 12)], fill=(0, 240, 150), width=5)
        draw.line([(cx + 10, cy + 12), (cx + 20, cy + 12)], fill=(0, 240, 150), width=5)
        return img

    if "BLCK" in upper or "BLACKLIST" in upper:
        # Black diamond with white 'B'
        draw.polygon([(cx, cy - 36), (cx + 34, cy), (cx, cy + 36), (cx - 34, cy)], fill=(22, 22, 26), outline=(245, 245, 250), width=3)
        draw.text((cx - 12, cy - 18), "B", fill=(255, 255, 255), font=load_font("Impact.ttf", 34))
        return img

    if "TLPH" in upper or "LIQUID" in upper:
        # Navy shield with cyan crest
        poly_tl = [(cx, cy - 36), (cx + 34, cy - 18), (cx + 26, cy + 26), (cx, cy + 38), (cx - 26, cy + 26), (cx - 34, cy - 18)]
        draw.polygon(poly_tl, fill=(10, 30, 60), outline=(0, 210, 200), width=2)
        draw.text((cx - 18, cy - 14), "TL", fill=(0, 220, 210), font=font_bold)
        return img

    # Generic team shield
    color = (0, 200, 180)
    for key, (c, _) in TEAM_IDENTITIES.items():
        if key in upper:
            color = c
            break

    poly = [
        (cx, cy - r),
        (cx + r, cy - r // 2),
        (cx + int(r * 0.8), cy + int(r * 0.6)),
        (cx, cy + r),
        (cx - int(r * 0.8), cy + int(r * 0.6)),
        (cx - r, cy - r // 2)
    ]
    draw.polygon(poly, fill=(18, 22, 30, 240), outline=color, width=3)

    r_in = r - 6
    poly_in = [
        (cx, cy - r_in),
        (cx + r_in, cy - r_in // 2),
        (cx + int(r_in * 0.8), cy + int(r_in * 0.6)),
        (cx, cy + r_in),
        (cx - int(r_in * 0.8), cy + int(r_in * 0.6)),
        (cx - r_in, cy - r_in // 2)
    ]
    draw.polygon(poly_in, fill=(10, 14, 20, 255))

    words = [wd for wd in upper.split() if wd]
    code = "".join(wd[0] for wd in words)[:4] if len(words) > 1 else upper[:4]
    tw, th = get_text_size(draw, code, font_bold)
    draw.text((cx - tw / 2, cy - th / 2 - 2), code, fill=(255, 255, 255), font=font_bold)

    return img


def draw_shared_brand_badge(
    img: Image.Image,
    x: int,
    y: int,
    theme: str = "id"
):
    """Draw small unified 'MLBB NEWS UZ' branding badge."""
    draw = ImageDraw.Draw(img)
    font_brand = load_font("Arial-Bold.ttf", 13)

    brand_text = "@murodalievgg"
    tw, th = get_text_size(draw, brand_text, font_brand)

    badge_w = tw + 34
    badge_h = 28
    radius = 6

    if theme == "id":
        bg = (18, 20, 26, 230)
        border = (220, 38, 38)
        dot_color = (220, 38, 38)
        text_color = (241, 245, 249)
    else:
        bg = (10, 22, 44, 230)
        border = (14, 165, 233)
        dot_color = (56, 189, 248)
        text_color = (248, 250, 252)

    draw.rounded_rectangle([x, y, x + badge_w, y + badge_h], radius=radius, fill=bg, outline=border, width=1)
    dot_y = y + badge_h // 2
    draw.ellipse([x + 10, dot_y - 3, x + 16, dot_y + 3], fill=dot_color)
    draw.text((x + 22, y + 6), brand_text, fill=text_color, font=font_brand)


def image_to_png_bytes(im: Image.Image) -> bytes:
    """Export PIL Image to highly optimized PNG bytes."""
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
