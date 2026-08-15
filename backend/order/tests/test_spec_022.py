"""SPEC-ORDER-022: ExchangeRate table auto-sync + gap backfill.

Integration tests for the `sync_exchange_rates` management command.
T1~T12 map 1:1 to AC-XRATE-001~012 (acceptance.md, v1.1.0).

fetch_usd_krw_rate is mocked at the command module's namespace
("order.management.commands.sync_exchange_rates.fetch_usd_krw_rate") so no
real network call is made — this only works because the command imports the
function by name (`from order.exchange_rates import fetch_usd_krw_rate`,
D16). U1~U6 in test_exchange_rates.py already cover the contract function's
own failure-normalization behavior at the urlopen level.
"""

import io
from datetime import date, datetime
from datetime import timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext

from order.exchange_rates import ExchangeRateFetchError
from order.models import ExchangeRate, Order
from order.serializers import OrderDetailSerializer

pytestmark = pytest.mark.django_db

PATCH_TARGET = "order.management.commands.sync_exchange_rates.fetch_usd_krw_rate"

# AC-XRATE-005: absolute query count observed by running T5 against the
# correct (batch) implementation — not a guessed value (test_spec_018.py:64
# convention, per plan.md/acceptance.md). Observed directly (M4 GREEN,
# 2026-08-15): 4 queries per call_command run -- SAVEPOINT (pytest-django's
# nested-atomic wrapper, D7), the existence-check SELECT, the bulk_create
# INSERT, and RELEASE SAVEPOINT. Identical for N=3 and N=10.
SYNC_QUERY_COUNT = 4


# ---------------------------------------------------------------------------
# AC-XRATE-001 — T1: N=3 distinct dates, each stored with its own value
# ---------------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_t1_distinct_dates_stored_with_their_own_values(mock_fetch):
    values = {
        date(2026, 7, 1): Decimal("1500.00"),
        date(2026, 7, 2): Decimal("1501.00"),
        date(2026, 7, 3): Decimal("1502.00"),
    }
    mock_fetch.side_effect = lambda d: (d, values[d])

    call_command("sync_exchange_rates", "--start", "2026-07-01", "--end", "2026-07-03")

    assert (
        ExchangeRate.objects.filter(
            effective_date__in=[date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3)]
        ).count()
        == 3
    )
    for d, expected_rate in values.items():
        assert ExchangeRate.objects.get(effective_date=d).rate == expected_rate


# ---------------------------------------------------------------------------
# AC-XRATE-002 — T2: echoed date used for storage, not the requested date
# ---------------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_t2_echoed_date_used_for_storage_not_requested_date(mock_fetch):
    mock_fetch.return_value = (date(2026, 6, 18), Decimal("1538.89"))

    call_command("sync_exchange_rates", "--start", "2026-06-20", "--end", "2026-06-20")

    assert ExchangeRate.objects.filter(effective_date=date(2026, 6, 20)).exists() is False
    stored = ExchangeRate.objects.get(effective_date=date(2026, 6, 18))
    assert stored.rate == Decimal("1538.89")


# ---------------------------------------------------------------------------
# AC-XRATE-003 — T3: re-run idempotency when fetch returns identical values
# ---------------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_t3_rerun_with_identical_fetched_values_is_idempotent(mock_fetch):
    mock_fetch.return_value = (date(2026, 7, 10), Decimal("1510.00"))

    call_command("sync_exchange_rates", "--start", "2026-07-10", "--end", "2026-07-10")
    call_command("sync_exchange_rates", "--start", "2026-07-10", "--end", "2026-07-10")

    assert ExchangeRate.objects.filter(effective_date=date(2026, 7, 10)).count() == 1
    assert ExchangeRate.objects.get(effective_date=date(2026, 7, 10)).rate == Decimal("1510.00")


# ---------------------------------------------------------------------------
# AC-XRATE-004 — T4: existing/manually-corrected record is not overwritten
# even when the newly fetched value differs
# ---------------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_t4_existing_record_not_overwritten_with_different_fetched_value(mock_fetch):
    ExchangeRate.objects.create(effective_date=date(2026, 6, 25), rate=Decimal("1500.00"))
    mock_fetch.return_value = (date(2026, 6, 25), Decimal("1420.29"))

    call_command("sync_exchange_rates", "--start", "2026-06-25", "--end", "2026-06-25")

    assert ExchangeRate.objects.get(effective_date=date(2026, 6, 25)).rate == Decimal("1500.00")


# ---------------------------------------------------------------------------
# AC-XRATE-005 — T5: absolute query-count invariant across N=3 and N=10
# ---------------------------------------------------------------------------


