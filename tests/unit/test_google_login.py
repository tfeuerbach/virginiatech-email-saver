from web.services.google_login import normalise_duo_code


def test_normalise_duo_code_accepts_three_digits():
    assert normalise_duo_code("443") == "443"


def test_normalise_duo_code_strips_whitespace():
    assert normalise_duo_code(" 443 ") == "443"


def test_normalise_duo_code_rejects_letters():
    assert normalise_duo_code("abc") is None


def test_normalise_duo_code_rejects_too_short():
    assert normalise_duo_code("12") is None


def test_normalise_duo_code_rejects_empty():
    assert normalise_duo_code("") is None
