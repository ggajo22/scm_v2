"""SPEC-ORDER-015 T1~T7: outbound processing (Korea warehouse -> US warehouse).

TDD RED-GREEN-REFACTOR. Every test maps to an AC-OUTBOUND-XXX acceptance
scenario and the REQ-OUTBOUND-XXX requirement(s) it traces.

Coverage targets:
  T1  LineItem.shipped_quantity / shipped_at fields + migration 0035
      (REQ-OUTBOUND-001/002/002a, AC-OUTBOUND-009/009a)
  T2  duplicate (name, sku) row summation before matching
      (REQ-OUTBOUND-007, AC-OUTBOUND-005/005a)
  T3  Order.name matching + (order, sku) LineItem matching 0/1/2+ branches
      (REQ-OUTBOUND-003/003a/004/005/005a/006,
       AC-OUTBOUND-004/004a/006/010/010a/011/012)
  T4  quantity-exceeded rejection + shipped_quantity increment + shipped_at +
      logistics_status transition
      (REQ-OUTBOUND-008/009/010/010a, AC-OUTBOUND-001/002/003/013)
  T5  parse_outbound_excel header auto-detection
      (REQ-OUTBOUND-012/012a, AC-OUTBOUND-007/015)
  T6  OutboundProcessView / UploadOutboundView + URL registration
      (REQ-OUTBOUND-011/013/014, AC-OUTBOUND-014/016)
  T7  LineItemDetailSerializer exposes shipped_quantity / shipped_at
  T8  batched-query performance: DB round trips are O(1), not O(groups)
      (no new REQ — pure internal optimisation, behaviour must be identical)
"""

import inspect
import io
from unittest.mock import patch

import openpyxl
import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from freezegun import freeze_time
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.excel_utils import parse_outbound_excel
from order.models import LineItem, Order, Refund
from order.purchase_order_views import _process_outbound_rows
from order.serializers import LineItemDetailSerializer


def _make_order(shopify_order_id: int = 500001, store_type: str = "gimssine", **kwargs) -> Order:
    return Order.objects.create(shopify_order_id=shopify_order_id, store_type=store_type, **kwargs)


def _make_line_item(
    order: Order, shopify_line_item_id: int = 1, sku: str = "ISBN001", **kwargs
) -> LineItem:
    defaults = {"quantity": 10, "title": "Test Book"}
    defaults.update(kwargs)
    return LineItem.objects.create(
        order=order, shopify_line_item_id=shopify_line_item_id, sku=sku, **defaults
    )


# ---------------------------------------------------------------------------
# T1 — data model (REQ-OUTBOUND-001/002/002a, AC-OUTBOUND-009/009a)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLineItemShippedFields:
    """AC-OUTBOUND-009: shipped_quantity exists with default 0, shipped_at
    exists and is nullable. AC-OUTBOUND-009a: an untouched LineItem keeps
    shipped_at = None."""

    def test_shipped_quantity_field_declared_as_integer_default_zero(self):
        """REQ-OUTBOUND-001: IntegerField, default 0."""
        field = LineItem._meta.get_field("shipped_quantity")
        assert field.get_internal_type() == "IntegerField"
        assert field.get_default() == 0
        assert field.null is False

    def test_shipped_at_field_declared_as_nullable_datetime(self):
        """REQ-OUTBOUND-002: DateTimeField, null=True, blank=True."""
        field = LineItem._meta.get_field("shipped_at")
        assert field.get_internal_type() == "DateTimeField"
        assert field.null is True
        assert field.blank is True

    def test_new_line_item_defaults_shipped_quantity_to_zero(self):
        """AC-OUTBOUND-009: a freshly created LineItem starts at 0."""
        li = _make_line_item(_make_order())
        li.refresh_from_db()
        assert li.shipped_quantity == 0

    def test_untouched_line_item_keeps_shipped_at_null(self):
        """AC-OUTBOUND-009a / REQ-OUTBOUND-002a: never-processed LineItem has
        shipped_at = None."""
        li = _make_line_item(_make_order())
        li.refresh_from_db()
        assert li.shipped_at is None

    def test_shipped_fields_persist_to_database(self):
        """Both fields round-trip through the DB (migration 0035 applied)."""
        now = timezone.now()
        li = _make_line_item(_make_order(), shipped_quantity=3, shipped_at=now)
        li.refresh_from_db()
        assert li.shipped_quantity == 3
        assert li.shipped_at is not None


# ---------------------------------------------------------------------------
# T2 — duplicate row summation (REQ-OUTBOUND-007, AC-OUTBOUND-005/005a)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOutboundDuplicateRowSummation:
    """AC-OUTBOUND-005 / AC-OUTBOUND-005a: rows sharing an (order name, sku)
    key are summed into ONE combined quantity BEFORE any matching or
    quantity judgement — deliberately NOT the last-row-wins dedup that
    UploadRackNumberView uses (설계 결정 C)."""

    def test_duplicate_rows_are_summed_not_last_row_wins(self):
        """AC-OUTBOUND-005: total 3 + total 4 -> shipped_quantity 7.

        The discriminating assertion is `== 7`: a last-row-wins dedup would
        produce 4, and a first-row-wins dedup would produce 3.
        """
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10)

        _process_outbound_rows(
            [
                {"name": "#37349", "sku": "ISBN001", "total": 3},
                {"name": "#37349", "sku": "ISBN001", "total": 4},
            ]
        )

        li.refresh_from_db()
        assert li.shipped_quantity == 7

    def test_duplicate_rows_collapse_into_a_single_matched_entry(self):
        """AC-OUTBOUND-005: the response reports one merged item, not two."""
        order = _make_order(name="#37349")
        _make_line_item(order, sku="ISBN001", quantity=10)

        result = _process_outbound_rows(
            [
                {"name": "#37349", "sku": "ISBN001", "total": 3},
                {"name": "#37349", "sku": "ISBN001", "total": 4},
            ]
        )

        assert len(result["matched"]) == 1
        assert result["matched"][0]["total"] == 7

    def test_summation_happens_before_the_quantity_exceeded_check(self):
        """AC-OUTBOUND-005a: 6 + 5 = 11 > quantity 10 -> rejected as ONE
        merged quantity_exceeded item, and nothing is written.

        Judged row-by-row instead, both 6 and 5 would individually fit under
        10 and the LineItem would wrongly end up at 11.
        """
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10)

        result = _process_outbound_rows(
            [
                {"name": "#37349", "sku": "ISBN001", "total": 6},
                {"name": "#37349", "sku": "ISBN001", "total": 5},
            ]
        )

        li.refresh_from_db()
        assert li.shipped_quantity == 0
        assert len(result["quantity_exceeded"]) == 1
        assert result["quantity_exceeded"][0]["total"] == 11

    def test_distinct_keys_are_not_merged_together(self):
        """Different SKUs under the same order stay independent."""
        order = _make_order(name="#37349")
        li_a = _make_line_item(order, shopify_line_item_id=1, sku="ISBN001", quantity=10)
        li_b = _make_line_item(order, shopify_line_item_id=2, sku="ISBN002", quantity=10)

        result = _process_outbound_rows(
            [
                {"name": "#37349", "sku": "ISBN001", "total": 3},
                {"name": "#37349", "sku": "ISBN002", "total": 4},
            ]
        )

        li_a.refresh_from_db()
        li_b.refresh_from_db()
        assert li_a.shipped_quantity == 3
        assert li_b.shipped_quantity == 4
        assert len(result["matched"]) == 2


