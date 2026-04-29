from app.services.utils import sha256_text, split_markdown


def test_sha256_text_stable():
    val1 = sha256_text("hotspot")
    val2 = sha256_text("hotspot")
    assert val1 == val2
    assert len(val1) == 64


def test_split_markdown_by_chunk_size():
    text = "a" * 2500
    chunks = split_markdown(text, chunk_size=1000)
    assert len(chunks) == 3
    assert len(chunks[0]) == 1000
    assert len(chunks[1]) == 1000
    assert len(chunks[2]) == 500
