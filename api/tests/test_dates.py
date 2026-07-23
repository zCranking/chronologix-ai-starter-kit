from datetime import date

from extraction.dates import extract_dates


def test_extract_dates_finds_iso_format():
    assert extract_dates("Visit occurred 2024-01-15.") == [date(2024, 1, 15)]


def test_extract_dates_finds_us_slash_format():
    assert extract_dates("Seen on 01/15/2024 for follow-up.") == [date(2024, 1, 15)]


def test_extract_dates_finds_month_name_format():
    assert extract_dates("Patient admitted January 15, 2024.") == [date(2024, 1, 15)]


def test_extract_dates_finds_abbreviated_month():
    assert extract_dates("Discharged Jan 15, 2024.") == [date(2024, 1, 15)]


def test_extract_dates_finds_multiple_dates_in_order():
    text = "Injury on 2024-01-01, treated 2024-01-15, released 2024-02-01."
    assert extract_dates(text) == [date(2024, 1, 1), date(2024, 1, 15), date(2024, 2, 1)]


def test_extract_dates_returns_empty_list_for_no_dates():
    assert extract_dates("No dates mentioned here at all.") == []


def test_extract_dates_skips_invalid_calendar_dates():
    assert extract_dates("Error code 2024-13-45 in the log.") == []


def test_extract_dates_orders_mixed_formats_by_position_in_text():
    text = "Injury on January 1, 2024, treated 2024-01-15, released 03/01/2024."
    assert extract_dates(text) == [date(2024, 1, 1), date(2024, 1, 15), date(2024, 3, 1)]
