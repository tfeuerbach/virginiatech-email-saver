from web.routes.dashboard_routes import normalise_phone


def test_ten_digit():
    assert normalise_phone("5551234567") == "+15551234567"


def test_with_country_code():
    assert normalise_phone("15551234567") == "+15551234567"


def test_formatted_parens():
    assert normalise_phone("(555) 123-4567") == "+15551234567"


def test_formatted_dashes():
    assert normalise_phone("555-123-4567") == "+15551234567"


def test_formatted_dots():
    assert normalise_phone("555.123.4567") == "+15551234567"


def test_plus_one_prefix():
    assert normalise_phone("+15551234567") == "+15551234567"


def test_too_short():
    assert normalise_phone("55512345") is None


def test_too_long():
    assert normalise_phone("155512345678") is None


def test_empty_string():
    assert normalise_phone("") is None


def test_letters_only():
    assert normalise_phone("abcdefghij") is None


def test_spaces():
    assert normalise_phone("555 123 4567") == "+15551234567"
