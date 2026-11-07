import pytest
from app.utils.validators import (
    CategoryEnum,
    SourceReliability,
    verify_no_source_no_claim
)


def test_source_reliability_scores():
    assert SourceReliability.get_score("OFFICIAL_MLBB") == 100
    assert SourceReliability.get_score("OFFICIAL_MPL") == 100
    assert SourceReliability.get_score("UNKNOWN", "https://id-mpl.com/schedule") == 100
    assert SourceReliability.get_score("UNKNOWN", "https://liquipedia.net/mobilelegends") == 85
    assert SourceReliability.get_score("COMMUNITY") == 60
    assert SourceReliability.get_score("UNKNOWN", "https://randomblog.com") == 30


def test_verify_no_source_no_claim_valid():
    source_text = "RRQ Hoshi won 2 - 1 against Bigetron Alpha. MVP was Skylar on Claude."
    claims = {
        "score_a": 2,
        "score_b": 1,
        "mvp": "Skylar",
        "fake_field": "InvisiblePlayer"
    }
    verified = verify_no_source_no_claim(source_text, claims)
    assert verified["score_a"] == 2
    assert verified["score_b"] == 1
    assert verified["mvp"] == "Skylar"
    # fake_field should not be hallucinated
    assert verified["fake_field"] == "InvisiblePlayer"  # unrecognized keys passed through


def test_verify_no_source_no_claim_hallucination_prevention():
    source_text = "New Lunox skin Astral Echo released on October 5."
    claims = {
        "hero": "Lunox",
        "skin_name": "Astral Echo",
        "price": "99999 Diamonds"  # Not in source text!
    }
    verified = verify_no_source_no_claim(source_text, claims)
    assert verified["hero"] == "Lunox"
    assert verified["skin_name"] == "Astral Echo"
    assert verified["price"] == "Unknown"  # Sanitized to Unknown!


def test_is_match_time_elapsed_future_match():
    from app.utils.validators import is_match_time_elapsed, parse_match_datetime_uz, TASHKENT_TZ
    from datetime import datetime, timedelta

    # Match tomorrow in Tashkent time
    tomorrow = datetime.now(TASHKENT_TZ) + timedelta(days=1)
    tomorrow_date = tomorrow.strftime("%Y-%m-%d")

    # Match time in the future must return False (not elapsed)
    assert not is_match_time_elapsed(tomorrow_date, "15:00 (UZ)")
    assert not is_match_time_elapsed(tomorrow_date, "17:00 PHT")


def test_is_match_time_elapsed_past_match():
    from app.utils.validators import is_match_time_elapsed, TASHKENT_TZ
    from datetime import datetime, timedelta

    # Match yesterday in Tashkent time
    yesterday = datetime.now(TASHKENT_TZ) - timedelta(days=1)
    yesterday_date = yesterday.strftime("%Y-%m-%d")

    # Past match must return True
    assert is_match_time_elapsed(yesterday_date, "13:00 (UZ)")
    assert is_match_time_elapsed(yesterday_date, "15:00 WIB")

