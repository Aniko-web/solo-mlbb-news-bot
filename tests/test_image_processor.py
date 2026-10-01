import io
from PIL import Image
import pytest

from app.media.image_processor import ImageProcessor
from app.media.renderer import (
    render_match_graphic,
    render_match_result,
    render_match_upcoming,
    render_mpl_id_result,
    render_mpl_ph_result,
    render_mpl_id_upcoming,
    render_mpl_ph_upcoming,
)
from app.ai.formatter import PostFormatter


def test_generate_patch_graphic():
    graphic_bytes = ImageProcessor.generate_patch_graphic(
        version="1.9.20",
        buffs=["Fanny energy +1", "Hayabusa damage +15%"],
        nerfs=["Ling cooldown +7s", "Nolan rift energy -10%"]
    )
    assert isinstance(graphic_bytes, bytes)
    assert len(graphic_bytes) > 5000

    img = Image.open(io.BytesIO(graphic_bytes))
    assert img.size == (1080, 720)
    assert img.format == "JPEG"


def test_render_patch_recap_infographic():
    """Verify ImageProcessor.render_patch_recap generates 1080x960 recap infographic."""
    patch_data = {
        "server": "ORIGINAL SERVER",
        "version": "2.2.16",
        "buffs": ["Kalea", "Cici", "Alpha", "Kagura", "Edith", "Karina", "Kaja"],
        "nerfs": ["Melissa", "Miya", "Hanabi", "Yi Sun-shin", "Paquito"],
        "adjustments": ["Aulus", "Argus", "Aldous", "Lukas", "Odette", "Sun", "Marcel", "Kadita", "Hylos"],
        "revamps": ["Masha", "Bruno"]
    }
    png_bytes = ImageProcessor.render_patch_recap(patch_data)
    assert isinstance(png_bytes, bytes)
    assert len(png_bytes) > 10000

    img = Image.open(io.BytesIO(png_bytes))
    assert img.size == (1080, 960)
    assert img.format == "PNG"


def test_generate_mpl_matchup_graphic_id():
    """Verify ImageProcessor auto-routes MPL ID to 1200x675 PNG."""
    graphic_bytes = ImageProcessor.generate_mpl_matchup_graphic(
        league="MPL ID",
        team_a="RRQ",
        team_b="ONIC",
        score_a=2,
        score_b=1,
        matches=[{
            "mvp": "Skylar",
            "week": 4,
            "date": "29 SEPTEMBER 2026",
            "status": "FINAL"
        }]
    )
    assert isinstance(graphic_bytes, bytes)
    assert len(graphic_bytes) > 10000

    img = Image.open(io.BytesIO(graphic_bytes))
    assert img.size == (1200, 675)
    assert img.format == "PNG"


def test_generate_mpl_matchup_graphic_ph():
    """Verify ImageProcessor auto-routes MPL PH to 1200x675 PNG."""
    graphic_bytes = ImageProcessor.generate_mpl_matchup_graphic(
        league="MPL Philippines",
        team_a="FNOP",
        team_b="TLPH",
        score_a=2,
        score_b=1,
        matches=[{
            "mvp": "Kelra",
            "week": 4,
            "date": "SEPTEMBER 29",
            "status": "FINAL"
        }]
    )
    assert isinstance(graphic_bytes, bytes)
    assert len(graphic_bytes) > 10000

    img = Image.open(io.BytesIO(graphic_bytes))
    assert img.size == (1200, 675)
    assert img.format == "PNG"


def test_mpl_id_dedicated_result_renderer():
    """Test dedicated MPL ID result template."""
    data = {
        "league": "MPL ID",
        "season": "Season 17",
        "week": 4,
        "team_a": "RRQ",
        "team_b": "ONIC",
        "score_a": 2,
        "score_b": 1,
        "status": "FINAL",
        "mvp": "Skylar",
        "date": "2026-09-29",
        "time": "15:00"
    }
    raw_png = render_mpl_id_result(data)
    assert isinstance(raw_png, bytes)
    img = Image.open(io.BytesIO(raw_png))
    assert img.size == (1200, 675)
    assert img.format == "PNG"


