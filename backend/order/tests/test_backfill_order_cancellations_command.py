"""SPEC-ORDER-029 (v0.5.0) — backfill_order_cancellations management command
tests. Covers AC-CANC-019~023 (5 cases).

Patch targets follow acceptance.md §0.2:
- group 1 (write-result assertions): order.shopify_orders._get_with_headers
- group 4 (call-argument capture):
  order.management.commands.backfill_order_cancellations.open_candidate_order_ids
"""

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils.dateparse import parse_datetime

from order.models import LineItem, Order, PurchaseOrder, Refund, ShippingLine
from order.shopify_orders import open_candidate_order_ids

_GET_HEADERS_TARGET = "order.shopify_orders._get_with_headers"
_OPEN_CANDIDATE_TARGET = (
    "order.management.commands.backfill_order_cancellations.open_candidate_order_ids"
)
_FETCH_BY_IDS_TARGET = "order.shopify_orders.fetch_order_status_by_ids"


# ---------------------------------------------------------------------------
# AC-CANC-019 — backfill command passes closed_grace_days=None (unbounded)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_019_backfill_passes_closed_grace_days_none():
    with patch(_OPEN_CANDIDATE_TARGET, return_value=[]) as mock_candidates:
        call_command("backfill_order_cancellations", "--store", "gimssine")

    mock_candidates.assert_called_once_with("gimssine", closed_grace_days=None)


# ---------------------------------------------------------------------------
# AC-CANC-020 — existing unreflected cancellation (52-case type) is reflected
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_020_existing_unreflected_cancellation_reflected():
    Order.objects.create(shopify_order_id=90020, store_type="gimssine")

    with patch(
        _GET_HEADERS_TARGET,
        return_value=(
            {"orders": [{"id": 90020, "cancelled_at": "2026-07-01T00:00:00Z", "closed_at": None}]},
            {},
        ),
    ):
        call_command("backfill_order_cancellations", "--store", "gimssine")

    order = Order.objects.get(shopify_order_id=90020)
    assert order.cancelled_at == parse_datetime("2026-07-01T00:00:00Z")


# ---------------------------------------------------------------------------
# AC-CANC-021 — --dry-run writes nothing, but reports diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_021_dry_run_writes_nothing_but_reports():
    Order.objects.create(shopify_order_id=90021, store_type="gimssine")

    stdout = StringIO()
    with patch(
        _GET_HEADERS_TARGET,
        return_value=(
            {"orders": [{"id": 90021, "cancelled_at": "2026-07-02T00:00:00Z", "closed_at": None}]},
            {},
        ),
    ):
        call_command(
            "backfill_order_cancellations", "--store", "gimssine", "--dry-run", stdout=stdout
        )

    order = Order.objects.get(shopify_order_id=90021)
    assert order.cancelled_at is None

    output = stdout.getvalue()
    assert "90021" in output
    assert "would_change" in output


# ---------------------------------------------------------------------------
# AC-CANC-022 — manual fields + LineItem/ShippingLine/Refund fully preserved
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_022_manual_fields_and_related_rows_preserved():
    order = Order.objects.create(
        shopify_order_id=90022,
        store_type="gimssine",
        status="shipped",
        note="고객 특별 요청 메모",
        ready_to_ship=True,
    )
    li = LineItem.objects.create(
        order=order,
        shopify_line_item_id=70220,
        sku="ISBN-90022",
        quantity=1,
        logistics_status="shipment_confirmed",
        rack_number="A-7",
        received_quantity=2,
        purchase_status="in_stock",
        original_sku="9788901234567",
    )
    po = PurchaseOrder.objects.create(
        sku="ISBN-90022", title="Test", distributor="booxen", quantity=1, status="pending"
    )
    po.line_items.add(li)
    ShippingLine.objects.create(order=order, shopify_shipping_line_id=88022, title="Standard")
    Refund.objects.create(order=order, shopify_refund_id=99022, quantity=1)

    with patch(
        _GET_HEADERS_TARGET,
        return_value=(
            {"orders": [{"id": 90022, "cancelled_at": "2026-08-11T00:00:00Z", "closed_at": None}]},
            {},
        ),
    ):
        call_command("backfill_order_cancellations", "--store", "gimssine")

    order.refresh_from_db()
    li.refresh_from_db()
    assert order.cancelled_at == parse_datetime("2026-08-11T00:00:00Z")
    assert order.status == "shipped"
    assert order.note == "고객 특별 요청 메모"
    assert order.ready_to_ship is True

    assert li.logistics_status == "shipment_confirmed"
    assert li.rack_number == "A-7"
    assert li.received_quantity == 2
    assert li.purchase_status == "in_stock"
    assert li.original_sku == "9788901234567"
    assert list(li.purchase_orders.all()) == [po]

    assert ShippingLine.objects.filter(order=order).count() == 1
    assert Refund.objects.filter(order=order).count() == 1


