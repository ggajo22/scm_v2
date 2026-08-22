"""SPEC-ORDER-029 (v0.5.0) — shared core function tests.

Covers AC-CANC-001~012 and AC-CANC-024 against the four new
shopify_orders.py functions: _chunked, fetch_order_status_by_ids,
open_candidate_order_ids, reconcile_order_status_for_ids, and the
_is_lock_wait_timeout helper's effect on chunk_failures.

Patch targets follow acceptance.md §0.2:
- group 1 (HTTP layer): order.shopify_orders._get_with_headers
- group 3 (chunk-loop level): order.shopify_orders.fetch_order_status_by_ids
"""

import inspect
from unittest.mock import patch

import pytest
from django.db.utils import OperationalError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from order.models import Order
from order.shopify_orders import (
    IDS_CHUNK_SIZE,
    _chunked,
    _is_lock_wait_timeout,
    fetch_order_status_by_ids,
    open_candidate_order_ids,
    reconcile_order_status_for_ids,
)

DOMAIN = "shop.myshopify.com"
TOKEN = "token123"


# ---------------------------------------------------------------------------
# AC-CANC-001 — new cancellation reflected
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_001_new_cancellation_reflected():
    Order.objects.create(shopify_order_id=90001, store_type="gimssine")
    with patch(
        "order.shopify_orders._get_with_headers",
        return_value=(
            {"orders": [{"id": 90001, "cancelled_at": "2026-08-10T03:00:00Z", "closed_at": None}]},
            {},
        ),
    ):
        reconcile_order_status_for_ids("gimssine", DOMAIN, TOKEN, [90001])

    order = Order.objects.get(shopify_order_id=90001)
    assert order.cancelled_at == parse_datetime("2026-08-10T03:00:00Z")


# ---------------------------------------------------------------------------
# AC-CANC-002 — new closure reflected
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_002_new_closure_reflected():
    Order.objects.create(shopify_order_id=90002, store_type="gimssine")
    with patch(
        "order.shopify_orders._get_with_headers",
        return_value=(
            {"orders": [{"id": 90002, "cancelled_at": None, "closed_at": "2026-08-09T12:00:00Z"}]},
            {},
        ),
    ):
        reconcile_order_status_for_ids("gimssine", DOMAIN, TOKEN, [90002])

    order = Order.objects.get(shopify_order_id=90002)
    assert order.closed_at == parse_datetime("2026-08-09T12:00:00Z")


# ---------------------------------------------------------------------------
# AC-CANC-003 — closed-only record: closed_at only, cancelled_at stays NULL
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_003_closed_only_record_does_not_cross_write_cancelled_at():
    Order.objects.create(shopify_order_id=90003, store_type="gimssine")
    with patch(
        "order.shopify_orders._get_with_headers",
        return_value=(
            {"orders": [{"id": 90003, "cancelled_at": None, "closed_at": "2026-08-05T00:00:00Z"}]},
            {},
        ),
    ):
        reconcile_order_status_for_ids("gimssine", DOMAIN, TOKEN, [90003])

    order = Order.objects.get(shopify_order_id=90003)
    assert order.closed_at == parse_datetime("2026-08-05T00:00:00Z")
    assert order.cancelled_at is None


# ---------------------------------------------------------------------------
# AC-CANC-004 — cancelled-only record: cancelled_at only, closed_at stays NULL (symmetric)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_004_cancelled_only_record_does_not_cross_write_closed_at():
    Order.objects.create(shopify_order_id=90004, store_type="gimssine")
    with patch(
        "order.shopify_orders._get_with_headers",
        return_value=(
            {"orders": [{"id": 90004, "cancelled_at": "2026-08-06T00:00:00Z", "closed_at": None}]},
            {},
        ),
    ):
        reconcile_order_status_for_ids("gimssine", DOMAIN, TOKEN, [90004])

    order = Order.objects.get(shopify_order_id=90004)
    assert order.cancelled_at == parse_datetime("2026-08-06T00:00:00Z")
    assert order.closed_at is None


# ---------------------------------------------------------------------------
# AC-CANC-005 — locally-unmatched order skipped without exception, sibling
# order in the same chunk continues to be processed (v0.3.0 discrimination
# recovery — exception must NOT be swallowed by the chunk-level except)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_005_unmatched_order_skipped_sibling_still_processed():
    # 90005 intentionally has NO local Order row.
    Order.objects.create(shopify_order_id=90006, store_type="gimssine")

    with patch(
        "order.shopify_orders.fetch_order_status_by_ids",
        return_value=[
            {"id": 90005, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None},
            {"id": 90006, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None},
        ],
    ):
        result = reconcile_order_status_for_ids("gimssine", DOMAIN, TOKEN, [90005, 90006])

    assert not any(c["shopify_order_id"] == 90005 for c in result["changed"])
    assert Order.objects.filter(shopify_order_id=90005).exists() is False
    assert result["chunk_failures"] == []
    assert Order.objects.get(shopify_order_id=90006).cancelled_at == parse_datetime("2026-08-01T00:00:00Z")