def test_mpl_ph_dedicated_result_renderer():
    """Test dedicated MPL PH result template."""
    data = {
        "league": "MPL PH",
        "season": "Season 14",
        "week": 4,
        "team_a": "FNOP",
        "team_b": "TLPH",
        "score_a": 2,
        "score_b": 1,
        "status": "FINAL",
        "mvp": "Kelra",
        "date": "2026-09-29",
        "time": "17:00"
    }
    raw_png = render_mpl_ph_result(data)
    assert isinstance(raw_png, bytes)
    img = Image.open(io.BytesIO(raw_png))
    assert img.size == (1200, 675)
    assert img.format == "PNG"


def test_upcoming_match_renderers():
    """Test upcoming match graphics for both MPL ID and MPL PH."""
    data_id = {
        "league": "MPL ID",
        "season": "Season 17",
        "week": 4,
        "team_a": "RRQ",
        "team_b": "ONIC",
        "status": "UPCOMING",
        "time": "15:00",
        "date": "29 SEPTEMBER",
        "series": "BO3"
    }
    png_id = render_mpl_id_upcoming(data_id)
    img_id = Image.open(io.BytesIO(png_id))
    assert img_id.size == (1200, 675)
    assert img_id.format == "PNG"

    data_ph = {
        "league": "MPL PH",
        "season": "Season 14",
        "week": 4,
        "team_a": "FNOP",
        "team_b": "TLPH",
        "status": "UPCOMING",
        "time": "17:00",
        "date": "SEPTEMBER 29",
        "series": "BO3"
    }
    png_ph = render_mpl_ph_upcoming(data_ph)
    img_ph = Image.open(io.BytesIO(png_ph))
    assert img_ph.size == (1200, 675)
    assert img_ph.format == "PNG"


def test_missing_fields_graceful():
    """Ensure missing MVP, logos, or empty metadata don't crash."""
    minimal_data = {
        "league": "MPL ID",
        "team_a": "Unknown A",
        "team_b": "Unknown B",
        "score_a": 1,
        "score_b": 0,
        "status": "FINAL"
    }
    # No mvp, no date, no week, no season
    png = render_match_graphic(minimal_data)
    img = Image.open(io.BytesIO(png))
    assert img.size == (1200, 675)
    assert img.format == "PNG"


def test_various_match_statuses_and_series():
    """Support LIVE, POSTPONED, CANCELLED, and BO1/BO3/BO5."""
    for st in ["LIVE", "POSTPONED", "CANCELLED"]:
        data = {
            "league": "MPL PH",
            "team_a": "APBR",
            "team_b": "OMG",
            "score_a": 1,
            "score_b": 1,
            "status": st,
            "series": "BO5"
        }
        png = render_match_graphic(data)
        img = Image.open(io.BytesIO(png))
        assert img.size == (1200, 675)

    bo5_data = {
        "league": "MPL ID",
        "team_a": "EVOS",
        "team_b": "BTR",
        "score_a": 3,
        "score_b": 2,
        "status": "FINAL",
        "series": "BO5"
    }
    png_bo5 = render_match_result(bo5_data)
    assert Image.open(io.BytesIO(png_bo5)).size == (1200, 675)


def test_uzbek_caption_formatting():
    """Ensure Uzbek captions strictly match user prompt requirements."""
    id_data = {
        "league": "MPL ID",
        "team_a": "RRQ",
        "team_b": "ONIC",
        "score_a": 2,
        "score_b": 1,
        "status": "FINAL",
        "mvp": "Skylar",
        "week": 4,
        "date": "29 September"
    }
    caption_id = PostFormatter.format_match_result_from_data(id_data)
    assert "🇮🇩 <b>MPL ID — NATIJA</b>" in caption_id
    assert "RRQ 2 — 1 ONIC" in caption_id
    assert "⭐ <b>MVP:</b> Skylar" in caption_id
    assert "📌 Week 4" in caption_id
    assert "📅 29 September" in caption_id
    assert "#MPLID #MLBB" in caption_id

    ph_data = {
        "league": "MPL PH",
        "team_a": "FNOP",
        "team_b": "TLPH",
        "score_a": 2,
        "score_b": 1,
        "status": "FINAL",
        "mvp": "Kelra",
        "week": 4,
        "date": "September 29"
    }
    caption_ph = PostFormatter.format_match_result_from_data(ph_data)
    assert "🇵🇭 <b>MPL PH — NATIJA</b>" in caption_ph
    assert "FNOP 2 — 1 TLPH" in caption_ph
    assert "⭐ <b>MVP:</b> Kelra" in caption_ph
    assert "📌 Week 4" in caption_ph
    assert "📅 September 29" in caption_ph
    assert "#MPLPH #MLBB" in caption_ph