# ---------------------------------------------------------------------------
# AC-CANC-023 — re-running backfill twice does not create duplicate rows or raise
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_023_idempotent_rerun_no_duplicates():
    Order.objects.create(shopify_order_id=90023, store_type="gimssine")

    with patch(
        _GET_HEADERS_TARGET,
        return_value=(
            {"orders": [{"id": 90023, "cancelled_at": "2026-07-03T00:00:00Z", "closed_at": None}]},
            {},
        ),
    ):
        call_command("backfill_order_cancellations", "--store", "gimssine")

        order = Order.objects.get(shopify_order_id=90023)
        assert order.cancelled_at == parse_datetime("2026-07-03T00:00:00Z")

        call_command("backfill_order_cancellations", "--store", "gimssine")

    order.refresh_from_db()
    assert order.cancelled_at == parse_datetime("2026-07-03T00:00:00Z")
    assert Order.objects.filter(shopify_order_id=90023).count() == 1


# ---------------------------------------------------------------------------
# AC-CANC-026 — store-level failure does not block other stores
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_026_store_level_failure_does_not_block_other():
    """Verify one store's failure is recorded and other store is processed.

    SPEC-ORDER-029 §8.4: One store's exception is caught, reported to stderr,
    and the loop continues to the next store. Positive evidence: etoile order
    is processed despite gimssine failure.
    """
    Order.objects.create(shopify_order_id=90241, store_type="etoile")

    def side_effect(store_type, closed_grace_days=None):
        if store_type == "gimssine":
            raise RuntimeError("shopify 500 on gimssine")
        return open_candidate_order_ids(store_type, closed_grace_days=closed_grace_days)

    with (
        patch(_OPEN_CANDIDATE_TARGET, side_effect=side_effect),
        patch(
            _GET_HEADERS_TARGET,
            return_value=(
                {"orders": [{"id": 90241, "cancelled_at": None, "closed_at": "2026-08-15T00:00:00Z"}]},
                {},
            ),
        ),
    ):
        with pytest.raises(CommandError):
            call_command("backfill_order_cancellations")

    # Positive evidence: etoile order WAS processed despite gimssine failure.
    order = Order.objects.get(shopify_order_id=90241)
    assert order.closed_at == parse_datetime("2026-08-15T00:00:00Z")


@pytest.mark.django_db
def test_ac_cancc_026_store_level_failure_on_stderr():
    """Verify store-level failure message appears on stderr."""
    def side_effect(store_type, closed_grace_days=None):
        if store_type == "gimssine":
            raise RuntimeError("shopify 500 on gimssine")
        return []

    stderr = StringIO()
    with patch(_OPEN_CANDIDATE_TARGET, side_effect=side_effect):
        with pytest.raises(CommandError):
            call_command("backfill_order_cancellations", stderr=stderr)

    output = stderr.getvalue()
    assert "gimssine" in output
    assert "FAILED" in output