# ---------------------------------------------------------------------------
# T3 — matching (REQ-OUTBOUND-003/003a/004/005/005a/006,
#      AC-OUTBOUND-004/004a/006/010/010a/011/012)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOutboundMatching:
    """Order is located by exact `Order.name`; the LineItem by
    (matched order, sku). Zero matches and 2+ matches are both reported as
    unmatched and mutate nothing (설계 결정 A — no distribution)."""

    def test_exact_order_name_and_sku_match_is_applied(self):
        """AC-OUTBOUND-011 / REQ-OUTBOUND-004: order + sku together pin down
        exactly one LineItem, which becomes the processing target."""
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10)

        result = _process_outbound_rows([{"name": "#37349", "sku": "ISBN001", "total": 4}])

        li.refresh_from_db()
        assert li.shipped_quantity == 4
        assert len(result["matched"]) == 1
        assert result["unmatched"] == []

    def test_matching_uses_order_name_and_ignores_order_number(self):
        """AC-OUTBOUND-010/010a / REQ-OUTBOUND-003/003a: `Order.order_number`
        has no influence on matching whatsoever.

        Decoy setup: the target order carries a deliberately unrelated
        order_number, while a *different* order carries the order_number that
        naively parses out of the requested name ("#37349" -> 37349).
        Matching must land on the name-matched order, never the decoy.
        """
        target = _make_order(shopify_order_id=500001, name="#37349", order_number=99999)
        decoy = _make_order(shopify_order_id=500002, name="#EB10011778", order_number=37349)
        target_li = _make_line_item(target, sku="ISBN001", quantity=10)
        decoy_li = _make_line_item(decoy, sku="ISBN001", quantity=10)

        _process_outbound_rows([{"name": "#37349", "sku": "ISBN001", "total": 4}])

        target_li.refresh_from_db()
        decoy_li.refresh_from_db()
        assert target_li.shipped_quantity == 4
        assert decoy_li.shipped_quantity == 0

    def test_order_number_is_never_referenced_in_the_matching_source(self):
        """REQ-OUTBOUND-003a (Unwanted): `order_number` must not be *used* by
        the outbound processing implementation.

        Comments are stripped before the check: prose explaining why
        order_number is deliberately avoided is documentation, not usage.
        """
        source = inspect.getsource(_process_outbound_rows)
        code_only = "\n".join(line.split("#")[0] for line in source.splitlines())
        assert "order_number" not in code_only

    def test_order_not_found_is_reported_unmatched(self):
        """AC-OUTBOUND-004 / REQ-OUTBOUND-005: unknown order name -> unmatched,
        nothing modified."""
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10)

        result = _process_outbound_rows([{"name": "#99999", "sku": "ISBN001", "total": 3}])

        li.refresh_from_db()
        assert li.shipped_quantity == 0
        assert result["matched"] == []
        assert len(result["unmatched"]) == 1
        assert result["unmatched"][0]["name"] == "#99999"
        assert result["unmatched"][0]["reason"]

    def test_sku_not_found_under_existing_order_is_reported_unmatched(self):
        """AC-OUTBOUND-004a / REQ-OUTBOUND-005: order exists but has no such
        SKU -> unmatched, nothing modified."""
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10)

        result = _process_outbound_rows([{"name": "#37349", "sku": "ISBN999", "total": 2}])

        li.refresh_from_db()
        assert li.shipped_quantity == 0
        assert result["matched"] == []
        assert len(result["unmatched"]) == 1
        assert result["unmatched"][0]["sku"] == "ISBN999"

    def test_two_or_more_matching_line_items_are_reported_unmatched(self):
        """AC-OUTBOUND-006 / REQ-OUTBOUND-005a (설계 결정 A): an ambiguous
        multi-match is skipped as unmatched — the quantity is NOT distributed
        across the candidates.

        Duplicate SKUs within one order are legal since
        SPEC-SHOPIFY-SKU-SET-002 widened unique_together to
        (order, shopify_line_item_id, sku).
        """
        order = _make_order(name="#37349")
        li_a = _make_line_item(order, shopify_line_item_id=1, sku="ISBN001", quantity=10)
        li_b = _make_line_item(order, shopify_line_item_id=2, sku="ISBN001", quantity=10)

        result = _process_outbound_rows([{"name": "#37349", "sku": "ISBN001", "total": 3}])

        li_a.refresh_from_db()
        li_b.refresh_from_db()
        assert li_a.shipped_quantity == 0
        assert li_b.shipped_quantity == 0
        assert result["matched"] == []
        assert len(result["unmatched"]) == 1

    @pytest.mark.parametrize(
        "current_status",
        ["not_shipped", "shipment_confirmed", "received", "outbound_scheduled"],
    )
    def test_any_logistics_status_is_eligible_for_outbound(self, current_status):
        """AC-OUTBOUND-012 / REQ-OUTBOUND-006: there is no `outbound_scheduled`
        precondition — a LineItem in ANY logistics_status can be processed."""
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10, logistics_status=current_status)

        result = _process_outbound_rows([{"name": "#37349", "sku": "ISBN001", "total": 4}])

        li.refresh_from_db()
        assert li.shipped_quantity == 4
        assert len(result["matched"]) == 1


# ---------------------------------------------------------------------------
# T4 — quantity judgement, timestamp, status transition, atomicity
#      (REQ-OUTBOUND-008/009/010/010a, AC-OUTBOUND-001/002/003/013)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOutboundQuantityAndStatusTransition:
    """shipped_quantity accumulates, shipped_at is stamped, and
    logistics_status flips to "shipped" only once the cumulative quantity
    reaches `quantity`. Over-capacity requests are rejected wholesale."""

    def test_partial_shipment_stamps_time_but_leaves_status_unchanged(self):
        """AC-OUTBOUND-001 / REQ-OUTBOUND-008: 4 of 10 shipped -> quantity and
        timestamp updated, logistics_status untouched."""
        order = _make_order(name="#37349")
        li = _make_line_item(
            order, sku="ISBN001", quantity=10, logistics_status="outbound_scheduled"
        )

        _process_outbound_rows([{"name": "#37349", "sku": "ISBN001", "total": 4}])

        li.refresh_from_db()
        assert li.shipped_quantity == 4
        assert li.shipped_at is not None
        assert li.logistics_status == "outbound_scheduled"

    def test_cumulative_shipment_across_two_requests_transitions_to_shipped(self):
        """AC-OUTBOUND-002 / REQ-OUTBOUND-010: 4 then 6 against quantity 10
        accumulates to exactly 10 and flips logistics_status to "shipped"."""
        order = _make_order(name="#37349")
        li = _make_line_item(
            order, sku="ISBN001", quantity=10, logistics_status="outbound_scheduled"
        )

        _process_outbound_rows([{"name": "#37349", "sku": "ISBN001", "total": 4}])
        li.refresh_from_db()
        first_shipped_at = li.shipped_at
        assert li.logistics_status == "outbound_scheduled"

        _process_outbound_rows([{"name": "#37349", "sku": "ISBN001", "total": 6}])

        li.refresh_from_db()
        assert li.shipped_quantity == 10
        assert li.logistics_status == "shipped"
        assert li.shipped_at >= first_shipped_at

    def test_reaching_quantity_exactly_succeeds_and_is_not_treated_as_exceeded(self):
        """REQ-OUTBOUND-010: the boundary `shipped_quantity + total ==
        quantity` is a SUCCESS that transitions, not an overflow.

        Guards against an off-by-one `>=` in the rejection check.
        """
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=5, logistics_status="received")

        result = _process_outbound_rows([{"name": "#37349", "sku": "ISBN001", "total": 5}])

        li.refresh_from_db()
        assert result["quantity_exceeded"] == []
        assert len(result["matched"]) == 1
        assert li.shipped_quantity == 5
        assert li.logistics_status == "shipped"

    def test_quantity_exceeded_rejects_without_mutating_anything(self):
        """AC-OUTBOUND-003 / REQ-OUTBOUND-009: 8 already shipped + 5 requested
        against quantity 10 -> rejected, nothing written, and the report
        carries the current shipped_quantity, quantity and requested total."""
        order = _make_order(name="#37349")
        li = _make_line_item(
            order,
            sku="ISBN001",
            quantity=10,
            shipped_quantity=8,
            logistics_status="outbound_scheduled",
        )

        result = _process_outbound_rows([{"name": "#37349", "sku": "ISBN001", "total": 5}])

        li.refresh_from_db()
        assert li.shipped_quantity == 8
        assert li.shipped_at is None
        assert li.logistics_status == "outbound_scheduled"
        assert result["matched"] == []
        entry = result["quantity_exceeded"][0]
        assert entry["shipped_quantity"] == 8
        assert entry["quantity"] == 10
        assert entry["total"] == 5

    def test_null_quantity_is_treated_as_zero_and_always_exceeds(self):
        """REQ-OUTBOUND-009 (설계 결정 B): a NULL `quantity` counts as 0
        capacity, so any positive request overflows and is rejected."""
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=None)

        result = _process_outbound_rows([{"name": "#37349", "sku": "ISBN001", "total": 1}])

        li.refresh_from_db()
        assert li.shipped_quantity == 0
        assert li.shipped_at is None
        assert len(result["quantity_exceeded"]) == 1

    def test_below_threshold_keeps_previous_logistics_status(self):
        """AC-OUTBOUND-013 / REQ-OUTBOUND-010a: 3 + 2 = 5 < 10 -> quantity
        advances but the status is left exactly as it was."""
        order = _make_order(name="#37349")
        li = _make_line_item(
            order,
            sku="ISBN001",
            quantity=10,
            shipped_quantity=3,
            logistics_status="received",
        )

        _process_outbound_rows([{"name": "#37349", "sku": "ISBN001", "total": 2}])

        li.refresh_from_db()
        assert li.shipped_quantity == 5
        assert li.logistics_status == "received"

    def test_shipped_at_is_stamped_with_the_processing_time(self):
        """REQ-OUTBOUND-008: shipped_at reflects when the request ran."""
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10)

        with freeze_time("2026-08-10 12:34:56"):
            _process_outbound_rows([{"name": "#37349", "sku": "ISBN001", "total": 4}])

        li.refresh_from_db()
        assert li.shipped_at is not None
        assert li.shipped_at.strftime("%Y-%m-%d %H:%M:%S") == "2026-08-10 12:34:56"

    def test_processing_is_atomic_so_a_mid_run_failure_rolls_everything_back(self):
        """REQ-OUTBOUND-011/013: the whole run is one transaction — rows that
        were already written must be undone if the run fails before commit.

        The failure is injected at `bulk_update`, the batched write path the
        implementation now uses. (It previously hooked the per-row `save()`
        that path replaced; only the injection point moved, the requirement
        under test is unchanged.)

        The patch performs the REAL write first, reads the value back inside
        the transaction to prove it actually reached the database, and only
        then raises. Without that mid-transaction read the assertions below
        would also pass for an implementation that never wrote anything at
        all, which would not demonstrate rollback.
        """
        order = _make_order(name="#37349")
        li_a = _make_line_item(order, shopify_line_item_id=1, sku="ISBN001", quantity=10)
        li_b = _make_line_item(order, shopify_line_item_id=2, sku="ISBN002", quantity=10)

        real_bulk_update = LineItem.objects.bulk_update
        observed: dict[str, int] = {}

        def flaky_bulk_update(objs, fields, **kwargs):
            real_bulk_update(objs, fields, **kwargs)
            observed["a"] = LineItem.objects.get(pk=li_a.pk).shipped_quantity
            observed["b"] = LineItem.objects.get(pk=li_b.pk).shipped_quantity
            raise RuntimeError("simulated failure after the batch was written")

        with patch.object(LineItem.objects, "bulk_update", flaky_bulk_update):
            with pytest.raises(RuntimeError):
                _process_outbound_rows(
                    [
                        {"name": "#37349", "sku": "ISBN001", "total": 3},
                        {"name": "#37349", "sku": "ISBN002", "total": 4},
                    ]
                )

        assert observed == {"a": 3, "b": 4}, "the batch never reached the database"

        li_a.refresh_from_db()
        li_b.refresh_from_db()
        assert li_a.shipped_quantity == 0
        assert li_b.shipped_quantity == 0