# ---------------------------------------------------------------------------
# AC-CANC-006 — request URL includes status=any, ids=, fields=, limit=
# ---------------------------------------------------------------------------


def test_ac_cancc_006_request_url_includes_all_required_params():
    with patch(
        "order.shopify_orders._get_with_headers",
        return_value=({"orders": []}, {}),
    ) as mock_get:
        fetch_order_status_by_ids(DOMAIN, TOKEN, [90006, 90007])

    path = mock_get.call_args.args[2]
    assert "status=any" in path
    assert "ids=90006,90007" in path
    assert "fields=id,cancelled_at,closed_at" in path
    assert "limit=250" in path


# ---------------------------------------------------------------------------
# AC-CANC-007 — chunking helper respects 250 cap, default chunk_size == 250
# ---------------------------------------------------------------------------


def test_ac_cancc_007_chunking_respects_cap_and_default_is_250():
    ids = list(range(1000000000000, 1000000000260))  # 260 13-digit ids
    chunks = list(_chunked(ids, 250))

    assert len(chunks[0]) == 250
    assert len(chunks[1]) == 10
    assert chunks[0] + chunks[1] == ids

    joined = ",".join(str(i) for i in chunks[0])
    assert len(joined) < 4000

    assert IDS_CHUNK_SIZE == 250
    assert inspect.signature(reconcile_order_status_for_ids).parameters["chunk_size"].default == IDS_CHUNK_SIZE


# ---------------------------------------------------------------------------
# AC-CANC-008 — every chunk is processed, including the last one
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_008_all_chunks_processed_including_last():
    Order.objects.create(shopify_order_id=900081, store_type="gimssine")
    Order.objects.create(shopify_order_id=900082, store_type="gimssine")
    Order.objects.create(shopify_order_id=900083, store_type="gimssine")

    def side_effect(domain, token, shopify_order_ids):
        ids = set(shopify_order_ids)
        if ids == {900081, 900082}:
            return [
                {"id": 900081, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None},
                {"id": 900082, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None},
            ]
        if ids == {900083}:
            return [{"id": 900083, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None}]
        raise AssertionError(f"unexpected chunk: {ids}")

    with patch("order.shopify_orders.fetch_order_status_by_ids", side_effect=side_effect):
        reconcile_order_status_for_ids(
            "gimssine", DOMAIN, TOKEN, [900081, 900082, 900083], chunk_size=2
        )

    expected = parse_datetime("2026-08-01T00:00:00Z")
    assert Order.objects.get(shopify_order_id=900081).cancelled_at == expected
    assert Order.objects.get(shopify_order_id=900082).cancelled_at == expected
    assert Order.objects.get(shopify_order_id=900083).cancelled_at == expected


# ---------------------------------------------------------------------------
# AC-CANC-009 — defensive: unexpected Link header is still followed
# ---------------------------------------------------------------------------


def test_ac_cancc_009_unexpected_link_header_followed():
    link_with_next = (
        '<https://shop.myshopify.com/admin/api/2024-10/orders.json?'
        'limit=250&page_info=xyz>; rel="next"'
    )

    def side_effect(domain, token, path):
        if "page_info=xyz" in path:
            return {"orders": [{"id": 900092, "cancelled_at": None, "closed_at": None}]}, {}
        return (
            {"orders": [{"id": 900091, "cancelled_at": None, "closed_at": None}]},
            {"Link": link_with_next},
        )

    with patch("order.shopify_orders._get_with_headers", side_effect=side_effect):
        records = fetch_order_status_by_ids(DOMAIN, TOKEN, [900091, 900092])

    returned_ids = {r["id"] for r in records}
    assert returned_ids == {900091, 900092}


# ---------------------------------------------------------------------------
# AC-CANC-010 — reconciled orders auto-shrink from the candidate set, and
# candidate sets are scoped per-store
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_010_reconciled_order_leaves_candidate_set_store_scoped():
    Order.objects.create(shopify_order_id=90010, store_type="gimssine")
    Order.objects.create(shopify_order_id=900102, store_type="etoile")

    before = open_candidate_order_ids("gimssine", closed_grace_days=None)
    assert 90010 in before

    with patch(
        "order.shopify_orders._get_with_headers",
        return_value=(
            {"orders": [{"id": 90010, "cancelled_at": "2026-08-11T00:00:00Z", "closed_at": None}]},
            {},
        ),
    ):
        reconcile_order_status_for_ids("gimssine", DOMAIN, TOKEN, [90010])

    order = Order.objects.get(shopify_order_id=90010)
    assert order.cancelled_at == parse_datetime("2026-08-11T00:00:00Z")

    after_gimssine = open_candidate_order_ids("gimssine", closed_grace_days=None)
    assert 90010 not in after_gimssine

    after_etoile = open_candidate_order_ids("etoile", closed_grace_days=None)
    assert 90010 not in after_etoile


