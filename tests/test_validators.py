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