# ---------------------------------------------------------------------------
# T5 — Excel parsing (REQ-OUTBOUND-012/012a, AC-OUTBOUND-007/015)
# ---------------------------------------------------------------------------


def _make_outbound_excel(
    rows: list[tuple], header: tuple = ("Name", "Lineitem sku", "Total")
) -> bytes:
    """Build an outbound-upload .xlsx. Values are written verbatim so callers
    can exercise blank/None cells."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(list(header))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestParseOutboundExcel:
    """AC-OUTBOUND-015: headers are located by case-insensitive substring
    match against alias lists, independent of column order.
    AC-OUTBOUND-007 / REQ-OUTBOUND-012a: an unrecognised header set raises
    ValueError (the view turns this into HTTP 422)."""

    def test_parses_standard_english_headers(self):
        """AC-OUTBOUND-015 / REQ-OUTBOUND-012."""
        parsed = parse_outbound_excel(
            _make_outbound_excel([("#37349", "ISBN001", 4), ("#37350", "ISBN002", 2)])
        )

        assert parsed == [
            {"name": "#37349", "sku": "ISBN001", "total": 4},
            {"name": "#37350", "sku": "ISBN002", "total": 2},
        ]

    def test_parses_korean_alias_headers(self):
        """AC-OUTBOUND-015: 주문번호 / 수량 aliases resolve to the same keys."""
        parsed = parse_outbound_excel(
            _make_outbound_excel(
                [("#37349", "ISBN001", 4)], header=("주문번호", "Lineitem SKU", "수량")
            )
        )

        assert parsed == [{"name": "#37349", "sku": "ISBN001", "total": 4}]

    def test_header_detection_is_position_independent(self):
        """AC-OUTBOUND-015: columns may appear in any left-to-right order."""
        parsed = parse_outbound_excel(
            _make_outbound_excel([(4, "ISBN001", "#37349")], header=("Total", "SKU", "Name"))
        )

        assert parsed == [{"name": "#37349", "sku": "ISBN001", "total": 4}]

    @pytest.mark.parametrize(
        "header",
        [
            ("주문", "Lineitem sku", "Total"),  # order-name column unrecognised
            ("Name", "품목", "Total"),  # sku column unrecognised
            ("Name", "Lineitem sku", "개수"),  # quantity column unrecognised
        ],
    )
    def test_missing_required_column_raises_value_error(self, header):
        """AC-OUTBOUND-007 / REQ-OUTBOUND-012a: any of the 3 required columns
        failing to resolve is a hard parse error."""
        with pytest.raises(ValueError):
            parse_outbound_excel(_make_outbound_excel([("#37349", "ISBN001", 4)], header=header))

    def test_order_name_is_read_verbatim_including_leading_hash(self):
        """The value is matched against `Order.name` downstream, so the "#"
        prefix must survive parsing and no int coercion may happen."""
        parsed = parse_outbound_excel(_make_outbound_excel([("#EB10011778", "ISBN001", 1)]))

        assert parsed[0]["name"] == "#EB10011778"

    def test_rows_without_a_sku_are_skipped(self):
        """A row that exists but has no SKU is dropped — it cannot identify a
        LineItem, so it must not become a phantom entry.

        The order-name cell is deliberately populated so the row is really
        written to the sheet; an all-empty tuple would be discarded by
        openpyxl itself and would pass this test without ever reaching the
        parser's blank-SKU guard.
        """
        parsed = parse_outbound_excel(
            _make_outbound_excel([("#37349", "ISBN001", 4), ("#37350", None, 2)])
        )

        assert parsed == [{"name": "#37349", "sku": "ISBN001", "total": 4}]

    def test_trailing_blank_rows_do_not_become_entries(self):
        """Fully-empty trailing rows are dropped too."""
        parsed = parse_outbound_excel(
            _make_outbound_excel([("#37349", "ISBN001", 4), (None, None, None)])
        )

        assert len(parsed) == 1


# ---------------------------------------------------------------------------
# T6 — endpoints (REQ-OUTBOUND-011/013/014, AC-OUTBOUND-014/016)
# ---------------------------------------------------------------------------

OUTBOUND_PROCESS_URL = "/api/purchase-orders/line-items/outbound-process/"
UPLOAD_OUTBOUND_URL = "/api/purchase-orders/upload-outbound/"


def _file_obj(file_bytes: bytes, name: str = "outbound.xlsx"):
    f = io.BytesIO(file_bytes)
    f.name = name
    return f


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="spec015_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def anon_client():
    return APIClient()


@pytest.mark.django_db
class TestOutboundEndpoints:
    """Both endpoints are thin adapters over `_process_outbound_rows`, so they
    must produce byte-identical judgements for equivalent input
    (AC-OUTBOUND-014) and both return the 3-category contract
    (AC-OUTBOUND-016)."""

    def test_manual_entry_endpoint_applies_outbound(self, auth_client):
        """REQ-OUTBOUND-011: manual JSON rows are processed."""
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10)

        response = auth_client.post(
            OUTBOUND_PROCESS_URL,
            {"rows": [{"name": "#37349", "sku": "ISBN001", "total": 4}]},
            format="json",
        )

        assert response.status_code == 200
        li.refresh_from_db()
        assert li.shipped_quantity == 4
        assert response.data["matched_count"] == 1

    def test_manual_entry_endpoint_requires_authentication(self, anon_client):
        response = anon_client.post(OUTBOUND_PROCESS_URL, {"rows": []}, format="json")
        assert response.status_code in (401, 403)

    def test_excel_upload_endpoint_applies_outbound(self, auth_client):
        """REQ-OUTBOUND-013: Excel upload runs the identical pipeline."""
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10)
        file_bytes = _make_outbound_excel([("#37349", "ISBN001", 4)])

        response = auth_client.post(
            UPLOAD_OUTBOUND_URL, {"file": _file_obj(file_bytes)}, format="multipart"
        )

        assert response.status_code == 200
        li.refresh_from_db()
        assert li.shipped_quantity == 4
        assert response.data["matched_count"] == 1

    def test_excel_upload_with_unrecognised_header_returns_422(self, auth_client):
        """AC-OUTBOUND-007 / REQ-OUTBOUND-012a: parse failure -> HTTP 422 and
        nothing is modified."""
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10)
        file_bytes = _make_outbound_excel(
            [("#37349", "ISBN001", 4)], header=("주문", "품목", "개수")
        )

        response = auth_client.post(
            UPLOAD_OUTBOUND_URL, {"file": _file_obj(file_bytes)}, format="multipart"
        )

        assert response.status_code == 422
        li.refresh_from_db()
        assert li.shipped_quantity == 0

    def test_excel_upload_without_a_file_returns_400(self, auth_client):
        response = auth_client.post(UPLOAD_OUTBOUND_URL, {}, format="multipart")
        assert response.status_code == 400

    def test_response_exposes_three_categories_each_with_count_and_items(self, auth_client):
        """AC-OUTBOUND-016 / REQ-OUTBOUND-014."""
        order = _make_order(name="#37349")
        _make_line_item(order, shopify_line_item_id=1, sku="ISBN001", quantity=10)
        _make_line_item(order, shopify_line_item_id=2, sku="ISBN002", quantity=2)

        response = auth_client.post(
            OUTBOUND_PROCESS_URL,
            {
                "rows": [
                    {"name": "#37349", "sku": "ISBN001", "total": 4},
                    {"name": "#99999", "sku": "ISBN001", "total": 3},
                    {"name": "#37349", "sku": "ISBN002", "total": 5},
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        for category in ("matched", "unmatched", "quantity_exceeded"):
            assert category in response.data
            assert f"{category}_count" in response.data
            assert len(response.data[category]) == response.data[f"{category}_count"] == 1

    def test_both_endpoints_return_identical_results_for_equivalent_input(self, auth_client):
        """AC-OUTBOUND-014: the manual and Excel endpoints are two front doors
        onto one shared implementation — same input, same verdict.

        The LineItems are reset to their pre-request state between the two
        calls so the second run starts from an identical baseline.
        """
        order = _make_order(name="#37349")
        _make_line_item(order, shopify_line_item_id=1, sku="ISBN001", quantity=10)
        _make_line_item(order, shopify_line_item_id=2, sku="ISBN002", quantity=2)

        rows = [
            {"name": "#37349", "sku": "ISBN001", "total": 4},
            {"name": "#99999", "sku": "ISBN001", "total": 3},
            {"name": "#37349", "sku": "ISBN002", "total": 5},
        ]

        manual = auth_client.post(OUTBOUND_PROCESS_URL, {"rows": rows}, format="json")

        LineItem.objects.filter(order=order).update(
            shipped_quantity=0, shipped_at=None, logistics_status="not_shipped"
        )

        file_bytes = _make_outbound_excel([(r["name"], r["sku"], r["total"]) for r in rows])
        excel = auth_client.post(
            UPLOAD_OUTBOUND_URL, {"file": _file_obj(file_bytes)}, format="multipart"
        )

        assert manual.status_code == excel.status_code == 200
        for category in ("matched", "unmatched", "quantity_exceeded"):
            assert manual.data[category] == excel.data[category]
            assert manual.data[f"{category}_count"] == excel.data[f"{category}_count"]


# ---------------------------------------------------------------------------
# T7 — serializer exposure (user-approved addition)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLineItemDetailSerializerShippedFields:
    """`LineItemDetailSerializer` exposes the two new outbound fields so the
    order-detail screen can read them."""

    def test_serializer_exposes_shipped_quantity_and_shipped_at(self):
        assert "shipped_quantity" in LineItemDetailSerializer.Meta.fields
        assert "shipped_at" in LineItemDetailSerializer.Meta.fields

    def test_serialized_output_carries_the_current_values(self):
        stamped = timezone.now()
        li = _make_line_item(
            _make_order(name="#37349"), sku="ISBN001", shipped_quantity=4, shipped_at=stamped
        )

        data = LineItemDetailSerializer(li).data

        assert data["shipped_quantity"] == 4
        assert data["shipped_at"] is not None

    def test_untouched_line_item_serializes_shipped_at_as_null(self):
        """AC-OUTBOUND-009a surfaced through the API layer."""
        li = _make_line_item(_make_order(name="#37349"), sku="ISBN001")

        data = LineItemDetailSerializer(li).data

        assert data["shipped_quantity"] == 0
        assert data["shipped_at"] is None


# ---------------------------------------------------------------------------
# Malformed-input / error-branch coverage
#
# NOTE: unlike the T1-T7 classes above, these tests were written AFTER the
# implementation to cover defensive branches (bad cell values, unreadable
# uploads, malformed request bodies) that were written alongside the
# requirement-driven code rather than driven by their own failing test.
# They are gap-filling tests, not TDD cycles.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOutboundMalformedInput:
    """Garbage cell values must degrade to a reported row rather than raising,
    and both endpoints must reject structurally invalid requests with 4xx."""

    @pytest.mark.parametrize("bad_total", [None, "", "abc", "12abc"])
    def test_unparseable_total_is_rejected_rather_than_silently_applied(self, bad_total):
        """An unreadable quantity is not a shippable amount — the row must be
        reported, not counted as a success."""
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10)

        result = _process_outbound_rows(
            [{"name": "#37349", "sku": "ISBN001", "total": bad_total}]
        )

        li.refresh_from_db()
        assert li.shipped_quantity == 0
        assert result["matched"] == []
        assert result["unmatched"][0]["reason"] == "invalid_total"

    def test_missing_total_key_is_rejected(self):
        order = _make_order(name="#37349")
        _make_line_item(order, sku="ISBN001", quantity=10)

        result = _process_outbound_rows([{"name": "#37349", "sku": "ISBN001"}])

        assert result["matched"] == []
        assert result["unmatched"][0]["reason"] == "invalid_total"

    def test_manual_endpoint_rejects_a_non_list_rows_value(self, auth_client):
        response = auth_client.post(
            OUTBOUND_PROCESS_URL, {"rows": "not-a-list"}, format="json"
        )
        assert response.status_code == 400

    def test_manual_endpoint_accepts_an_empty_batch(self, auth_client):
        response = auth_client.post(OUTBOUND_PROCESS_URL, {"rows": []}, format="json")

        assert response.status_code == 200
        assert response.data["matched_count"] == 0
        assert response.data["unmatched_count"] == 0
        assert response.data["quantity_exceeded_count"] == 0

    def test_upload_endpoint_rejects_a_non_xlsx_filename(self, auth_client):
        response = auth_client.post(
            UPLOAD_OUTBOUND_URL,
            {"file": _file_obj(b"whatever", name="outbound.csv")},
            format="multipart",
        )
        assert response.status_code == 400

    def test_upload_endpoint_returns_422_for_unreadable_bytes(self, auth_client):
        """A .xlsx-named file that openpyxl cannot open is a parse failure,
        not a server error."""
        response = auth_client.post(
            UPLOAD_OUTBOUND_URL,
            {"file": _file_obj(b"this is not a spreadsheet", name="outbound.xlsx")},
            format="multipart",
        )
        assert response.status_code == 422


class TestParseOutboundExcelMalformedInput:
    """Parser-level defensive branches."""

    def test_unreadable_bytes_raise_value_error(self):
        with pytest.raises(ValueError):
            parse_outbound_excel(b"not a spreadsheet at all")

    def test_workbook_with_no_rows_raises_value_error(self):
        wb = openpyxl.Workbook()
        buf = io.BytesIO()
        wb.save(buf)

        with pytest.raises(ValueError):
            parse_outbound_excel(buf.getvalue())

    def test_blank_order_name_cell_becomes_empty_string(self):
        """A blank order cell must not crash; it flows through as "" and is
        reported unmatched downstream rather than vanishing."""
        parsed = parse_outbound_excel(_make_outbound_excel([(None, "ISBN001", 4)]))

        assert parsed == [{"name": "", "sku": "ISBN001", "total": 4}]

    @pytest.mark.parametrize("bad_total", [None, "abc", ""])
    def test_non_numeric_total_cell_becomes_none_not_zero(self, bad_total):
        """CHANGED from `... becomes_zero`, which asserted `total == 0`.

        That assertion encoded the safety gap rather than a requirement. It was
        written when every non-positive total was rejected identically, so
        flattening an unreadable cell to 0 was unobservable. Once total 0 on a
        warehouse_ca / warehouse_nj LineItem became a "mark complete" signal
        (TestZeroTotalUsWarehouseCompletion), that flattening turned an empty
        or garbage cell into a shipment-closing instruction. The parser now
        preserves the parse failure as None so the matching layer can reject
        it; see TestZeroTotalRequiresAGenuineParsedZero for the behaviour this
        protects.
        """
        parsed = parse_outbound_excel(
            _make_outbound_excel([("#37349", "ISBN001", bad_total)])
        )

        assert parsed[0]["total"] is None

    def test_numeric_total_cell_is_still_parsed_as_int(self):
        """The counterpart to the above: readable cells, INCLUDING an explicit
        0, must still arrive as ints so the completion path stays reachable."""
        parsed = parse_outbound_excel(
            _make_outbound_excel([("#37349", "ISBN001", 0), ("#37349", "ISBN002", 4)])
        )

        assert [r["total"] for r in parsed] == [0, 4]

    @pytest.mark.django_db
    def test_blank_order_name_is_reported_unmatched_end_to_end(self):
        """Ties the parser's "" order name to the matching layer's verdict."""
        _make_order(name="#37349")

        result = _process_outbound_rows(
            parse_outbound_excel(_make_outbound_excel([(None, "ISBN001", 4)]))
        )

        assert result["unmatched_count"] == 1
        assert result["unmatched"][0]["reason"] == "order_not_found"


# ---------------------------------------------------------------------------
# Exclusion guard: shipped_quantity must never decrease
#
# spec.md Exclusions: "출고 취소/되돌리기(undo) 기능 — shipped_quantity 감소 —
# 이번 SPEC 범위 밖". A negative `total` would reach exactly that excluded
# capability through ordinary input, so non-positive totals are rejected.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOutboundRejectsNonPositiveTotals:
    def test_negative_total_cannot_decrement_shipped_quantity(self):
        """The core invariant: no input may reduce shipped_quantity."""
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10, shipped_quantity=8)

        result = _process_outbound_rows([{"name": "#37349", "sku": "ISBN001", "total": -5}])

        li.refresh_from_db()
        assert li.shipped_quantity == 8
        assert result["matched"] == []
        assert result["unmatched"][0]["reason"] == "invalid_total"

    @pytest.mark.parametrize("bad_total", [0, -1, -5, -100])
    def test_non_positive_totals_are_all_rejected(self, bad_total):
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10, shipped_quantity=4)

        result = _process_outbound_rows(
            [{"name": "#37349", "sku": "ISBN001", "total": bad_total}]
        )

        li.refresh_from_db()
        assert li.shipped_quantity == 4
        assert result["matched"] == []
        assert result["unmatched_count"] == 1

    def test_rejected_row_leaves_timestamp_and_status_untouched(self):
        order = _make_order(name="#37349")
        li = _make_line_item(
            order,
            sku="ISBN001",
            quantity=10,
            shipped_quantity=8,
            logistics_status="outbound_scheduled",
        )

        _process_outbound_rows([{"name": "#37349", "sku": "ISBN001", "total": -5}])

        li.refresh_from_db()
        assert li.shipped_at is None
        assert li.logistics_status == "outbound_scheduled"

    def test_negative_row_cannot_offset_a_positive_row_for_the_same_key(self):
        """Rejection happens per row, BEFORE summation — otherwise a negative
        row could quietly shrink a legitimate positive one."""
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10)

        result = _process_outbound_rows(
            [
                {"name": "#37349", "sku": "ISBN001", "total": 8},
                {"name": "#37349", "sku": "ISBN001", "total": -5},
            ]
        )

        li.refresh_from_db()
        assert li.shipped_quantity == 8
        assert result["matched"][0]["total"] == 8
        assert any(u["reason"] == "invalid_total" for u in result["unmatched"])

    def test_manual_endpoint_cannot_decrement_shipped_quantity(self, auth_client):
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10, shipped_quantity=8)

        response = auth_client.post(
            OUTBOUND_PROCESS_URL,
            {"rows": [{"name": "#37349", "sku": "ISBN001", "total": -5}]},
            format="json",
        )

        li.refresh_from_db()
        assert response.status_code == 200
        assert li.shipped_quantity == 8
        assert response.data["matched_count"] == 0

    def test_excel_endpoint_cannot_decrement_shipped_quantity(self, auth_client):
        order = _make_order(name="#37349")
        li = _make_line_item(order, sku="ISBN001", quantity=10, shipped_quantity=8)
        file_bytes = _make_outbound_excel([("#37349", "ISBN001", -5)])

        response = auth_client.post(
            UPLOAD_OUTBOUND_URL, {"file": _file_obj(file_bytes)}, format="multipart"
        )

        li.refresh_from_db()
        assert response.status_code == 200
        assert li.shipped_quantity == 8
        assert response.data["matched_count"] == 0


@pytest.mark.django_db
class TestOutboundMalformedRowShape:
    """A structurally invalid request body is a client error (400), never an
    unhandled AttributeError surfacing as a 500."""

    @pytest.mark.parametrize("bad_rows", [[123, "abc"], ["just-a-string"], [None], [[1, 2]]])
    def test_manual_endpoint_returns_400_for_non_dict_rows(self, auth_client, bad_rows):
        response = auth_client.post(OUTBOUND_PROCESS_URL, {"rows": bad_rows}, format="json")
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "bad_row",
        [{"sku": "ISBN001", "total": 4}, {"name": "#37349", "total": 4}, {"name": "#37349"}],
    )
    def test_manual_endpoint_returns_400_for_row_missing_required_keys(
        self, auth_client, bad_row
    ):
        response = auth_client.post(OUTBOUND_PROCESS_URL, {"rows": [bad_row]}, format="json")
        assert response.status_code == 400

    def test_process_outbound_rows_does_not_crash_on_non_dict_rows(self):
        """Defensive: the shared function must degrade, not raise, if a caller
        ever hands it a malformed row."""
        result = _process_outbound_rows([123, "abc", None])

        assert result["matched"] == []
        assert result["unmatched_count"] == 3


@pytest.mark.django_db
class TestOutboundViewErrorHandling:
    """Both views mirror UploadRackNumberView's graceful-failure contract."""

    def test_upload_endpoint_requires_authentication(self, anon_client):
        file_bytes = _make_outbound_excel([("#37349", "ISBN001", 4)])
        response = anon_client.post(
            UPLOAD_OUTBOUND_URL, {"file": _file_obj(file_bytes)}, format="multipart"
        )
        assert response.status_code in (401, 403)

    def test_manual_endpoint_returns_json_500_on_unexpected_error(self, auth_client):
        with patch(
            "order.purchase_order_views._process_outbound_rows",
            side_effect=RuntimeError("boom"),
        ):
            response = auth_client.post(
                OUTBOUND_PROCESS_URL,
                {"rows": [{"name": "#37349", "sku": "ISBN001", "total": 4}]},
                format="json",
            )

        assert response.status_code == 500
        assert "detail" in response.data

    def test_upload_endpoint_returns_json_500_on_unexpected_error(self, auth_client):
        file_bytes = _make_outbound_excel([("#37349", "ISBN001", 4)])
        with patch(
            "order.purchase_order_views._process_outbound_rows",
            side_effect=RuntimeError("boom"),
        ):
            response = auth_client.post(
                UPLOAD_OUTBOUND_URL, {"file": _file_obj(file_bytes)}, format="multipart"
            )

        assert response.status_code == 500
        assert "detail" in response.data