# ---------------------------------------------------------------------------
# AC-CANC-011 — closed_grace_days window: recent closures included, old
# closures excluded (bounded mode); unbounded mode includes both
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_011_closed_grace_days_window_recent_in_old_out():
    now = timezone.now()
    Order.objects.create(shopify_order_id=90011001, store_type="gimssine", closed_at=None)
    Order.objects.create(
        shopify_order_id=90011002, store_type="gimssine", closed_at=now - timezone.timedelta(days=10)
    )
    Order.objects.create(
        shopify_order_id=90011003, store_type="gimssine", closed_at=now - timezone.timedelta(days=60)
    )

    bounded = open_candidate_order_ids("gimssine", closed_grace_days=30)
    assert 90011001 in bounded
    assert 90011002 in bounded
    assert 90011003 not in bounded

    unbounded = open_candidate_order_ids("gimssine", closed_grace_days=None)
    assert 90011001 in unbounded
    assert 90011002 in unbounded
    assert 90011003 in unbounded


# ---------------------------------------------------------------------------
# AC-CANC-012 — ids not returned by Shopify are reported in missing_ids
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_012_missing_id_reported_and_sibling_still_processed():
    Order.objects.create(shopify_order_id=900121, store_type="gimssine")
    Order.objects.create(shopify_order_id=900122, store_type="gimssine")

    with patch(
        "order.shopify_orders.fetch_order_status_by_ids",
        return_value=[{"id": 900121, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None}],
    ):
        result = reconcile_order_status_for_ids("gimssine", DOMAIN, TOKEN, [900121, 900122])

    assert 900122 in result["missing_ids"]
    assert Order.objects.get(shopify_order_id=900121).cancelled_at == parse_datetime("2026-08-01T00:00:00Z")


# ---------------------------------------------------------------------------
# AC-CANC-024 — MySQL lock-wait-timeout exceptions are distinguished from
# other exceptions in chunk_failures via lock_timeout
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_024_lock_wait_timeout_classified_separately():
    Order.objects.create(shopify_order_id=900241, store_type="gimssine")
    Order.objects.create(shopify_order_id=900242, store_type="gimssine")

    def side_effect(domain, token, shopify_order_ids):
        ids = list(shopify_order_ids)
        if ids == [900241]:
            raise OperationalError("(1205, 'Lock wait timeout exceeded; try restarting transaction')")
        if ids == [900242]:
            raise ValueError("malformed response")
        raise AssertionError(f"unexpected chunk: {ids}")

    with patch("order.shopify_orders.fetch_order_status_by_ids", side_effect=side_effect):
        result = reconcile_order_status_for_ids(
            "gimssine", DOMAIN, TOKEN, [900241, 900242], chunk_size=1
        )

    assert len(result["chunk_failures"]) == 2
    by_ids = {tuple(cf["ids"]): cf for cf in result["chunk_failures"]}
    assert by_ids[(900241,)]["lock_timeout"] is True
    assert by_ids[(900242,)]["lock_timeout"] is False


# ---------------------------------------------------------------------------
# evaluator-active finding #1 (BLOCKING) — _is_lock_wait_timeout() must not
# classify by message substring alone. An unrelated exception TYPE whose
# message happens to contain "1205" must NOT be treated as a lock timeout;
# only a genuine django.db.utils.OperationalError carrying that code should.
# ---------------------------------------------------------------------------


def test_is_lock_wait_timeout_ignores_non_operational_error_with_matching_digits():
    """A non-OperationalError exception (e.g. KeyError/ValueError) whose
    string representation happens to contain "1205" must classify as False —
    otherwise a real bug (KeyError, ValueError, ...) that happens to mention
    that digit sequence would be silently swallowed as a self-healing lock
    wait, exactly the ExchangeRate failure mode spec.md §1.2/D10 warns about.
    """
    assert _is_lock_wait_timeout(ValueError("record 1205 not found")) is False
    assert _is_lock_wait_timeout(KeyError("1205")) is False


def test_is_lock_wait_timeout_true_for_genuine_operational_error_1205():
    """A genuine OperationalError carrying MySQL error code 1205 must still
    classify as True — the fix must not regress the true-positive case."""
    assert (
        _is_lock_wait_timeout(
            OperationalError(1205, "Lock wait timeout exceeded; try restarting transaction")
        )
        is True
    )


# ---------------------------------------------------------------------------
# evaluator-active finding #2 (MEDIUM) — the change-detection gate
# (`if order.cancelled_at != new_cancelled or order.closed_at != new_closed`)
# has zero AC coverage: mutating it to `if True:` still passed every test.
# A second reconciliation over already-reconciled data must report an empty
# `changed` list — otherwise every cycle reports every candidate as changed,
# destroying the signal-vs-noise value of the command's output.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_second_reconciliation_over_unchanged_data_reports_no_changes():
    Order.objects.create(shopify_order_id=90026, store_type="gimssine")
    mocked_response = (
        {"orders": [{"id": 90026, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None}]},
        {},
    )

    with patch("order.shopify_orders._get_with_headers", return_value=mocked_response):
        first = reconcile_order_status_for_ids("gimssine", DOMAIN, TOKEN, [90026])
        assert len(first["changed"]) == 1

        second = reconcile_order_status_for_ids("gimssine", DOMAIN, TOKEN, [90026])

    assert second["changed"] == []
