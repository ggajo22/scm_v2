"""SPEC-ORDER-017: rack-number upload batching (TDD).

`UploadRackNumberView` ran 3 DB queries per (order_name, sku) dedup key. This
SPEC extracts the dedup/batch-match/write logic into a module-level pure
function, `_process_rack_number_rows(rows) -> dict`, mirroring the
`_process_outbound_rows` (SPEC-ORDER-015) / `_process_force_outbound_rows`
(SPEC-ORDER-016) architecture, so the whole batch costs a fixed number of
queries regardless of key count.

Two call scopes are used below, matching acceptance.md's `[함수]` / `[뷰]`
markers:
  - function scope: calls `_process_rack_number_rows(rows)` directly — no
    HTTP request, no `JWTAuthentication` user-lookup query.
  - view scope: calls `auth_client.post(UPLOAD_RACK_NUMBER_URL, ...)`.

Coverage targets:
  T1  2-key vs 10-key query count equality (REQ-RACKBATCH-002, AC-001) [함수]
  T2  10-key fully-matched batch query count <= 6 (REQ-RACKBATCH-001, AC-001)
      [함수]
  T3  10-key all-unmatched-via-absent-Order batch query count <= 4
      (REQ-RACKBATCH-001, AC-001) [함수]
  T4  empty batch query count <= 2 (REQ-RACKBATCH-001, AC-001) [함수]
  T5  duplicate Order.name resolves to the lowest pk, even when that Order
      was created LATER (REQ-RACKBATCH-004, AC-003) [함수]
  T6  blank order-identifier rows with the SAME sku are not merged
      (REQ-RACKBATCH-005, AC-007) [함수]
  T7  bulk_update's already-executed write is rolled back by
      transaction.atomic() when a later exception is injected
      (REQ-RACKBATCH-013, AC-012) [함수]
  T8  UPDATE statement's SET clause assigns only rack_number + all other
      LineItem fields stay byte-identical (REQ-RACKBATCH-014, AC-011) [함수]
  T9  empty-string rack_number clears the field instead of being skipped
      (REQ-RACKBATCH-007, AC-004) [뷰]
  T10 response body key set is exactly {matched_count, skipped_count}
      (REQ-RACKBATCH-008, AC-010) [뷰]
  T11 unhandled exception inside _process_rack_number_rows surfaces as
      HTTP 500 (REQ-RACKBATCH-015, AC-009) [함수+뷰]
"""

import io
import re
from decimal import Decimal
from unittest.mock import patch

import openpyxl
import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import LineItem, Order
from order.purchase_order_views import _process_rack_number_rows

User = get_user_model()

UPLOAD_RACK_NUMBER_URL = "/api/purchase-orders/upload-rack-number/"


def _make_order(shopify_order_id: int, store_type: str = "gimssine", **kwargs) -> Order:
    return Order.objects.create(shopify_order_id=shopify_order_id, store_type=store_type, **kwargs)


def _make_line_item(
    order: Order, shopify_line_item_id: int = 1, sku: str = "SKU-RACKBATCH-001", **kwargs
) -> LineItem:
    defaults = {"quantity": 1, "title": "Test Book"}
    defaults.update(kwargs)
    return LineItem.objects.create(
        order=order, shopify_line_item_id=shopify_line_item_id, sku=sku, **defaults
    )


def _make_rack_excel(rows: list[tuple], header: tuple = ("주문번호", "SKU", "렉번호")) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(list(header))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _file_obj(file_bytes: bytes, name: str = "rack-upload.xlsx"):
    f = io.BytesIO(file_bytes)
    f.name = name
    return f