# ---------------------------------------------------------------------------
# T8 — batched DB access (performance; no behaviour change)
#
# The dev/prod database is a remote MySQL instance with ~130ms round-trip
# latency, so the wall-clock cost of this endpoint is dominated by the NUMBER
# of queries, not by the work each query does. The original implementation ran
# 3 queries per (order name, sku) group — Order lookup, LineItem lookup, save —
# so an 8-row upload cost ~24 round trips (~3s) and a 50-row upload ~150 round
# trips (~19s). These tests pin the query count as an O(1) contract.
# ---------------------------------------------------------------------------


def _seed_outbound_groups(n: int, offset: int = 0) -> list[dict]:
    """Create `n` orders, each with exactly one matching LineItem, and return
    the request rows that target them (one distinct group per order)."""
    rows = []
    for i in range(n):
        seq = offset + i
        name = f"#Q{seq:05d}"
        sku = f"ISBNQ{seq:05d}"
        order = _make_order(shopify_order_id=900000 + seq, name=name)
        _make_line_item(order, shopify_line_item_id=900000 + seq, sku=sku, quantity=10)
        rows.append({"name": name, "sku": sku, "total": 1})
    return rows


def _count_queries(rows: list[dict]) -> int:
    with CaptureQueriesContext(connection) as ctx:
        _process_outbound_rows(rows)
    return len(ctx.captured_queries)