# ---------------------------------------------------------------------------
# AC-CANC-027 — chunk-level failure reported and does not block other chunks
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_027_chunk_level_failure_raises_partial():
    """Verify chunk-level failure is reported with (partial) marker.

    When fetch_order_status_by_ids fails on one chunk, reconcile_order_status_for_ids
    returns chunk_failures. The command reports each failure to stderr and raises
    CommandError with (partial) marker. Positive evidence: successful chunk is processed.
    Uses different stores to force separate API calls (like AC-CANC-017 scenario 2).
    """
    Order.objects.create(shopify_order_id=900241, store_type="gimssine")
    Order.objects.create(shopify_order_id=900242, store_type="etoile")

    def side_effect(domain, token, shopify_order_ids):
        ids = list(shopify_order_ids)
        if ids == [900241]:
            raise RuntimeError("chunk fetch error")
        if ids == [900242]:
            return [{"id": 900242, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None}]
        raise AssertionError(f"unexpected chunk: {ids}")

    with patch(_FETCH_BY_IDS_TARGET, side_effect=side_effect):
        with pytest.raises(CommandError, match="partial"):
            call_command("backfill_order_cancellations")

    # Positive evidence: etoile order WAS updated despite gimssine chunk failure.
    order_success = Order.objects.get(shopify_order_id=900242)
    assert order_success.cancelled_at == parse_datetime("2026-08-01T00:00:00Z")


@pytest.mark.django_db
def test_ac_cancc_027_chunk_failures_reported_on_stderr():
    """Verify chunk failure details appear on stderr."""
    Order.objects.create(shopify_order_id=900241, store_type="gimssine")
    Order.objects.create(shopify_order_id=900242, store_type="etoile")

    def side_effect(domain, token, shopify_order_ids):
        ids = list(shopify_order_ids)
        if ids == [900241]:
            raise RuntimeError("network timeout")
        if ids == [900242]:
            return [{"id": 900242, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None}]
        raise AssertionError(f"unexpected chunk: {ids}")

    stderr = StringIO()
    with patch(_FETCH_BY_IDS_TARGET, side_effect=side_effect):
        with pytest.raises(CommandError):
            call_command("backfill_order_cancellations", stderr=stderr)

    output = stderr.getvalue()
    assert "ids=" in output
    assert "900241" in output
    assert "error=" in output


# ---------------------------------------------------------------------------
# AC-CANC-026 (negative control) — success path does not raise CommandError
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_026_success_path_no_error_raised():
    """Verify successful execution does not raise CommandError.

    Negative control: without failures, call_command completes cleanly.
    Positive evidence: orders are actually updated, not just "no error".
    """
    Order.objects.create(shopify_order_id=900243, store_type="gimssine")

    with patch(
        _GET_HEADERS_TARGET,
        return_value=(
            {"orders": [{"id": 900243, "cancelled_at": "2026-08-01T00:00:00Z", "closed_at": None}]},
            {},
        ),
    ):
        # Should not raise CommandError
        call_command("backfill_order_cancellations", "--store", "gimssine")

    # Positive evidence: order WAS updated.
    order = Order.objects.get(shopify_order_id=900243)
    assert order.cancelled_at == parse_datetime("2026-08-01T00:00:00Z")


# ---------------------------------------------------------------------------
# AC-CANC-028 — etoile credentials branch resolves correctly
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ac_cancc_028_etoile_credentials_passed():
    """Verify etoile store resolves and passes correct domain/token.

    The _credentials(store_type) function returns different domain/token
    based on store_type. Capture the arguments passed to reconcile_order_status_for_ids
    and verify etoile's credentials are used (not gimssine's).
    """
    Order.objects.create(shopify_order_id=900244, store_type="etoile")

    captured_calls = []
    original_fetch = __import__("order.shopify_orders", fromlist=["fetch_order_status_by_ids"]).fetch_order_status_by_ids

    def mock_fetch(domain, token, shopify_order_ids):
        captured_calls.append({"domain": domain, "token": token})
        # Return empty list so no orders are updated (we only care about capturing args)
        return []

    # Patch _credentials to return test values per store type
    credentials_gimssine = ("gimssine.myshopify.com", "gimssine_token")
    credentials_etoile = ("etoile.myshopify.com", "etoile_token")

    def mock_credentials(store_type):
        if store_type == "gimssine":
            return credentials_gimssine
        return credentials_etoile

    with patch(_FETCH_BY_IDS_TARGET, side_effect=mock_fetch):
        with patch("order.management.commands.backfill_order_cancellations._credentials", side_effect=mock_credentials):
            call_command("backfill_order_cancellations", "--store", "etoile")

    # Verify etoile's credentials (not gimssine's) are passed to the Shopify API
    assert len(captured_calls) > 0
    assert captured_calls[0]["domain"] == credentials_etoile[0]
    assert captured_calls[0]["token"] == credentials_etoile[1]
