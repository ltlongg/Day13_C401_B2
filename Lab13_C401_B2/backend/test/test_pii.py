from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_passport() -> None:
    out = scrub_text("Passport B12345678 belongs to the student.")
    assert "B12345678" not in out
    assert "REDACTED_PASSPORT" in out


def test_scrub_address() -> None:
    out = scrub_text("Dia chi lien he: so 12 duong Nguyen Trai, quan 1, TP.HCM")
    assert "REDACTED_ADDRESS" in out