@pytest.mark.django_db
class TestOutboundQueryCountIsIndependentOfRowCount:
    """Response time must not scale with the number of uploaded rows.

    The discriminating assertion is the EQUALITY between a 2-group batch and a
    10-group batch: any per-group query at all makes those two numbers differ,
    regardless of what the absolute constant happens to be on a given backend.
    """

    def test_query_count_is_identical_for_2_and_for_10_groups(self):
        """The strongest proof of O(1): 5x the input, same number of queries."""
        two = _count_queries(_seed_outbound_groups(2, offset=0))
        ten = _count_queries(_seed_outbound_groups(10, offset=100))

        assert two == ten, (
            f"query count scales with input size: 2 groups -> {two} queries, "
            f"10 groups -> {ten} queries"
        )

    def test_query_count_stays_within_a_small_fixed_bound(self):
        """Absolute ceiling: Order fetch + LineItem fetch + bulk_update, plus
        the savepoint statements `transaction.atomic()` emits inside the test's
        own wrapping transaction."""
        assert _count_queries(_seed_outbound_groups(10, offset=200)) <= 6

    def test_a_batch_that_writes_nothing_issues_no_write_query(self):
        """All-unmatched batches must not emit a bulk_update at all."""
        rows = [{"name": f"#MISSING{i}", "sku": "ISBN001", "total": 1} for i in range(10)]

        assert _count_queries(rows) <= 4

    def test_an_empty_batch_touches_the_database_at_most_for_the_transaction(self):
        """Nothing to look up means nothing to query."""
        assert _count_queries([]) <= 2


