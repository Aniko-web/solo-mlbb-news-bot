import os
import io
import math
from typing import List, Optional, Dict, Any, Tuple
import httpx
from PIL import Image, ImageDraw, ImageFont

from app.utils.logger import logger

# Paths to bundled assets (fonts and official logos)
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
LOGOS_DIR = os.path.join(ASSETS_DIR, "logos")
FONT_IMPACT = os.path.join(FONTS_DIR, "Impact.ttf")
FONT_ANTON = os.path.join(FONTS_DIR, "Anton-Regular.ttf")
FONT_ARIAL_BOLD = os.path.join(FONTS_DIR, "Arial-Bold.ttf")
FONT_ARIAL_BLACK = os.path.join(FONTS_DIR, "Arial-Black.ttf")

# Known MLBB team color identities and abbreviations
TEAM_IDENTITIES: Dict[str, Tuple[Tuple[int, int, int], str]] = {
    # MPL PH
    "APBR": ((212, 175, 55), "APBR"),
    "FALCONS": ((212, 175, 55), "APBR"),
    "BREN": ((212, 175, 55), "APBR"),
    "FNOP": ((245, 179, 0), "ONIC"),
    "FNATIC": ((245, 179, 0), "ONIC"),
    "ONIC": ((245, 179, 0), "ONIC"),
    "TLPH": ((0, 191, 178), "TLPH"),
    "LIQUID": ((0, 191, 178), "TLPH"),
    "BLCK": ((40, 40, 45), "BLCK"),
    "BLACKLIST": ((40, 40, 45), "BLCK"),
    "OMG": ((0, 168, 120), "OMG"),
    "OMEGA": ((0, 168, 120), "OMG"),
    "RSG": ((230, 50, 50), "RSG"),
    "TNC": ((255, 102, 0), "TNC"),
    "AURORA": ((80, 120, 240), "RORA"),
    "TWIS": ((235, 70, 125), "TWIS"),
    # MPL ID
    "RRQ": ((243, 112, 33), "RRQ"),
    "EVOS": ((0, 91, 170), "EVOS"),
    "BTR": ((227, 27, 35), "BTR"),
    "BIGETRON": ((227, 27, 35), "BTR"),
    "GEEK": ((200, 30, 30), "GEEK"),
    "AE": ((180, 20, 20), "AE"),
    "ALTER EGO": ((180, 20, 20), "AE"),
    "DEWA": ((212, 160, 23), "DEWA"),
    "RBL": ((50, 120, 220), "RBL"),
    "REBELLION": ((50, 120, 220), "RBL")
}


