"""External USD/KRW exchange-rate data source contract (SPEC-ORDER-022)."""

import decimal
import json
import urllib.error
import urllib.request
from datetime import date
from decimal import Decimal

REQUEST_TIMEOUT = 30

_FRANKFURTER_URL_TEMPLATE = "https://api.frankfurter.dev/v1/{date}?base=USD&symbols=KRW"

# M8 live-backfill incident (2026-08-15): Frankfurter returns HTTP 403 for
# the stdlib default User-Agent ("Python-urllib/3.x"). Confirmed live on
# the deployment machine: Request(url) -> 403, Request(url, headers=
# {"User-Agent": USER_AGENT}) -> 200. No mocked test exercises the real
# HTTP layer (all tests mock urllib.request.urlopen, per D8), so this was
# structurally invisible until the live call -- REQ-XRATE-002 now requires
# a non-default User-Agent explicitly for this reason.
USER_AGENT = "scm-v2/1.0"


class ExchangeRateFetchError(Exception):
    """Raised when the USD/KRW rate for a given date cannot be retrieved."""


# @MX:NOTE: [AUTO] fetch_usd_krw_rate is the single point of contact with an
# external exchange-rate source. REQ-XRATE-003: the date used to key a
# fetched rate is the one echoed in the response body, not the date that
# was requested -- Frankfurter returns the nearest prior publication date
# (and echoes that date) when the requested date is not itself a
# publication day. REQ-XRATE-004: swapping the data source (e.g. to Korea
# Eximbank's official basic rate) requires only rewriting this function to
# the same signature/exception contract; sync_exchange_rates is unaffected.
# @MX:ANCHOR: [AUTO] fetch_usd_krw_rate -- sole external exchange-rate contact point.
# @MX:REASON: REQ-XRATE-004 extension contract -- any future data source
# (e.g. Korea Eximbank) replaces only this function's body, keeping the same
# signature and exception contract, so sync_exchange_rates never changes.
def fetch_usd_krw_rate(request_date: date) -> tuple[date, Decimal]:
    """Fetch the USD->KRW rate for request_date from Frankfurter.

    Returns (published_date, rate). published_date is the date echoed back
    in the response body (REQ-XRATE-003) -- it may differ from
    request_date, since Frankfurter echoes the nearest prior publication
    date when request_date is not itself a publication day.

    Raises ExchangeRateFetchError on any failure: network error, non-200
    HTTP response, malformed JSON, a response body missing the "date" or
    "KRW" key, or a "date"/"KRW" value present but not parseable as an
    ISO date / decimal number respectively (design decision F -- all
    failure modes are normalized to this one exception type).
    """
    url = _FRANKFURTER_URL_TEMPLATE.format(date=request_date.isoformat())
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise ExchangeRateFetchError(f"{request_date}: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ExchangeRateFetchError(f"{request_date}: network error ({exc.reason})") from exc
    except json.JSONDecodeError as exc:
        raise ExchangeRateFetchError(f"{request_date}: malformed JSON response") from exc

    try:
        published_date = date.fromisoformat(body["date"])
        rate = Decimal(str(body["rates"]["KRW"]))
    except KeyError as exc:
        raise ExchangeRateFetchError(
            f"{request_date}: response missing expected key {exc}"
        ) from exc
    except (ValueError, TypeError, decimal.InvalidOperation) as exc:
        # F1: fields present but their values are malformed -- e.g.
        # "date": "not-a-date" (ValueError from date.fromisoformat) or
        # "rates": {"KRW": null} (decimal.InvalidOperation from Decimal(str(None))).
        raise ExchangeRateFetchError(
            f"{request_date}: response contains an invalid date or rate value ({exc})"
        ) from exc

    return published_date, rate