@pytest.mark.django_db
class TestOutboundBatchingPreservesMatchingSemantics:
    """Behavioural parity guards for the batched lookup. Each of these passes
    identically against the original per-group implementation — they exist to
    pin the semantics a batched rewrite could plausibly break."""

    def test_duplicate_order_names_resolve_to_the_lowest_pk_order(self):
        """`Order.name` carries no uniqueness constraint (unique_together is
        (shopify_order_id, store_type)), so colliding names are legal.

        `.filter(name=X).first()` on an unordered queryset falls back to
        `ORDER BY pk` in Django, i.e. the OLDEST order wins. A batched
        `name__in` fetch must reproduce that tie-break exactly, not whatever
        order MySQL happens to return rows in.
        """
        first = _make_order(shopify_order_id=910001, name="#DUPNAME")
        second = _make_order(shopify_order_id=910002, name="#DUPNAME")
        first_li = _make_line_item(first, shopify_line_item_id=1, sku="ISBN001", quantity=10)
        second_li = _make_line_item(second, shopify_line_item_id=2, sku="ISBN001", quantity=10)

        result = _process_outbound_rows([{"name": "#DUPNAME", "sku": "ISBN001", "total": 3}])

        first_li.refresh_from_db()
        second_li.refresh_from_db()
        assert first_li.shipped_quantity == 3
        assert second_li.shipped_quantity == 0
        assert result["matched"][0]["line_item_id"] == first_li.id

    def test_duplicate_order_names_do_not_turn_into_a_multiple_line_items_verdict(self):
        """Two same-named orders each holding one matching SKU is still a
        single match against the winning order — not an ambiguous 2-candidate
        rejection (설계 결정 A applies per order, not across orders)."""
        first = _make_order(shopify_order_id=911001, name="#DUPNAME2")
        _make_order(shopify_order_id=911002, name="#DUPNAME2")
        _make_line_item(first, shopify_line_item_id=1, sku="ISBN001", quantity=10)

        result = _process_outbound_rows([{"name": "#DUPNAME2", "sku": "ISBN001", "total": 3}])

        assert result["matched_count"] == 1
        assert result["unmatched"] == []

    def test_a_sku_belonging_to_another_order_is_not_borrowed_across_groups(self):
        """Cross-product guard.

        A batched fetch keyed on `order__in` AND `sku__in` independently also
        returns pairs nobody asked for. Requesting (order A, sku B) — where
        sku B only exists under order B — must stay `line_item_not_found`, and
        order B's LineItem must not be touched.
        """
        order_a = _make_order(shopify_order_id=912001, name="#XPROD_A")
        order_b = _make_order(shopify_order_id=912002, name="#XPROD_B")
        li_a = _make_line_item(order_a, shopify_line_item_id=1, sku="SKU_A", quantity=10)
        li_b = _make_line_item(order_b, shopify_line_item_id=2, sku="SKU_B", quantity=10)

        result = _process_outbound_rows(
            [
                {"name": "#XPROD_A", "sku": "SKU_A", "total": 2},
                {"name": "#XPROD_A", "sku": "SKU_B", "total": 3},
            ]
        )

        li_a.refresh_from_db()
        li_b.refresh_from_db()
        assert li_a.shipped_quantity == 2
        assert li_b.shipped_quantity == 0
        assert result["matched_count"] == 1
        assert result["unmatched"][0]["reason"] == "line_item_not_found"

    def test_result_lists_keep_their_original_first_seen_row_ordering(self):
        """Grouping is insertion-ordered, so the response lists must follow the
        order the keys first appeared in the request — a batched rewrite that
        iterates a lookup dict instead would silently reshuffle them."""
        order = _make_order(shopify_order_id=913001, name="#ORDERING")
        _make_line_item(order, shopify_line_item_id=1, sku="SKU_1", quantity=10)
        _make_line_item(order, shopify_line_item_id=2, sku="SKU_2", quantity=10)
        _make_line_item(order, shopify_line_item_id=3, sku="SKU_3", quantity=10)

        result = _process_outbound_rows(
            [
                {"name": "#ORDERING", "sku": "SKU_3", "total": 1},
                {"name": "#ORDERING", "sku": "SKU_1", "total": 1},
                {"name": "#ORDERING", "sku": "SKU_2", "total": 1},
            ]
        )

        assert [m["sku"] for m in result["matched"]] == ["SKU_3", "SKU_1", "SKU_2"]

    def test_below_threshold_match_does_not_advance_logistics_status_via_batch_write(self):
        """The batched write lists `logistics_status` unconditionally, so a
        below-threshold match rewrites the field with its own existing value.
        That must be a no-op, never a reset to the model default."""
        order = _make_order(shopify_order_id=914001, name="#KEEPSTATUS")
        li_keep = _make_line_item(
            order,
            shopify_line_item_id=1,
            sku="SKU_KEEP",
            quantity=10,
            logistics_status="received",
        )
        li_advance = _make_line_item(
            order,
            shopify_line_item_id=2,
            sku="SKU_ADVANCE",
            quantity=4,
            logistics_status="outbound_scheduled",
        )

        _process_outbound_rows(
            [
                {"name": "#KEEPSTATUS", "sku": "SKU_KEEP", "total": 1},
                {"name": "#KEEPSTATUS", "sku": "SKU_ADVANCE", "total": 4},
            ]
        )

        li_keep.refresh_from_db()
        li_advance.refresh_from_db()
        assert li_keep.logistics_status == "received"
        assert li_advance.logistics_status == "shipped"