def _run_and_capture_queries(start: str, end: str):
    with CaptureQueriesContext(connection) as ctx:
        call_command("sync_exchange_rates", "--start", start, "--end", end)
    return ctx.captured_queries


@patch(PATCH_TARGET)
def test_t5_query_count_invariant_across_n3_and_n10(mock_fetch):
    mock_fetch.side_effect = lambda d: (d, Decimal("1500.00") + Decimal(d.day))

    queries_x = _run_and_capture_queries("2026-09-01", "2026-09-03")  # N=3, fresh dates
    queries_y = _run_and_capture_queries("2026-09-10", "2026-09-19")  # N=10, fresh dates

    assert len(queries_x) == len(queries_y) == SYNC_QUERY_COUNT

    er_queries_x = [q for q in queries_x if "orders_exchangerate" in q["sql"]]
    er_queries_y = [q for q in queries_y if "orders_exchangerate" in q["sql"]]
    assert len(er_queries_x) == 2
    assert len(er_queries_y) == 2


# ---------------------------------------------------------------------------
# AC-XRATE-006 — T6: failure -> nonzero exit, no DB change, stderr reported
# ---------------------------------------------------------------------------


FAILURE_CASES = [
    ("network", "network error (Name or service not known)"),
    ("http500", "HTTP 500"),
    ("malformed_json", "malformed JSON response"),
    ("missing_krw_key", "response missing expected key 'KRW'"),
]


@pytest.mark.parametrize("case_id, reason", FAILURE_CASES)
@patch(PATCH_TARGET)
def test_t6_fetch_failure_nonzero_exit_no_db_change_stderr_reported(mock_fetch, case_id, reason):
    mock_fetch.side_effect = ExchangeRateFetchError(f"2026-07-20: {reason}")
    count_before = ExchangeRate.objects.count()
    stderr = io.StringIO()

    with pytest.raises(CommandError):
        call_command(
            "sync_exchange_rates",
            "--start", "2026-07-20",
            "--end", "2026-07-20",
            stderr=stderr,
        )

    assert ExchangeRate.objects.count() == count_before
    output = stderr.getvalue()
    assert "2026-07-20" in output
    assert reason in output


# ---------------------------------------------------------------------------
# AC-XRATE-007 — T7: partial failure preserves successful dates
# ---------------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_t7_partial_failure_preserves_successful_dates(mock_fetch):
    def side_effect(d):
        if d == date(2026, 7, 21):
            return (date(2026, 7, 21), Decimal("1600.00"))
        if d == date(2026, 7, 22):
            raise ExchangeRateFetchError("2026-07-22: network error (timeout)")
        return (date(2026, 7, 23), Decimal("1602.00"))

    mock_fetch.side_effect = side_effect

    with pytest.raises(CommandError):
        call_command("sync_exchange_rates", "--start", "2026-07-21", "--end", "2026-07-23")

    assert ExchangeRate.objects.get(effective_date=date(2026, 7, 21)).rate == Decimal("1600.00")
    assert ExchangeRate.objects.get(effective_date=date(2026, 7, 23)).rate == Decimal("1602.00")
    assert ExchangeRate.objects.filter(effective_date=date(2026, 7, 22)).exists() is False


# ---------------------------------------------------------------------------
# AC-XRATE-008 — T8: default range = next day after latest stored, today (UTC)
#
# DIVERGENCE FROM acceptance.md (recorded in spec.md HISTORY, v1.1.0
# implementation entry): acceptance.md specifies
# freeze_time("2026-06-21 23:30:00", tz_offset=9) as the discriminating
# fixture for REQ-XRATE-009 (timezone.localdate() vs datetime.date.today()).
# Verified by direct execution against freezegun 1.5.5 (the version pinned
# in this repo's poetry.lock) that this fixture CANNOT discriminate the two
# candidate implementations: FakeDate.today() (freezegun/api.py:338-341)
# and FakeDatetime.now(tz=X) (freezegun/api.py:400-407) both unconditionally
# add tz_offset to the frozen instant, regardless of whether an explicit
# `tz` is passed -- so date.today() and
# datetime.now(tz=utc).date() (== timezone.localdate() under
# TIME_ZONE="UTC") are byte-for-byte equal for every tz_offset value (0, 1,
# 9, -5 all checked interactively). This contradicts acceptance.md's stated
# verification claim for this exact fixture.
#
# This test instead mocks timezone.localdate() directly and leaves
# datetime.date.today() real (unpatched, pinned to the actual host clock,
# which will not coincidentally equal 2026-06-21 in test runs). This
# discriminates strictly *more* reliably than the freeze_time approach: a
# date.today()-using mutation would either call the real host "today" (far
# from the expected range) or never invoke the mocked timezone.localdate()
# at all -- both are directly asserted below. REQ-XRATE-007 (start = next
# day after latest stored) is unaffected by this issue and is verified
# exactly as specified.
# ---------------------------------------------------------------------------