def test_uzbek_upcoming_caption_formatting():
    """Ensure Uzbek upcoming match captions match formatting requirements."""
    id_data = {
        "league": "MPL ID",
        "team_a": "RRQ",
        "team_b": "ONIC",
        "time": "15:00",
        "date": "29 September",
        "week": 4,
        "series": "BO3"
    }
    cap_id = PostFormatter.format_match_upcoming_from_data(id_data)
    assert "🇮🇩 <b>MPL ID — KUTILAYOTGAN O‘YIN</b>" in cap_id
    assert "RRQ 🆚 ONIC" in cap_id
    assert "15:00" in cap_id
    assert "Week 4 • BO3" in cap_id
    assert "#MPLID #MLBB" in cap_id

    ph_data = {
        "league": "MPL PH",
        "team_a": "FNOP",
        "team_b": "TLPH",
        "time": "17:00",
        "date": "September 29",
        "week": 4,
        "series": "BO3"
    }
    cap_ph = PostFormatter.format_match_upcoming_from_data(ph_data)
    assert "🇵🇭 <b>MPL PH — KUTILAYOTGAN O‘YIN</b>" in cap_ph
    assert "FNOP 🆚 TLPH" in cap_ph
    assert "17:00" in cap_ph
    assert "Week 4 • BO3" in cap_ph
    assert "#MPLPH #MLBB" in cap_ph


def test_generate_news_graphic():
    """Ensure generate_news_graphic produces a valid 1200x675 broadcast JPEG card."""
    raw_jpg = ImageProcessor.generate_news_graphic(
        title="Yangi Starlight Skin: Aulus Starwake Corsair",
        category="SKIN",
        summary="Aulus qahramoni uchun yangi kosmik dizayndagi starlight skin taqdim etildi.",
        highlights=["300 olmos evaziga", "Eksklyuziv animatsiyalar", "Sentabr oyi mukofotlari"]
    )
    assert isinstance(raw_jpg, bytes)
    img = Image.open(io.BytesIO(raw_jpg))
    assert img.size == (1200, 675)
    assert img.format == "JPEG"


def test_publisher_caption_split():
    """Test caption splitting for Telegram's strict 1024 character limit."""
    from app.telegram.publisher import _split_caption

    short_text = "Qisqa post sarlavhasi va matni."
    cap, rest = _split_caption(short_text, max_len=1020)
    assert cap == short_text
    assert rest is None

    long_text = "Paragraph 1: MLBB yangiliklari.\n\n" + ("Batafsil matn qismi. " * 80)
    assert len(long_text) > 1024
    cap, rest = _split_caption(long_text, max_len=1020)
    assert len(cap) <= 1024
    assert rest is not None
    assert len(rest) > 0


def test_hero_and_event_formatters():
    """Test format_hero and format_event produce rich Uzbek Telegram markup."""
    hero_post = PostFormatter.format_hero(
        hero_name="Suyou",
        role="Qotil / Jangchi",
        description="Ikki xil ko'rinishga ega yangi qahramon.",
        skills=["Pichoq sakrashi", "Ruh zarbasi", "Yovuzlikni yo'qotuvchi"],
        source_url="https://m.mobilelegends.com"
    )
    assert "🦸 <b>YANGI QAHRAMON / REVAMP</b>" in hero_post
    assert "Suyou" in hero_post
    assert "Qotil / Jangchi" in hero_post
    assert "#MLBB #Hero" in hero_post

    event_post = PostFormatter.format_event(
        title="MLBB x Street Fighter 6 Collab",
        description="Capcom bilan hamkorlikdagi maxsus tadbir.",
        rewards=["Ryu skini", "Chun-Li avatar ramkasi"],
        duration="10-oktabrgacha",
        source_url="https://mlbbhub.com"
    )
    assert "🎉 <b>MAXSUS TADBIR (EVENT)</b>" in event_post
    assert "Street Fighter 6" in event_post
    assert "10-oktabrgacha" in event_post
    assert "#MLBB #Event" in event_post