# ---------------------------------------------------------------------------
# T9 — total == 0 as a US-warehouse completion signal
#
# A LineItem confirmed against a US warehouse (warehouse_ca / warehouse_nj)
# was never physically shipped Korea -> US: it was already sitting in the
# destination warehouse. Such a row arrives with total 0 and must be read as
# "already complete", not as an unshippable amount.
#
# Everything else about total 0 is unchanged: a non-US confirmed_distributor
# (Korea warehouse, unset, or a real distributor) still yields invalid_total,
# and a NEGATIVE total is still rejected per row before grouping, because
# 출고 취소/되돌리기(undo) stays out of scope.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestZeroTotalUsWarehouseCompletion:
    """total == 0 + confirmed_distributor in {warehouse_ca, warehouse_nj}
    completes the LineItem through the existing REQ-OUTBOUND-010 threshold
    mechanism."""

    @pytest.mark.parametrize("us_warehouse", ["warehouse_ca", "warehouse_nj"])
    def test_zero_total_on_a_us_warehouse_line_item_completes_it(self, us_warehouse):
        """T9-1 / T9-2: shipped_quantity jumps to the full quantity and the
        existing `shipped_quantity >= effective_quantity` check flips
        logistics_status to "shipped"."""
        order = _make_order(shopify_order_id=920001, name="#USWH")
        li = _make_line_item(
            order,
            sku="ISBN001",
            quantity=7,
            confirmed_distributor=us_warehouse,
            logistics_status="outbound_scheduled",
        )

        result = _process_outbound_rows([{"name": "#USWH", "sku": "ISBN001", "total": 0}])

        li.refresh_from_db()
        assert li.shipped_quantity == 7
        assert li.logistics_status == "shipped"
        assert li.shipped_at is not None
        assert result["unmatched"] == []
        assert result["quantity_exceeded"] == []
        assert result["matched_count"] == 1
        assert result["matched"][0] == {
            "name": "#USWH",
            "sku": "ISBN001",
            "total": 0,
            "line_item_id": li.id,
            "shipped_quantity": 7,
            "quantity": 7,
            "logistics_status": "shipped",
        }

    @pytest.mark.parametrize(
        "distributor", ["warehouse_korea", None, "booxen", "kyobo", "yes24", ""]
    )
    def test_zero_total_on_a_non_us_warehouse_line_item_stays_invalid_total(
        self, distributor
    ):
        """T9-3 / T9-4 / T9-5: only the two US warehouse codes unlock the
        completion path. Korea warehouse, an unconfirmed LineItem and a real
        distributor all keep the pre-existing rejection, untouched."""
        order = _make_order(shopify_order_id=920002, name="#NONUS")
        li = _make_line_item(
            order,
            sku="ISBN001",
            quantity=7,
            shipped_quantity=2,
            confirmed_distributor=distributor,
            logistics_status="outbound_scheduled",
        )

        result = _process_outbound_rows([{"name": "#NONUS", "sku": "ISBN001", "total": 0}])

        li.refresh_from_db()
        assert li.shipped_quantity == 2
        assert li.shipped_at is None
        assert li.logistics_status == "outbound_scheduled"
        assert result["matched"] == []
        assert result["unmatched_count"] == 1
        assert result["unmatched"][0]["reason"] == "invalid_total"

    def test_zero_total_on_an_already_shipped_us_warehouse_line_item_is_idempotent(self):
        """T9-6: re-running the same completion must not double-apply. The new
        value is max(current, effective) — never a blind overwrite."""
        order = _make_order(shopify_order_id=920003, name="#USWHIDEM")
        li = _make_line_item(
            order,
            sku="ISBN001",
            quantity=7,
            shipped_quantity=7,
            confirmed_distributor="warehouse_ca",
            logistics_status="shipped",
        )

        result = _process_outbound_rows([{"name": "#USWHIDEM", "sku": "ISBN001", "total": 0}])

        li.refresh_from_db()
        assert li.shipped_quantity == 7
        assert li.logistics_status == "shipped"
        assert result["matched_count"] == 1
        assert result["matched"][0]["shipped_quantity"] == 7

    def test_zero_total_never_decreases_an_over_shipped_line_item(self):
        """SAFETY: an anomalous shipped_quantity ABOVE quantity must not be
        pulled back down to quantity by this path — mirrors the
        negative-row undo guard. The completion path writes
        max(shipped_quantity, effective_quantity), never effective_quantity
        unconditionally."""
        order = _make_order(shopify_order_id=920004, name="#USWHOVER")
        li = _make_line_item(
            order,
            sku="ISBN001",
            quantity=7,
            shipped_quantity=9,
            confirmed_distributor="warehouse_nj",
        )

        result = _process_outbound_rows([{"name": "#USWHOVER", "sku": "ISBN001", "total": 0}])

        li.refresh_from_db()
        assert li.shipped_quantity == 9
        assert li.logistics_status == "shipped"
        assert result["matched"][0]["shipped_quantity"] == 9

    def test_zero_total_reports_order_not_found_when_the_order_is_missing(self):
        """T9-7a: matching is unchanged by total value. With no Order there is
        no LineItem to read confirmed_distributor from, so the match verdict
        wins over the invalid_total verdict."""
        result = _process_outbound_rows([{"name": "#NOSUCHORDER", "sku": "ISBN001", "total": 0}])

        assert result["matched"] == []
        assert result["unmatched"][0]["reason"] == "order_not_found"

    def test_zero_total_reports_line_item_not_found_when_the_sku_is_missing(self):
        """T9-7b: same for a known order holding no such SKU."""
        order = _make_order(shopify_order_id=920005, name="#USWHNOSKU")
        _make_line_item(order, sku="ISBN001", quantity=7, confirmed_distributor="warehouse_ca")

        result = _process_outbound_rows(
            [{"name": "#USWHNOSKU", "sku": "ISBN_MISSING", "total": 0}]
        )

        assert result["matched"] == []
        assert result["unmatched"][0]["reason"] == "line_item_not_found"

    @pytest.mark.parametrize("bad_total", [-1, -5, -100])
    def test_negative_total_is_still_rejected_on_a_us_warehouse_line_item(self, bad_total):
        """T9-8: the completion path is reachable through total == 0 ONLY. A US
        warehouse LineItem gives a negative row no new privileges."""
        order = _make_order(shopify_order_id=920006, name="#USWHNEG")
        li = _make_line_item(
            order,
            sku="ISBN001",
            quantity=7,
            shipped_quantity=5,
            confirmed_distributor="warehouse_ca",
            logistics_status="outbound_scheduled",
        )

        result = _process_outbound_rows(
            [{"name": "#USWHNEG", "sku": "ISBN001", "total": bad_total}]
        )

        li.refresh_from_db()
        assert li.shipped_quantity == 5
        assert li.logistics_status == "outbound_scheduled"
        assert result["matched"] == []
        assert result["unmatched"][0]["reason"] == "invalid_total"

    def test_negative_row_never_reaches_the_matching_stage_at_all(self):
        """SAFETY: negative rejection stays STRICTLY pre-grouping. A batch of
        nothing but negative rows must issue no Order/LineItem lookup
        whatsoever — proving a negative row can never enter the summation that
        the new zero path reads."""
        order = _make_order(shopify_order_id=920007, name="#USWHPRE")
        _make_line_item(order, sku="ISBN001", quantity=7, confirmed_distributor="warehouse_ca")

        with CaptureQueriesContext(connection) as ctx:
            result = _process_outbound_rows(
                [
                    {"name": "#USWHPRE", "sku": "ISBN001", "total": -3},
                    {"name": "#USWHPRE", "sku": "ISBN001", "total": -4},
                ]
            )

        selects = [q["sql"] for q in ctx.captured_queries if "orders_" in (q["sql"] or "")]
        assert selects == []
        assert result["unmatched_count"] == 2
        assert all(u["reason"] == "invalid_total" for u in result["unmatched"])

    def test_a_zero_row_summed_with_a_positive_row_is_a_normal_shipment(self):
        """T9-9: the completion branch keys off the SUMMED total. 0 + 5 is 5,
        i.e. an ordinary partial shipment — the zero contributes nothing and
        confirmed_distributor is never consulted."""
        order = _make_order(shopify_order_id=920008, name="#USWHMIX")
        li = _make_line_item(
            order,
            sku="ISBN001",
            quantity=7,
            confirmed_distributor="warehouse_ca",
            logistics_status="outbound_scheduled",
        )

        result = _process_outbound_rows(
            [
                {"name": "#USWHMIX", "sku": "ISBN001", "total": 0},
                {"name": "#USWHMIX", "sku": "ISBN001", "total": 5},
            ]
        )

        li.refresh_from_db()
        assert li.shipped_quantity == 5
        assert li.logistics_status == "outbound_scheduled"
        assert result["matched_count"] == 1
        assert result["matched"][0]["total"] == 5
        # The zero row is absorbed by the sum, not reported separately: it now
        # enters grouping instead of being dropped as invalid_total up front.
        assert result["unmatched"] == []