@pytest.fixture
def user(db):
    return User.objects.create_user(username="spec017_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ---------------------------------------------------------------------------
# T1-T4 — batched DB access (function scope; mirrors
# test_spec_015.py:1104-1157's _seed_outbound_groups/_count_queries technique)
# ---------------------------------------------------------------------------


def _seed_rack_rows(n: int, offset: int = 0) -> list[dict]:
    """Create `n` Orders, each with exactly one matching LineItem, and
    return the parsed-row dicts that target them (one distinct dedup key
    per Order)."""
    rows = []
    for i in range(n):
        seq = offset + i
        name = f"#RACKQ{seq:05d}"
        sku = f"ISBNRACKQ{seq:05d}"
        order = _make_order(shopify_order_id=970_000_000 + seq, name=name)
        _make_line_item(order, shopify_line_item_id=970_000_000 + seq, sku=sku, quantity=10)
        rows.append({"order_name": name, "sku": sku, "rack_number": f"R-{seq:05d}"})
    return rows


def _count_queries(rows: list[dict]) -> int:
    with CaptureQueriesContext(connection) as ctx:
        _process_rack_number_rows(rows)
    return len(ctx.captured_queries)


@pytest.mark.django_db
class TestRackNumberQueryCountIsIndependentOfKeyCount:
    """Response time must not scale with the number of uploaded dedup keys.

    The discriminating assertion is the EQUALITY between a 2-key batch and a
    10-key batch (T1) — any per-key query at all makes those two numbers
    differ, regardless of what the absolute constant happens to be. T2-T4
    pin the absolute ceilings derived from `_process_rack_number_rows`'s own
    guard structure (spec.md AC-RACKBATCH-001).
    """

    def test_query_count_is_identical_for_2_and_for_10_keys(self):
        two = _count_queries(_seed_rack_rows(2, offset=0))
        ten = _count_queries(_seed_rack_rows(10, offset=100))

        assert two == ten, (
            f"query count scales with input size: 2 keys -> {two} queries, "
            f"10 keys -> {ten} queries"
        )

    def test_query_count_stays_within_a_small_fixed_bound_when_all_match(self):
        """savepoint + Order fetch + LineItem fetch + bulk_update + release
        = 5 actual queries, +1 safety margin (test_spec_015.py:1143-1147)."""
        assert _count_queries(_seed_rack_rows(10, offset=200)) <= 6

    def test_all_unmatched_via_absent_order_stays_within_bound(self):
        """Every row targets an Order.name that does not exist at all (not
        an unmatched SKU on an existing Order) -- the LineItem lookup must
        be skipped entirely. savepoint + Order fetch + release = 3 actual,
        +1 margin (test_spec_015.py:1149-1153)."""
        rows = [
            {"order_name": f"#RACKMISSING{i}", "sku": "ISBN-ANY", "rack_number": "X"}
            for i in range(10)
        ]

        assert _count_queries(rows) <= 4

    def test_an_empty_batch_touches_the_database_at_most_for_the_transaction(self):
        """savepoint + release = 2, no margin (test_spec_015.py:1155-1157)."""
        assert _count_queries([]) <= 2


# ---------------------------------------------------------------------------
# T5-T6 — matching/dedup semantics (function scope)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRackNumberTieBreakAndDedupSemantics:
    def test_duplicate_order_names_resolve_to_the_lowest_pk_order_created_later(self):
        """REQ-RACKBATCH-004/AC-RACKBATCH-003. The reference tie-break test
        (test_spec_015.py:1166-1186) creates its lower-pk Order FIRST, so pk
        order and creation order coincide there and it cannot prove the
        implementation keys off `pk` rather than creation order
        (SPEC-ORDER-017 spec.md D21). This fixture deliberately inverts
        them: the lower-pk Order is created SECOND, via an explicit pk far
        outside the normal autoincrement range so it cannot collide with
        any other row. O1/O2 hold disjoint SKU sets, so a wrong Order pick
        would leave the row unmatched rather than silently matching."""
        order_high_pk_created_first = Order.objects.create(
            pk=970_500_001,
            shopify_order_id=970_500_001,
            store_type="gimssine",
            name="#RACKTIE",
        )
        order_low_pk_created_second = Order.objects.create(
            pk=970_500_000,
            shopify_order_id=970_500_000,
            store_type="gimssine",
            name="#RACKTIE",
        )
        assert order_low_pk_created_second.pk < order_high_pk_created_first.pk

        li_low = _make_line_item(
            order_low_pk_created_second, shopify_line_item_id=1, sku="SKU-TIE-LOW"
        )
        li_high = _make_line_item(
            order_high_pk_created_first, shopify_line_item_id=1, sku="SKU-TIE-HIGH"
        )

        result = _process_rack_number_rows(
            [{"order_name": "#RACKTIE", "sku": "SKU-TIE-LOW", "rack_number": "B-01"}]
        )

        li_low.refresh_from_db()
        li_high.refresh_from_db()
        assert result["matched_count"] == 1
        assert result["skipped_count"] == 0
        assert li_low.rack_number == "B-01"
        assert li_high.rack_number == ""

    def test_blank_order_identifier_rows_with_same_sku_are_not_merged(self):
        """REQ-RACKBATCH-005/AC-RACKBATCH-007 (spec.md D4-R). The two blank
        rows deliberately share one SKU -- a `(None, sku)`-keyed
        implementation would collapse them into a single key and report
        skipped_count == 1; only a correct `(None, idx)` implementation
        reports 2."""
        order = _make_order(shopify_order_id=970_500_100, name="#RACKBLANK")
        li = _make_line_item(order, shopify_line_item_id=1, sku="SKU-RACKBLANK-VALID")

        rows = [
            {"order_name": None, "sku": "SKU-RACKBLANK-SHARED", "rack_number": "X"},
            {"order_name": None, "sku": "SKU-RACKBLANK-SHARED", "rack_number": "Y"},
            {"order_name": "#RACKBLANK", "sku": "SKU-RACKBLANK-VALID", "rack_number": "Z"},
        ]

        result = _process_rack_number_rows(rows)

        assert result["matched_count"] == 1
        assert result["skipped_count"] == 2
        li.refresh_from_db()
        assert li.rack_number == "Z"


# ---------------------------------------------------------------------------
# T7-T8 — atomicity and write scope (function scope)
# ---------------------------------------------------------------------------


def _assigned_columns(sql: str) -> list[str]:
    """Extract the left-hand-side column names of a bulk_update UPDATE
    statement's SET clause, e.g. ["rack_number"] for
    'SET `rack_number` = CASE WHEN `id` = ... THEN ... END WHERE ...'.
    Deliberately matches only `<col> = CASE` assignment targets, NOT `id`
    inside the `WHEN `id` = ...` condition (spec.md D17/AC-RACKBATCH-011a)
    -- Django's bulk_update renders the PK inside the CASE WHEN condition,
    not as a SET assignment target (research.md §11, Django 5.1.6
    django/db/models/query.py:897)."""
    set_clause = sql.split(" SET ", 1)[1].rsplit(" WHERE ", 1)[0]
    return re.findall(r'[`"]?(\w+)[`"]?\s*=\s*CASE', set_clause)


@pytest.mark.django_db
class TestRackNumberWriteScopeAndAtomicity:
    def test_bulk_update_already_executed_write_is_rolled_back_on_later_failure(self):
        """REQ-RACKBATCH-013/AC-RACKBATCH-012. The exception is injected
        AFTER the real bulk_update() has actually run the UPDATE, but
        before transaction.atomic() exits -- an injection point BEFORE the
        write (as in an earlier SPEC draft) cannot distinguish atomic from
        non-atomic, because nothing has been written yet either way."""
        order = _make_order(shopify_order_id=970_500_200, name="#RACKATOMIC")
        li1 = _make_line_item(
            order, shopify_line_item_id=1, sku="SKU-ATOMIC-1", rack_number="OLD-1"
        )
        li2 = _make_line_item(
            order, shopify_line_item_id=2, sku="SKU-ATOMIC-2", rack_number="OLD-2"
        )
        rows = [
            {"order_name": "#RACKATOMIC", "sku": "SKU-ATOMIC-1", "rack_number": "NEW-1"},
            {"order_name": "#RACKATOMIC", "sku": "SKU-ATOMIC-2", "rack_number": "NEW-2"},
        ]

        original_bulk_update = LineItem.objects.bulk_update

        def _bulk_update_then_raise(objs, fields, **kwargs):
            original_bulk_update(objs, fields, **kwargs)
            raise RuntimeError("boom after write")

        with patch.object(LineItem.objects, "bulk_update", side_effect=_bulk_update_then_raise):
            with pytest.raises(RuntimeError):
                _process_rack_number_rows(rows)

        # Fresh reads, outside the now-rolled-back transaction.atomic()
        # savepoint -- if transaction.atomic() were absent, the already-
        # executed UPDATE would still be visible here.
        li1_after = LineItem.objects.get(pk=li1.pk)
        li2_after = LineItem.objects.get(pk=li2.pk)
        assert li1_after.rack_number == "OLD-1"
        assert li2_after.rack_number == "OLD-2"

    def test_sql_set_clause_and_field_snapshot_show_only_rack_number_changes(self):
        """REQ-RACKBATCH-014/AC-RACKBATCH-011. Two independent Thens: (a)
        SQL-level -- the only column ASSIGNED in the UPDATE's SET clause is
        rack_number; (b) value-level -- every other seeded field is
        byte-identical before/after. (a) alone catches an over-broad
        bulk_update field list that (b) cannot (bulk_update writes back the
        just-read value, producing an empty diff for an extra field)."""
        order = _make_order(shopify_order_id=970_500_300, name="#RACKWRITESCOPE")
        li = _make_line_item(
            order,
            shopify_line_item_id=1,
            sku="SKU-WRITE-SCOPE",
            rack_number="OLD-LOC",
            title="Original Title",
            quantity=7,
            price=Decimal("12.34"),
            purchase_status="in_stock",
            logistics_status="shipped",
            shipped_quantity=3,
            shipped_at=timezone.now(),
        )
        before = {
            "title": li.title,
            "quantity": li.quantity,
            "price": li.price,
            "purchase_status": li.purchase_status,
            "logistics_status": li.logistics_status,
            "shipped_quantity": li.shipped_quantity,
            "shipped_at": li.shipped_at,
        }
        rows = [
            {"order_name": "#RACKWRITESCOPE", "sku": "SKU-WRITE-SCOPE", "rack_number": "NEW-LOC"}
        ]

        with CaptureQueriesContext(connection) as ctx:
            result = _process_rack_number_rows(rows)

        update_queries = [
            q["sql"] for q in ctx.captured_queries if q["sql"].strip().upper().startswith("UPDATE")
        ]
        assert len(update_queries) == 1
        assert _assigned_columns(update_queries[0]) == ["rack_number"]

        assert result["matched_count"] == 1
        li.refresh_from_db()
        assert li.rack_number == "NEW-LOC"
        after = {
            "title": li.title,
            "quantity": li.quantity,
            "price": li.price,
            "purchase_status": li.purchase_status,
            "logistics_status": li.logistics_status,
            "shipped_quantity": li.shipped_quantity,
            "shipped_at": li.shipped_at,
        }
        assert before == after


# ---------------------------------------------------------------------------
# T9-T11 — response/error-path contract preservation (view scope)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUploadRackNumberViewBatchedContract:
    def test_empty_string_rack_number_clears_existing_value(self, auth_client):
        """REQ-RACKBATCH-007/AC-RACKBATCH-004. No existing test in
        test_spec_013.py verifies this at the view level (spec.md D3) --
        test_spec_013.py:467 only exercises the parser, which never reaches
        the view."""
        order = _make_order(shopify_order_id=970_500_400, name="#RACKCLEAR")
        li = _make_line_item(
            order, shopify_line_item_id=1, sku="SKU-RACKCLEAR", rack_number="A-01"
        )
        file_bytes = _make_rack_excel([("#RACKCLEAR", "SKU-RACKCLEAR", "")])
        f = _file_obj(file_bytes)

        res = auth_client.post(UPLOAD_RACK_NUMBER_URL, {"file": f}, format="multipart")

        assert res.status_code == 200
        assert res.data["matched_count"] == 1
        li.refresh_from_db()
        assert li.rack_number == ""

    def test_response_key_set_is_exactly_matched_and_skipped_count(self, auth_client):
        """REQ-RACKBATCH-008/AC-RACKBATCH-010 (spec.md D13). The existing
        test_upload_matches_and_updates_lineitem (test_spec_013.py:664)
        only asserts individual key VALUES, so an added third response
        field would pass it unnoticed."""
        order = _make_order(shopify_order_id=970_500_500, name="#RACKKEYSET")
        _make_line_item(order, shopify_line_item_id=1, sku="SKU-RACKKEYSET")
        file_bytes = _make_rack_excel([("#RACKKEYSET", "SKU-RACKKEYSET", "K-01")])
        f = _file_obj(file_bytes)

        res = auth_client.post(UPLOAD_RACK_NUMBER_URL, {"file": f}, format="multipart")

        assert res.status_code == 200
        assert set(res.data.keys()) == {"matched_count", "skipped_count"}

    def test_unhandled_exception_inside_process_function_returns_500(self, auth_client):
        """REQ-RACKBATCH-015/AC-RACKBATCH-009. Injection happens inside
        `_process_rack_number_rows` (function level); the 500 is observed
        through the view (AC's `[함수+뷰]` scope). This does not prove
        atomicity -- see the dedicated bulk_update-then-raise test above."""
        order = _make_order(shopify_order_id=970_500_600, name="#RACKBOOM")
        _make_line_item(order, shopify_line_item_id=1, sku="SKU-RACKBOOM")
        file_bytes = _make_rack_excel([("#RACKBOOM", "SKU-RACKBOOM", "X-01")])
        f = _file_obj(file_bytes)

        with patch(
            "order.purchase_order_views._resolve_orders_by_name",
            side_effect=RuntimeError("boom"),
        ):
            res = auth_client.post(UPLOAD_RACK_NUMBER_URL, {"file": f}, format="multipart")

        assert res.status_code == 500