def _load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load TTF font with fallback to system default."""
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    for fallback in [
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


def _draw_slanted_text(
    target_img: Image.Image,
    cx: float,
    cy: float,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill_color: Tuple[int, int, int],
    angle_deg: float = 10.0
):
    """Draw text with italic/slanted transform to match broadcast graphics."""
    dummy_img = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    bbox = dummy_draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0] + 20
    th = bbox[3] - bbox[1] + 20

    pad = 30
    patch = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(patch)
    pdraw.text((pad - bbox[0], pad - bbox[1]), text, fill=fill_color, font=font)

    m = -math.tan(math.radians(angle_deg))
    sheared = patch.transform(
        (patch.width + int(abs(m) * patch.height), patch.height),
        Image.AFFINE,
        (1, m, 0, 0, 1, 0),
        Image.Resampling.BILINEAR
    )

    px = int(cx - sheared.width / 2)
    py = int(cy - sheared.height / 2)
    target_img.paste(sheared, (px, py), sheared)


class ImageProcessor:
    """
    State-of-the-art Esports Graphic Generator for MLBB match results, schedules, and patch updates.
    Replicates official MPL broadcast graphic packages with slanted teal cards, glowing borders,
    custom team vector crests, and sheared scores.
    """

    @classmethod
    def _draw_team_emblem(
        cls,
        target_img: Image.Image,
        draw: ImageDraw.ImageDraw,
        cx: int,
        cy: int,
        team_name: str
    ):
        """Draw official logo if available in assets/logos, or accurate vector insignia."""
        upper = team_name.upper()

        # 1. Official transparent logo file from assets/logos
        logo_file = None
        if "ONIC" in upper or "FNOP" in upper:
            logo_file = os.path.join(LOGOS_DIR, "onic.png")
        else:
            for key in TEAM_IDENTITIES:
                if key in upper:
                    candidate = os.path.join(LOGOS_DIR, f"{key.lower()}.png")
                    if os.path.exists(candidate):
                        logo_file = candidate
                        break

        if logo_file and os.path.exists(logo_file):
            try:
                logo_img = Image.open(logo_file).convert("RGBA")
                logo_img.thumbnail((78, 62), Image.Resampling.LANCZOS)
                lx = int(cx - logo_img.width / 2)
                ly = int(cy - logo_img.height / 2)
                target_img.paste(logo_img, (lx, ly), logo_img)
                return
            except Exception as e:
                logger.warning(f"Error loading logo {logo_file}: {e}")

        font_bold = _load_font(FONT_IMPACT, 22)
        font_sub = _load_font(FONT_ARIAL_BOLD, 12)

        if "TWIS" in upper:
            # Twisted Mind / Brain Icon (Pink brain lobes & folds)
            draw.ellipse([cx - 30, cy - 22, cx + 2, cy + 18], fill=(235, 70, 125))
            draw.ellipse([cx - 2, cy - 22, cx + 30, cy + 18], fill=(235, 70, 125))
            draw.ellipse([cx - 24, cy - 28, cx + 24, cy - 2], fill=(245, 95, 145))
            draw.ellipse([cx - 20, cy + 2, cx + 20, cy + 24], fill=(225, 60, 115))
            draw.arc([cx - 22, cy - 18, cx - 4, cy + 8], start=30, end=300, fill=(255, 210, 230), width=3)
            draw.arc([cx + 4, cy - 18, cx + 22, cy + 8], start=240, end=150, fill=(255, 210, 230), width=3)
            draw.arc([cx - 14, cy - 24, cx + 14, cy - 6], start=180, end=0, fill=(255, 220, 235), width=3)
            draw.line([(cx, cy - 20), (cx, cy + 20)], fill=(170, 30, 80), width=3)
        elif "APBR" in upper or "BREN" in upper or "FALCON" in upper:
            # Falcons AP.Bren: Golden Shield with Falcon wings and crown
            poly = [
                (cx, cy - 30),
                (cx + 28, cy - 18),
                (cx + 22, cy + 18),
                (cx, cy + 32),
                (cx - 22, cy + 18),
                (cx - 28, cy - 18),
            ]
            draw.polygon(poly, fill=(212, 175, 55), outline=(255, 235, 130), width=2)
            poly_in = [
                (cx, cy - 25),
                (cx + 23, cy - 15),
                (cx + 17, cy + 14),
                (cx, cy + 26),
                (cx - 17, cy + 14),
                (cx - 23, cy - 15),
            ]
            draw.polygon(poly_in, fill=(18, 18, 22))
            draw.polygon([(cx - 16, cy - 10), (cx, cy - 22), (cx + 16, cy - 10), (cx, cy - 2)], fill=(245, 200, 45))
            draw.text((cx - 16, cy), "AP", fill=(255, 230, 100), font=font_bold)
        elif "OMG" in upper or "OMEGA" in upper:
            # Smart Omega: Emerald Green Omega Ring
            r = 28
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 210, 130), width=4)
            draw.ellipse([cx - r + 6, cy - r + 6, cx + r - 6, cy + r - 6], fill=(10, 32, 24))
            draw.arc([cx - 16, cy - 16, cx + 16, cy + 16], start=45, end=135, fill=(0, 240, 150), width=4)
            draw.line([(cx - 16, cy + 10), (cx - 8, cy + 10)], fill=(0, 240, 150), width=4)
            draw.line([(cx + 8, cy + 10), (cx + 16, cy + 10)], fill=(0, 240, 150), width=4)
            draw.rounded_rectangle([cx - 20, cy - 34, cx + 20, cy - 20], radius=5, fill=(0, 170, 95))
            draw.text((cx - 16, cy - 33), "SMART", fill=(255, 255, 255), font=_load_font(FONT_ARIAL_BOLD, 9))
        elif "ONIC" in upper or "FNOP" in upper:
            # Fnatic ONIC: Golden hedgehog / spike silhouette
            draw.polygon([
                (cx - 28, cy + 12),
                (cx - 24, cy - 5),
                (cx - 14, cy - 20),
                (cx, cy - 26),
                (cx + 16, cy - 20),
                (cx + 30, cy - 5),
                (cx + 22, cy + 16),
                (cx, cy + 26),
                (cx - 18, cy + 22)
            ], fill=(255, 210, 0))
            draw.polygon([(cx - 26, cy - 5), (cx - 18, cy - 20), (cx - 12, cy - 8)], fill=(18, 18, 18))
            draw.polygon([(cx - 10, cy - 20), (cx + 2, cy - 26), (cx + 5, cy - 12)], fill=(18, 18, 18))
            draw.polygon([(cx + 8, cy - 20), (cx + 22, cy - 18), (cx + 16, cy - 5)], fill=(18, 18, 18))
            draw.text((cx - 10, cy + 3), "PH", fill=(10, 10, 10), font=_load_font(FONT_ARIAL_BOLD, 13))
        elif "RRQ" in upper:
            # RRQ: King's Crown in orange/gold
            poly_crown = [
                (cx - 28, cy + 18),
                (cx - 26, cy - 14),
                (cx - 12, cy + 2),
                (cx, cy - 22),
                (cx + 12, cy + 2),
                (cx + 26, cy - 14),
                (cx + 28, cy + 18)
            ]
            draw.polygon(poly_crown, fill=(245, 115, 30), outline=(255, 180, 50), width=2)
            draw.text((cx - 16, cy + 2), "RRQ", fill=(255, 255, 255), font=font_sub)
        elif "BLCK" in upper or "BLACKLIST" in upper:
            # Blacklist: Sleek black diamond with white B
            draw.polygon([(cx, cy - 28), (cx + 26, cy), (cx, cy + 28), (cx - 26, cy)], fill=(22, 22, 26), outline=(245, 245, 250), width=2)
            draw.text((cx - 10, cy - 14), "B", fill=(255, 255, 255), font=_load_font(FONT_IMPACT, 26))
        elif "EVOS" in upper:
            # EVOS: Royal blue shield with white roaring tiger
            draw.polygon([(cx, cy - 28), (cx + 26, cy - 14), (cx + 20, cy + 20), (cx, cy + 28), (cx - 20, cy + 20), (cx - 26, cy - 14)], fill=(0, 95, 175), outline=(0, 190, 255), width=2)
            draw.text((cx - 16, cy - 12), "EVO", fill=(255, 255, 255), font=font_bold)
        elif "BTR" in upper or "BIGETRON" in upper:
            # Bigetron: Crimson robotic emblem
            r = 26
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(220, 25, 35), outline=(255, 255, 255), width=2)
            draw.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=(255, 255, 255))
            draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(20, 20, 20))
        elif "TLPH" in upper or "LIQUID" in upper or "ECHO" in upper:
            # Team Liquid: Navy shield with cyan crest
            poly_tl = [(cx, cy - 28), (cx + 26, cy - 14), (cx + 20, cy + 20), (cx, cy + 28), (cx - 20, cy + 20), (cx - 26, cy - 14)]
            draw.polygon(poly_tl, fill=(10, 30, 60), outline=(0, 210, 200), width=2)
            draw.text((cx - 14, cy - 10), "TL", fill=(0, 220, 210), font=font_bold)
        else:
            # Generic team emblem
            r = 26
            words = [w for w in team_name.split() if w]
            code = "".join(w[0] for w in words)[:4].upper() if words else team_name[:4].upper()
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(18, 34, 44), outline=(0, 220, 200), width=2)
            draw.text((cx - 14, cy - 8), code, fill=(255, 255, 255), font=font_sub)

    @classmethod
    def generate_mpl_matchup_graphic(
        cls,
        league: str = "MPL PHILIPPINES",
        team_a: str = "Team A",
        team_b: str = "Team B",
        score_a: Optional[int] = None,
        score_b: Optional[int] = None,
        status_text: str = "VS",
        matches: Optional[List[Dict[str, Any]]] = None,
        date_str: Optional[str] = None
    ) -> bytes:
        """
        Create league-specific broadcast-style graphic in 1200x675 PNG.
        Automatically routes to dedicated MPL ID or MPL PH templates.
        """
        from app.media.renderer import render_match_graphic

        first_match = matches[0] if (matches and len(matches) > 0) else {}
        m_team_a = first_match.get("team_a") or team_a
        m_team_b = first_match.get("team_b") or team_b
        m_score_a = first_match.get("score_a") if first_match.get("score_a") is not None else score_a
        m_score_b = first_match.get("score_b") if first_match.get("score_b") is not None else score_b
        m_time = first_match.get("time") or status_text or "15:00"
        m_series = first_match.get("series") or "BO3"
        m_date = date_str or first_match.get("date") or "29 SEPTEMBER"
        m_status = first_match.get("status") or ("FINAL" if (m_score_a is not None and m_score_b is not None) else "UPCOMING")
        m_mvp = first_match.get("mvp")

        match_data = {
            "league": league,
            "team_a": m_team_a,
            "team_b": m_team_b,
            "score_a": m_score_a,
            "score_b": m_score_b,
            "status": m_status,
            "mvp": m_mvp,
            "date": m_date,
            "time": m_time,
            "series": m_series,
            "season": "Season 14",
            "week": 4
        }
        return render_match_graphic(match_data)

    @classmethod
    def render_match_result(cls, match_data: Dict[str, Any]) -> bytes:
        from app.media.renderer import render_match_result
        return render_match_result(match_data)

    @classmethod
    def render_match_upcoming(cls, match_data: Dict[str, Any]) -> bytes:
        from app.media.renderer import render_match_upcoming
        return render_match_upcoming(match_data)

    @classmethod
    def generate_patch_graphic(
        cls,
        version: str,
        buffs: List[str],
        nerfs: List[str]
    ) -> bytes:
        """
        Create a sleek dark-themed visual patch graphic summarizing buffs & nerfs.
        """
        width, height = 1080, 720
        image = Image.new("RGB", (width, height), color=(12, 16, 24))
        draw = ImageDraw.Draw(image)

        font_header = _load_font(FONT_IMPACT, 52)
        font_sub = _load_font(FONT_ARIAL_BOLD, 20)
        font_section = _load_font(FONT_IMPACT, 30)
        font_item = _load_font(FONT_ARIAL_BOLD, 22)

        # Header bar
        draw.rectangle([0, 0, width, 115], fill=(18, 24, 38))
        draw.rectangle([0, 111, width, 115], fill=(0, 220, 200))

        # Title
        draw.text((40, 24), "MOBILE LEGENDS: BANG BANG", fill=(0, 220, 200), font=font_sub)
        draw.text((40, 52), f"PATCH NOTES {version.upper()}", fill=(255, 255, 255), font=font_header)

        # Column 1: BUFFS
        draw.rounded_rectangle([40, 140, 520, 195], radius=10, fill=(20, 50, 35), outline=(46, 204, 113), width=2)
        draw.text((60, 150), "🟢 BUFF (KUCHAYTIRILGANLAR)", fill=(46, 204, 113), font=font_section)

        y_offset = 215
        for buff in buffs[:5]:
            clean_b = buff[:48]
            draw.text((60, y_offset), f"• {clean_b}", fill=(245, 245, 245), font=font_item)
            y_offset += 48

        # Column 2: NERFS
        draw.rounded_rectangle([560, 140, 1040, 195], radius=10, fill=(55, 25, 30), outline=(231, 76, 60), width=2)
        draw.text((580, 150), "🔴 NERF (ZAIFLASHTIRILGANLAR)", fill=(231, 76, 60), font=font_section)

        y_offset = 215
        for nerf in nerfs[:5]:
            clean_n = nerf[:48]
            draw.text((580, y_offset), f"• {clean_n}", fill=(245, 245, 245), font=font_item)
            y_offset += 48

        # Footer
        draw.rectangle([0, height - 50, width, height], fill=(8, 12, 18))
        draw.text((40, height - 35), "MLBB Official Updates • Telegram Channel", fill=(120, 160, 175), font=font_sub)

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=92)
        return buffer.getvalue()

    @classmethod
    def render_patch_recap(cls, patch_data: Dict[str, Any]) -> bytes:
        """
        Render professional MLBB Patch Notes Recap Infographic matching GosuGamers / Moonton layout.
        Features categorized hero circular portraits (Buffs, Nerfs, Adjustments, Revamps),
        colored ring borders, hero names, vector badges, and dynamic brush splashes.
        """
        from app.media.templates.patch_recap import render_patch_recap
        return render_patch_recap(patch_data)

    @classmethod
    def generate_news_graphic(
        cls,
        title: str,
        category: str = "NEWS",
        summary: str = "",
        highlights: Optional[List[str]] = None
    ) -> bytes:
        """
        Create a high-impact 1200x675 broadcast graphic for MLBB news (skins, hero revamps, events, etc.)
        when no online photo is available.
        """
        width, height = 1200, 675
        image = Image.new("RGB", (width, height), color=(11, 15, 23))
        draw = ImageDraw.Draw(image)

        # Background gradient & decorative tech diagonals
        for y in range(height):
            ratio = y / height
            r = int(14 + (6 - 14) * ratio)
            g = int(18 + (10 - 18) * ratio)
            b = int(28 + (16 - 28) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Cyan / gold decorative angle shards
        cat_upper = category.upper()
        if "PATCH" in cat_upper:
            accent_color = (0, 220, 200) # Cyan
            badge_text = "🛠 PATCH NOTES"
        elif "SKIN" in cat_upper:
            accent_color = (255, 185, 0) # Gold
            badge_text = "✨ NEW SKIN"
        elif "HERO" in cat_upper:
            accent_color = (220, 80, 240) # Purple/Magenta
            badge_text = "🦸 HERO SPOTLIGHT / REVAMP"
        elif "EVENT" in cat_upper:
            accent_color = (255, 90, 95) # Crimson Coral
            badge_text = "🎉 SPECIAL EVENT"
        else:
            accent_color = (0, 190, 245) # Sky Cyan
            badge_text = "📢 MLBB RASMIY YANGILIK"

        # Angled geometric accents on borders
        draw.polygon([(0, 0), (320, 0), (260, 8), (0, 8)], fill=accent_color)
        draw.polygon([(width - 320, height - 8), (width, height - 8), (width, height), (width - 260, height)], fill=accent_color)

        # Fonts
        font_brand = _load_font(FONT_ARIAL_BOLD, 16)
        font_badge = _load_font(FONT_IMPACT, 22)
        font_title = _load_font(FONT_IMPACT, 44)
        font_summary = _load_font(FONT_ARIAL_BOLD, 22)
        font_bullet = _load_font(FONT_ARIAL_BOLD, 20)

        # Top Bar
        draw.rectangle([50, 40, 240, 72], fill=(20, 28, 42), outline=(40, 56, 80), width=1)
        draw.text((65, 48), "MLBB NEWS UZ", fill=(180, 200, 220), font=font_brand)

        # Category Badge
        bbox_b = draw.textbbox((0, 0), badge_text, font=font_badge)
        bw = bbox_b[2] - bbox_b[0] + 36
        draw.rounded_rectangle([width - 50 - bw, 36, width - 50, 76], radius=6, fill=(15, 25, 38), outline=accent_color, width=2)
        draw.text((width - 50 - bw + 18, 44), badge_text, fill=accent_color, font=font_badge)

        # Main Title (wrapped)
        words = title.split()
        lines: List[str] = []
        cur_line = ""
        for w in words:
            test_line = f"{cur_line} {w}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font_title)
            if (bbox[2] - bbox[0]) < 1080:
                cur_line = test_line
            else:
                if cur_line:
                    lines.append(cur_line)
                cur_line = w
        if cur_line:
            lines.append(cur_line)

        title_y = 120
        for l in lines[:3]:
            draw.text((50, title_y), l, fill=(255, 255, 255), font=font_title)
            title_y += 56

        # Separator line
        draw.line([(50, title_y + 15), (width - 50, title_y + 15)], fill=(35, 48, 70), width=2)

        # Content Card / Highlights
        content_y = title_y + 35
        pts = highlights or []
        if not pts and summary:
            # Split summary into short chunks
            pts = [s.strip() for s in summary.replace("•", "").split(". ") if len(s.strip()) > 10][:4]

        if pts:
            draw.rounded_rectangle([50, content_y, width - 50, height - 85], radius=10, fill=(16, 22, 34), outline=(32, 44, 66), width=1)
            py = content_y + 24
            for pt in pts[:4]:
                clean_p = pt.strip().rstrip(".")
                if len(clean_p) > 95:
                    clean_p = clean_p[:92] + "..."
                draw.text((80, py), f"•  {clean_p}", fill=(215, 225, 235), font=font_bullet)
                py += 44
        elif summary:
            draw.rounded_rectangle([50, content_y, width - 50, height - 85], radius=10, fill=(16, 22, 34), outline=(32, 44, 66), width=1)
            draw.text((80, content_y + 30), summary[:240], fill=(210, 220, 230), font=font_summary)

        # Footer
        draw.text((50, height - 50), "Mobile Legends: Bang Bang • O‘zbekiston Rasmiy Yangiliklar Portali", fill=(100, 130, 150), font=font_brand)

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=92)
        return buffer.getvalue()

    @classmethod
    async def download_and_optimize(cls, image_url: str) -> Optional[bytes]:
        """
        Download image from URL with browser headers and optimize for Telegram.
        Supports standard JPG/PNG, WEBP, and CDN proxy urls.
        """
        if not image_url or not image_url.strip():
            return None

        # Clean relative or double encoded urls
        clean_url = image_url.strip()
        if clean_url.startswith("//"):
            clean_url = f"https:{clean_url}"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://mobilelegends.com/"
        }

        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, verify=False, headers=headers) as client:
                resp = await client.get(clean_url)
                if resp.status_code == 200 and resp.content:
                    img = Image.open(io.BytesIO(resp.content))
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    # Scale down if very large, preserve aspect ratio
                    if img.width > 1920 or img.height > 1080:
                        img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                    out = io.BytesIO()
                    img.save(out, format="JPEG", quality=88, optimize=True)
                    return out.getvalue()
                else:
                    logger.warning(f"Download image returned HTTP {resp.status_code} for {clean_url[:60]}")
        except Exception as e:
            logger.warning(f"Failed to download/optimize image from {clean_url[:60]}: {e}")
        return None