# ---------------------------------------------------------------------------
# T10 — the US-warehouse completion path requires a GENUINELY PARSED zero
#
# SAFETY tightening for the T9 completion path above. Before T9 existed, every
# non-positive total was rejected identically, so it did not matter that a
# blank / missing / garbage quantity silently coerced to 0 — real 0, negative
# and parse failure all landed on the same `invalid_total` verdict.
#
# T9 gave the integer 0 meaning: on a warehouse_ca / warehouse_nj LineItem it
# CLOSES OUT the shipment. That turns the silent coercion into a live hazard —
# an empty Total cell or a stray Excel formula error (#N/A, #REF!) on such a
# LineItem would be indistinguishable from a deliberate "already in the US
# warehouse" signal and would wrongly mark the item shipped.
#
# So the completion path must key off a zero the input actually SPELLED, and
# a value that merely defaulted to zero keeps the pre-T9 `invalid_total`
# rejection it always had. The reason code is deliberately reused: both cases
# are "the total value was not usable", and callers already handle it.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestZeroTotalRequiresAGenuineParsedZero:
    """A parse failure must never be read as a US-warehouse completion signal."""

    @staticmethod
    def _us_warehouse_item(shopify_order_id: int, name: str):
        order = _make_order(shopify_order_id=shopify_order_id, name=name)
        return _make_line_item(
            order,
            sku="ISBN001",
            quantity=7,
            shipped_quantity=2,
            confirmed_distributor="warehouse_ca",
            logistics_status="outbound_scheduled",
        )

    @pytest.mark.parametrize("bad_total", [None, "", "abc", "12abc", "  ", "#N/A"])
    def test_unparseable_total_never_completes_a_us_warehouse_line_item(self, bad_total):
        """T10-1: the exact hazard — a blank/garbage quantity on a US-warehouse
        LineItem must stay `invalid_total`, not close the shipment out."""
        li = self._us_warehouse_item(930001, "#T10BAD")

        result = _process_outbound_rows(
            [{"name": "#T10BAD", "sku": "ISBN001", "total": bad_total}]
        )

        li.refresh_from_db()
        assert li.shipped_quantity == 2
        assert li.shipped_at is None
        assert li.logistics_status == "outbound_scheduled"
        assert result["matched"] == []
        assert result["unmatched_count"] == 1
        assert result["unmatched"][0]["reason"] == "invalid_total"

    def test_missing_total_key_never_completes_a_us_warehouse_line_item(self):
        """T10-2: an absent key is a parse failure too, not an implicit 0."""
        li = self._us_warehouse_item(930002, "#T10MISSING")

        result = _process_outbound_rows([{"name": "#T10MISSING", "sku": "ISBN001"}])

        li.refresh_from_db()
        assert li.shipped_quantity == 2
        assert li.logistics_status == "outbound_scheduled"
        assert result["matched"] == []
        assert result["unmatched"][0]["reason"] == "invalid_total"

    @pytest.mark.parametrize("genuine_zero", [0, "0", " 0 ", 0.0, "00"])
    def test_a_genuinely_spelled_zero_still_completes_a_us_warehouse_line_item(
        self, genuine_zero
    ):
        """T10-3: the T9 feature is unchanged for input that really says zero.
        Any representation the parser can read as 0 counts — the distinction
        being drawn is parsed-vs-defaulted, not int-vs-str."""
        li = self._us_warehouse_item(930003, "#T10ZERO")

        result = _process_outbound_rows(
            [{"name": "#T10ZERO", "sku": "ISBN001", "total": genuine_zero}]
        )

        li.refresh_from_db()
        assert li.shipped_quantity == 7
        assert li.logistics_status == "shipped"
        assert li.shipped_at is not None
        assert result["unmatched"] == []
        assert result["matched_count"] == 1

    def test_parse_failure_is_rejected_before_grouping_not_absorbed_by_the_sum(self):
        """T10-4: placement matters. The rejection sits with the negative-row
        guard, BEFORE summation, so a garbage row is surfaced to the operator
        instead of vanishing as a silent +0 into a legitimate row's total."""
        li = self._us_warehouse_item(930004, "#T10MIX")

        result = _process_outbound_rows(
            [
                {"name": "#T10MIX", "sku": "ISBN001", "total": 3},
                {"name": "#T10MIX", "sku": "ISBN001", "total": None},
            ]
        )

        li.refresh_from_db()
        assert li.shipped_quantity == 5
        assert result["matched_count"] == 1
        assert result["matched"][0]["total"] == 3
        assert result["unmatched_count"] == 1
        assert result["unmatched"][0]["reason"] == "invalid_total"

    def test_blank_excel_total_cell_never_completes_a_us_warehouse_line_item(self):
        """T10-5: END-TO-END through the Excel path, which is where the hazard
        actually originates — an operator leaving a Total cell empty. The
        parser must carry the parse failure through to the matching layer
        rather than flattening it to a 0 that reads as a completion signal."""
        li = self._us_warehouse_item(930005, "#T10XLSX")

        result = _process_outbound_rows(
            parse_outbound_excel(_make_outbound_excel([("#T10XLSX", "ISBN001", None)]))
        )

        li.refresh_from_db()
        assert li.shipped_quantity == 2
        assert li.logistics_status == "outbound_scheduled"
        assert result["matched"] == []
        assert result["unmatched"][0]["reason"] == "invalid_total"

    def test_explicit_excel_zero_still_completes_a_us_warehouse_line_item(self):
        """T10-6: the counterpart — a cell the operator actually typed 0 into
        keeps working, so the Excel path retains the T9 capability."""
        li = self._us_warehouse_item(930006, "#T10XLSXZERO")

        result = _process_outbound_rows(
            parse_outbound_excel(_make_outbound_excel([("#T10XLSXZERO", "ISBN001", 0)]))
        )

        li.refresh_from_db()
        assert li.shipped_quantity == 7
        assert li.logistics_status == "shipped"
        assert result["matched_count"] == 1


# ---------------------------------------------------------------------------
# 환불(취소) 수량 차감 — 출고 용량 판정 (사용자 보고: 주문 #37830)
#
# 고객이 환불받은 수량은 출고할 물건이 아니므로 용량에서 빠진다. 표시/집계
# 경로가 전량 환불 품목을 제외하는 것과 같은 규칙을 수량 축에서 적용한 것.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOutboundRefundNetting:
    def _refund(self, line_item, quantity, shopify_refund_id=700001):
        return Refund.objects.create(
            order=line_item.order,
            shopify_refund_id=shopify_refund_id,
            line_item_id=line_item.shopify_line_item_id,
            quantity=quantity,
        )

    def test_partial_refund_reduces_capacity_and_completes_shipment(self):
        """수량 3 중 1 환불 -> 잔여 2를 출고하면 '출고' 완료다."""
        order = _make_order(shopify_order_id=700101, name="#700101")
        li = _make_line_item(order, sku="ISBN-PR", quantity=3)
        self._refund(li, 1)

        result = _process_outbound_rows([{"name": "#700101", "sku": "ISBN-PR", "total": 2}])

        li.refresh_from_db()
        assert result["matched_count"] == 1
        assert result["quantity_exceeded_count"] == 0
        assert li.shipped_quantity == 2
        assert li.logistics_status == "shipped"

    def test_fully_refunded_line_item_has_no_capacity(self):
        """전량 환불 품목은 출고 용량이 0 — 수량초과로 거부되고 무변경."""
        order = _make_order(shopify_order_id=700102, name="#700102")
        li = _make_line_item(order, sku="ISBN-FR", quantity=1)
        self._refund(li, 1, shopify_refund_id=700002)

        result = _process_outbound_rows([{"name": "#700102", "sku": "ISBN-FR", "total": 1}])

        li.refresh_from_db()
        assert result["matched_count"] == 0
        assert result["quantity_exceeded_count"] == 1
        assert li.shipped_quantity == 0
        assert li.logistics_status == "not_shipped"

    def test_unrefunded_line_item_capacity_unchanged(self):
        """환불이 없으면 기존 동작 그대로 (회귀 방지)."""
        order = _make_order(shopify_order_id=700103, name="#700103")
        li = _make_line_item(order, sku="ISBN-NR", quantity=3)

        result = _process_outbound_rows([{"name": "#700103", "sku": "ISBN-NR", "total": 3}])

        li.refresh_from_db()
        assert result["matched_count"] == 1
        assert li.shipped_quantity == 3
        assert li.logistics_status == "shipped"
