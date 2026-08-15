"""Unit tests for order.exchange_rates.fetch_usd_krw_rate (SPEC-ORDER-022).

Traces: REQ-XRATE-001, REQ-XRATE-002, REQ-XRATE-003. U1~U6 per plan.md M1.

Mocking note (D8): this repository has no prior urlopen-mocking precedent
(test_shopify_orders.py mocks the module-level _get_with_headers helper
instead). urlopen is a context manager whose .read() returns bytes, so the
mock must be shaped as
mock_urlopen.return_value.__enter__.return_value.read.return_value = b"...".
"""

import urllib.error
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from order.exchange_rates import ExchangeRateFetchError, fetch_usd_krw_rate


def test_u1_success_echoed_date_matches_requested_date():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            b'{"amount":1.0,"base":"USD","date":"2026-08-13","rates":{"KRW":1420.29}}'
        )
        result = fetch_usd_krw_rate(date(2026, 8, 13))

    assert result == (date(2026, 8, 13), Decimal("1420.29"))


def test_u2_echoed_date_differs_from_requested_date():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            b'{"date":"2026-06-18","rates":{"KRW":1538.89}}'
        )
        published_date, rate = fetch_usd_krw_rate(date(2026, 6, 20))

    assert published_date == date(2026, 6, 18)
    assert published_date != date(2026, 6, 20)
    assert rate == Decimal("1538.89")


def test_u3_url_error_raises_contract_exception():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.URLError("Name or service not known")
        with pytest.raises(ExchangeRateFetchError):
            fetch_usd_krw_rate(date(2026, 7, 1))


def test_u4_http_error_raises_contract_exception():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://api.frankfurter.dev/v1/2026-07-01", 500, "Internal Server Error", {}, None
        )
        with pytest.raises(ExchangeRateFetchError):
            fetch_usd_krw_rate(date(2026, 7, 1))


def test_u5_malformed_json_raises_contract_exception():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"not json"
        with pytest.raises(ExchangeRateFetchError):
            fetch_usd_krw_rate(date(2026, 7, 1))


def test_u6_missing_krw_key_raises_contract_exception():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            b'{"date":"2026-07-01","rates":{}}'
        )
        with pytest.raises(ExchangeRateFetchError):
            fetch_usd_krw_rate(date(2026, 7, 1))


def test_u7_malformed_date_field_raises_contract_exception():
    """F1: "date" key present but its value is not a valid ISO date string."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            b'{"date":"not-a-date","rates":{"KRW":1420.29}}'
        )
        with pytest.raises(ExchangeRateFetchError):
            fetch_usd_krw_rate(date(2026, 7, 1))


def test_u8_null_krw_rate_raises_contract_exception():
    """F1: "KRW" key present but its value is null (None), not a number."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            b'{"date":"2026-07-01","rates":{"KRW":null}}'
        )
        with pytest.raises(ExchangeRateFetchError):
            fetch_usd_krw_rate(date(2026, 7, 1))