@patch("order.management.commands.sync_exchange_rates.timezone.localdate")
@patch(PATCH_TARGET)
def test_t8_default_range_uses_next_day_and_utc_localdate(mock_fetch, mock_localdate):
    ExchangeRate.objects.create(effective_date=date(2026, 6, 18), rate=Decimal("1540.64"))
    mock_localdate.return_value = date(2026, 6, 21)
    mock_fetch.side_effect = lambda d: (d, Decimal("1500.00"))

    call_command("sync_exchange_rates")

    mock_localdate.assert_called_once()
    called_dates = {call_args.args[0] for call_args in mock_fetch.call_args_list}
    assert called_dates == {date(2026, 6, 19), date(2026, 6, 20), date(2026, 6, 21)}


# ---------------------------------------------------------------------------
# AC-XRATE-009 — T9: start after end -> no fetch, no write, exit 0
# ---------------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_t9_start_after_end_is_a_no_op_success(mock_fetch):
    count_before = ExchangeRate.objects.count()

    call_command("sync_exchange_rates", "--start", "2026-07-05", "--end", "2026-07-01")

    assert mock_fetch.call_count == 0
    assert ExchangeRate.objects.count() == count_before


# ---------------------------------------------------------------------------
# AC-XRATE-010 — T10: empty table + no --start -> CommandError
# ---------------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_t10_empty_table_without_start_raises_command_error(mock_fetch):
    ExchangeRate.objects.all().delete()

    with pytest.raises(CommandError):
        call_command("sync_exchange_rates", "--end", "2026-07-01")

    assert mock_fetch.call_count == 0


# ---------------------------------------------------------------------------
# AC-XRATE-011 — T11: regression — _get_exchange_rate picks up backfilled rate
# ---------------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_t11_regression_get_exchange_rate_returns_backfilled_rate(mock_fetch):
    mock_fetch.return_value = (date(2026, 8, 13), Decimal("1420.29"))

    call_command("sync_exchange_rates", "--start", "2026-08-13", "--end", "2026-08-13")

    order = Order.objects.create(
        shopify_order_id=990001,
        store_type="gimssine",
        financial_status="paid",
        total_price=Decimal("100.00"),
        shopify_created_at=datetime(2026, 8, 13, 3, 0, 0, tzinfo=dt_timezone.utc),
    )

    er = OrderDetailSerializer()._get_exchange_rate(order)

    assert er.effective_date == date(2026, 8, 13)
    assert er.rate == Decimal("1420.29")


# ---------------------------------------------------------------------------
# AC-XRATE-012 — T12: duplicate echoed publish date across a weekend
# collapses to exactly one row (audit D3, REQ-XRATE-024)
# ---------------------------------------------------------------------------


@patch(PATCH_TARGET)
def test_t12_duplicate_echoed_publish_date_across_weekend_collapses_to_one_row(mock_fetch):
    mock_fetch.side_effect = lambda d: (date(2026, 6, 19), Decimal("1530.00"))

    # F2: assert the application-level compression itself (REQ-XRATE-024),
    # not merely the post-write row count -- ignore_conflicts=True (design
    # decision G) would silently absorb an un-compressed 3-object list at
    # the DB level and make count()==1 pass even without REQ-XRATE-024's
    # dict-based dedup, so the row-count assertions alone have no
    # discriminating power over that specific mutation. wraps= keeps the
    # real bulk_create behavior (and the DB write) intact while recording
    # what it was called with.
    with patch(
        "order.models.ExchangeRate.objects.bulk_create",
        wraps=ExchangeRate.objects.bulk_create,
    ) as mock_bulk_create:
        call_command("sync_exchange_rates", "--start", "2026-06-19", "--end", "2026-06-21")

    assert mock_bulk_create.call_count == 1
    created_objects = mock_bulk_create.call_args.args[0]
    assert len(created_objects) == 1
    assert created_objects[0].effective_date == date(2026, 6, 19)

    assert ExchangeRate.objects.filter(effective_date=date(2026, 6, 19)).count() == 1
    assert ExchangeRate.objects.get(effective_date=date(2026, 6, 19)).rate == Decimal("1530.00")
    assert not ExchangeRate.objects.filter(
        effective_date__in=[date(2026, 6, 20), date(2026, 6, 21)]
    ).exists()
