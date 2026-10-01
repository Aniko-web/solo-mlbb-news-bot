from app.utils.hashing import generate_content_hash, normalize_text


def test_normalize_text():
    raw = "  <p>Mobile  Legends: <b>Bang Bang</b> \n Update! </p> "
    normalized = normalize_text(raw)
    assert "<" not in normalized
    assert ">" not in normalized
    assert "mobile legends: bang bang update!" == normalized


def test_content_hash_consistency():
    h1 = generate_content_hash(
        title="Patch Notes 1.9.20",
        content="Fanny buffed and Hayabusa damage increased",
        source_url="https://m.mobilelegends.com/en/news/patch-notes-1-9-20?ref=telegram"
    )
    h2 = generate_content_hash(
        title="Patch Notes 1.9.20 ",
        content="Fanny buffed and Hayabusa damage increased ",
        source_url="https://m.mobilelegends.com/en/news/patch-notes-1-9-20#comments"
    )
    # Different query/fragment, same canonical content
    assert h1 == h2


def test_content_hash_different():
    h1 = generate_content_hash(title="Patch 1.9.20", content="Fanny buff", source_url="https://a.com")
    h2 = generate_content_hash(title="Patch 1.9.22", content="Ling nerf", source_url="https://a.com")
    assert h1 != h2
