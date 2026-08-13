"""
TDD tests for SPEC-ORDER-018 — 보류/제외 품목 발주 대상 복구.

Coverage targets:
  T1   AC-RESTORE-001  REQ-RESTORE-001/002  exactly the 4 excluded states are
                       returned out of 7, and the request writes nothing
  T2   AC-RESTORE-002  REQ-RESTORE-004      null-SKU LineItems are omitted
  T3   AC-RESTORE-003  REQ-RESTORE-005      refund netting: fully refunded is
                       dropped, unrefunded NULL-quantity is kept
  T4   AC-RESTORE-004  REQ-RESTORE-003/006/007  response envelope, field set,
                       deterministic ordering across a created_at tie
  T5   AC-RESTORE-005  REQ-RESTORE-008      unauthenticated -> 401, no leakage
  T6   AC-RESTORE-006  REQ-RESTORE-009/010  unordered list + daily-review upload
                       matching are unchanged by this SPEC
  T7   AC-RESTORE-007  REQ-RESTORE-011      the unordered endpoint issues the
                       same number of queries with and without excluded items
  T8   AC-RESTORE-008  REQ-RESTORE-014      order_cancelled restore flips
                       ready_to_ship true->false, leaves Order.status alone
  T9   AC-RESTORE-009  REQ-RESTORE-014      on_hold restore is a no-op for both
                       aggregates; cs_required restore lifts ready_to_ship
  T10  AC-RESTORE-010  REQ-RESTORE-012/013/015  restore writes purchase_status
                       only and never touches LineItemNote (both endpoints)
  T11  AC-RESTORE-011  REQ-RESTORE-022      a PurchaseOrder-linked item stays
                       out of the reorder queue after restore (known limit)

T6~T11 characterize behaviour that must already hold: T6/T7 prove the shared
`_reorder_candidate_filter` read path is untouched, and T8~T11 pin the current
behaviour of the two pre-existing purchase_status write endpoints. None of them
may require a production-code change to pass.
"""

import io
from datetime import datetime, timezone
from unittest.mock import patch

import openpyxl
import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import LineItem, LineItemNote, Order, PurchaseOrder, Refund
from order.purchase_order_views import ExcludedItemsView, _recompute_order_aggregates

User = get_user_model()

EXCLUDED_URL = "/api/purchase-orders/excluded-items/"
UNORDERED_URL = "/api/purchase-orders/unordered/"
LINE_ITEM_STATUS_URL = "/api/purchase-orders/line-items/{pk}/status/"
BULK_STATUS_URL = "/api/purchase-orders/line-items/bulk-status/"
UPLOAD_DAILY_URL = "/api/purchase-orders/upload-daily-review/"

# The four purchase_status codes this SPEC makes visible again
# (models.py PURCHASE_STATUS_CHOICES).
EXCLUDED_STATUSES = ("on_hold", "order_cancelled", "cs_required", "other_publisher")

# Queries GET /api/purchase-orders/unordered/ issues once the auth machinery
# is warm: 1 JWT user lookup + the 2 the view already issued before
# SPEC-ORDER-018. Pinned exactly so that ANY query added to a pre-existing
# endpoint fails REQ-RESTORE-011 — a with/without comparison alone cannot,
# because a constant addition lands in both measurements and cancels.
UNORDERED_ENDPOINT_QUERY_COUNT = 3


# ---------------------------------------------------------------------------
# Fixtures / helpers (mirrors test_purchase_orders.py:72/:77/:85/:89/:97)
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="spec018_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def anon_client():
    return APIClient()


def _make_order(
    shopify_order_id: int = 918001,
    store_type: str = "gimssine",
    name: str | None = "#9180",
    shopify_created_at: datetime | None = None,
) -> Order:
    return Order.objects.create(
        shopify_order_id=shopify_order_id,
        store_type=store_type,
        name=name,
        shopify_created_at=shopify_created_at,
    )


def _make_line_item(
    order: Order,
    shopify_line_item_id: int = 1,
    sku: str | None = "9788901234567",
    title: str = "테스트 도서",
    vendor: str = "처음교육",
    quantity: int | None = 2,
    purchase_status: str = "unordered",
    **kwargs,
) -> LineItem:
    return LineItem.objects.create(
        order=order,
        shopify_line_item_id=shopify_line_item_id,
        sku=sku,
        title=title,
        vendor=vendor,
        quantity=quantity,
        purchase_status=purchase_status,
        **kwargs,
    )


def _make_daily_review_excel(rows: list[dict]) -> bytes:
    """Daily Review .xlsx with the standard headers.

    Same column layout as test_daily_review_upload.py's helper — kept local
    to this suite because cross-suite helper imports are not the convention
    here (each suite defines its own fixtures/helpers).
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "주문번호", "ISBN", "제목", "수량", "주문위치", "메모",
        "재고(한국)", "재고(CA)", "재고(NJ)",
        "북센 공급가", "교보 공급가",
        "북센 재고수량", "북센 재고상태",
        "교보 재고수량", "교보 재고상태",
        "공급가차이", "북센 입고예정", "북센 반품가능여부",
        "교보 출고여부", "교보 반품가능여부",
        "가격차이알림", "출판사", "선택근거", "선택",
    ])
    for row in rows:
        ws.append([
            row.get("order_name", "#9180"),
            row.get("isbn", ""),
            row.get("title", ""),
            row.get("quantity", 1),
            "",
            row.get("note", ""),
            row.get("korea_stock", 0),
            row.get("ca_stock", 0),
            row.get("nj_stock", 0),
            row.get("bs_price", ""),
            "", "", "", "", "", "", "", "", "", "", "", "", "",
            row.get("selected", ""),
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# T1~T5 — the new read-only excluded-items endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExcludedItemsViewSelection:
    """AC-RESTORE-001/002/003 — which rows come back."""

    def test_returns_exactly_the_four_excluded_statuses_and_writes_nothing(
        self, auth_client
    ):
        """T1 (AC-RESTORE-001) — REQ-RESTORE-001/002."""
        order = _make_order()
        statuses = [
            ("unordered", "SKU-UNORDERED"),
            ("on_hold", "SKU-HOLD"),
            ("order_cancelled", "SKU-CANCEL"),
            ("other_publisher", "SKU-OTHERPUB"),
            ("cs_required", "SKU-CS"),
            ("in_stock", "SKU-STOCK"),
            ("damaged_exchange", "SKU-DMG"),
        ]
        for idx, (status_code, sku) in enumerate(statuses, start=1):
            _make_line_item(
                order,
                shopify_line_item_id=idx,
                sku=sku,
                quantity=1,
                purchase_status=status_code,
            )

        before = list(LineItem.objects.order_by("pk").values())
        note_count_before = LineItemNote.objects.count()
        po_count_before = PurchaseOrder.objects.count()
        order_count_before = Order.objects.count()

        res = auth_client.get(EXCLUDED_URL)

        assert res.status_code == 200
        assert {row["sku"] for row in res.data["results"]} == {
            "SKU-HOLD",
            "SKU-CANCEL",
            "SKU-OTHERPUB",
            "SKU-CS",
        }
        assert len(res.data["results"]) == 4

        # No write of any kind (REQ-RESTORE-001).
        assert list(LineItem.objects.order_by("pk").values()) == before
        assert LineItemNote.objects.count() == note_count_before
        assert PurchaseOrder.objects.count() == po_count_before
        assert Order.objects.count() == order_count_before

    def test_line_item_without_sku_is_omitted(self, auth_client):
        """T2 (AC-RESTORE-002) — REQ-RESTORE-004."""
        order = _make_order()
        li_nosku = _make_line_item(
            order, shopify_line_item_id=1, sku=None, quantity=1, purchase_status="on_hold"
        )
        _make_line_item(
            order,
            shopify_line_item_id=2,
            sku="SKU-HAS",
            quantity=1,
            purchase_status="on_hold",
        )

        res = auth_client.get(EXCLUDED_URL)

        assert res.status_code == 200
        assert len(res.data["results"]) == 1
        assert res.data["results"][0]["sku"] == "SKU-HAS"
        assert li_nosku.pk not in {row["id"] for row in res.data["results"]}

    def test_refund_netting_drops_only_fully_refunded_rows(self, auth_client):
        """T3 (AC-RESTORE-003) — REQ-RESTORE-005.

        Discriminates the guarded netting skip
        (`if li.refunded_qty and net_qty == 0`) from UnorderedItemsView's
        unconditional `if net_qty == 0` — the latter would also drop the
        unrefunded NULL-quantity row (spec.md 설계 결정 D).
        """
        order = _make_order()
        li_partial = _make_line_item(
            order,
            shopify_line_item_id=11,
            sku="SKU-PARTIAL",
            quantity=5,
            purchase_status="order_cancelled",
        )
        li_full = _make_line_item(
            order,
            shopify_line_item_id=12,
            sku="SKU-FULL",
            quantity=3,
            purchase_status="order_cancelled",
        )
        _make_line_item(
            order,
            shopify_line_item_id=13,
            sku="SKU-NULLQTY",
            quantity=None,
            purchase_status="order_cancelled",
        )

        # Refund rows key on (order_id, Shopify line_item_id), not local pk.
        Refund.objects.create(
            order=order,
            shopify_refund_id=1,
            line_item_id=li_partial.shopify_line_item_id,
            quantity=2,
        )
        Refund.objects.create(
            order=order,
            shopify_refund_id=2,
            line_item_id=li_full.shopify_line_item_id,
            quantity=3,
        )

        res = auth_client.get(EXCLUDED_URL)

        assert res.status_code == 200
        by_sku = {row["sku"]: row for row in res.data["results"]}
        assert set(by_sku) == {"SKU-PARTIAL", "SKU-NULLQTY"}
        assert by_sku["SKU-PARTIAL"]["quantity"] == 3
        assert by_sku["SKU-NULLQTY"]["quantity"] == 0


@pytest.mark.django_db
class TestExcludedItemsViewResponseContract:
    """AC-RESTORE-004/005 — envelope, fields, ordering, auth."""

    def test_envelope_fields_and_deterministic_order(self, auth_client):
        """T4 (AC-RESTORE-004) — REQ-RESTORE-003/006/007."""
        tie_ts = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
        # 10 items across 5 orders with distinct timestamps ...
        line_no = 0
        for order_idx in range(5):
            order = _make_order(
                shopify_order_id=918100 + order_idx,
                name=f"#918{order_idx}",
                shopify_created_at=datetime(
                    2026, 4, order_idx + 1, 9, 0, 0, tzinfo=timezone.utc
                ),
            )
            for j in range(2):
                line_no += 1
                _make_line_item(
                    order,
                    shopify_line_item_id=line_no,
                    sku=f"SKU-{line_no:03d}",
                    title=f"도서 {line_no}",
                    vendor="처음교육",
                    quantity=1,
                    purchase_status=EXCLUDED_STATUSES[line_no % 4],
                )
        # ... plus 2 items on two DIFFERENT orders sharing one timestamp,
        # which is what makes a single-key ordering non-deterministic.
        for order_idx in (5, 6):
            order = _make_order(
                shopify_order_id=918100 + order_idx,
                name=f"#918{order_idx}",
                shopify_created_at=tie_ts,
            )
            line_no += 1
            _make_line_item(
                order,
                shopify_line_item_id=line_no,
                sku=f"SKU-{line_no:03d}",
                title=f"도서 {line_no}",
                vendor="처음교육",
                quantity=1,
                purchase_status="on_hold",
            )

        first = auth_client.get(EXCLUDED_URL)
        second = auth_client.get(EXCLUDED_URL)

        assert first.status_code == 200
        assert second.status_code == 200
        # (a) envelope has exactly count/results — no page cursor.
        assert set(first.data.keys()) == {"count", "results"}
        assert set(second.data.keys()) == {"count", "results"}
        # (b) count matches the returned rows.
        assert first.data["count"] == len(first.data["results"]) == 12
        # (c) every row carries the contracted field set.
        for row in first.data["results"]:
            assert set(row.keys()) >= {
                "id",
                "order_name",
                "sku",
                "title",
                "vendor",
                "quantity",
                "purchase_status",
            }
        # (d) two identical requests return an identical row order.
        assert [row["id"] for row in first.data["results"]] == [
            row["id"] for row in second.data["results"]
        ]
        # (e) the emitted ORDER BY carries BOTH keys.
        #
        # (d) alone cannot fail: plan-audit SPEC-ORDER-018-review-1 (D1)
        # dropped `"pk"` from the view's .order_by() and this test still
        # passed, because MySQL happens to return these ties in pk order
        # anyway. "Two runs agreed" is a property of the sample, not of the
        # query — an implementation with no tie-break at all satisfies it.
        # Asserting the SQL the ORM actually emitted does fail when the
        # tie-break is removed, which is the property REQ-RESTORE-007 asks
        # for. Same SQL-level technique as test_spec_017.py's write-scope
        # assertion.
        with CaptureQueriesContext(connection) as ctx:
            auth_client.get(EXCLUDED_URL)
        ordered_selects = [
            q["sql"]
            for q in ctx.captured_queries
            if "orders_line_item" in q["sql"] and " ORDER BY " in q["sql"]
        ]
        assert len(ordered_selects) == 1, ordered_selects
        order_by = ordered_selects[0].rsplit(" ORDER BY ", 1)[1]
        terms = [t.strip() for t in order_by.split(",")]
        assert len(terms) == 2, f"tie-break이 없다 — ORDER BY {order_by}"
        assert "shopify_created_at" in terms[0], order_by
        assert "DESC" in terms[0].upper(), order_by
        assert "id" in terms[1], order_by

    def test_unauthenticated_request_is_rejected_without_leaking_data(
        self, anon_client
    ):
        """T5 (AC-RESTORE-005) — REQ-RESTORE-008."""
        order = _make_order()
        li = _make_line_item(
            order,
            shopify_line_item_id=1,
            sku="SKU-SECRET",
            title="Secret Book",
            quantity=1,
            purchase_status="on_hold",
        )

        res = anon_client.get(EXCLUDED_URL)

        assert res.status_code == 401
        body = res.content.decode()
        assert "SKU-SECRET" not in body
        assert "Secret Book" not in body
        assert str(li.pk) not in body


# ---------------------------------------------------------------------------
# T6~T7 — the pre-existing reorder path is untouched
#
# Both tests characterize behaviour that already holds. If either fails, this
# SPEC's implementation widened the shared `_reorder_candidate_filter` or one
# of its four call sites — fix the implementation, never these tests.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExistingReorderPathUnchanged:
    """AC-RESTORE-006/007 — REQ-RESTORE-009/010/011."""

    def test_unordered_list_and_daily_review_upload_still_skip_excluded_items(
        self, auth_client
    ):
        """T6 (AC-RESTORE-006) — REQ-RESTORE-009/010."""
        order = _make_order(name="#9180")
        _make_line_item(
            order, shopify_line_item_id=1, sku="SKU-A", quantity=1,
            purchase_status="unordered",
        )
        excluded = {}
        for idx, status_code in enumerate(
            ("on_hold", "order_cancelled", "cs_required", "other_publisher"), start=2
        ):
            sku = f"SKU-{chr(ord('A') + idx - 1)}"  # SKU-B .. SKU-E
            excluded[sku] = _make_line_item(
                order,
                shopify_line_item_id=idx,
                sku=sku,
                quantity=1,
                purchase_status=status_code,
            )

        # (1) the unordered list returns only the unordered item.
        res_unordered = auth_client.get(UNORDERED_URL)
        assert res_unordered.status_code == 200
        assert {row["sku"] for row in res_unordered.data["results"]} == {"SKU-A"}

        # (2) a daily-review upload naming SKU-B..SKU-E matches nothing.
        file_bytes = _make_daily_review_excel([
            {"order_name": "#9180", "isbn": sku, "selected": "북센"}
            for sku in sorted(excluded)
        ])
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = "daily_review.xlsx"
        res_upload = auth_client.post(
            UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart"
        )
        assert res_upload.status_code == 201
        assert res_upload.data["confirmed_count"] == 0
        assert res_upload.data["skipped_count"] == 4

        # (3) none of the four rows was written to.
        expected = {
            "SKU-B": "on_hold",
            "SKU-C": "order_cancelled",
            "SKU-D": "cs_required",
            "SKU-E": "other_publisher",
        }
        for sku, li in excluded.items():
            li.refresh_from_db()
            assert li.purchase_status == expected[sku]
            assert li.confirmed_distributor is None
            assert li.confirmed_price is None
            assert li.purchase_orders.count() == 0

    def test_unordered_endpoint_query_count_is_unaffected_by_excluded_items(
        self, auth_client
    ):
        """T7 (AC-RESTORE-007, first clause) — REQ-RESTORE-011.

        Asserts BOTH that excluded rows change nothing (the with/without
        equivalence) AND that the absolute count is unchanged. The second
        half is what gives this test discriminating power — see (b) below.
        """
        order = _make_order()
        for idx in range(3):
            _make_line_item(
                order,
                shopify_line_item_id=idx + 1,
                sku=f"SKU-U{idx}",
                quantity=1,
                purchase_status="unordered",
            )

        # Warm the auth/JWT machinery so first-request-only lookups do not
        # land inside the measured window asymmetrically.
        auth_client.get(UNORDERED_URL)

        with CaptureQueriesContext(connection) as ctx_a:
            res_a = auth_client.get(UNORDERED_URL)
        queries_without_excluded = len(ctx_a.captured_queries)

        for idx in range(8):
            _make_line_item(
                order,
                shopify_line_item_id=100 + idx,
                sku=f"SKU-X{idx}",
                quantity=1,
                purchase_status=EXCLUDED_STATUSES[idx % 4],
            )

        with CaptureQueriesContext(connection) as ctx_b:
            res_b = auth_client.get(UNORDERED_URL)
        queries_with_excluded = len(ctx_b.captured_queries)

        # (a) the original property: excluded rows change nothing.
        assert queries_without_excluded == queries_with_excluded
        assert len(res_a.data["results"]) == 3
        assert len(res_b.data["results"]) == 3

        # (b) the count is pinned EXACTLY, not merely to itself.
        #
        # (a) alone cannot fail the thing REQ-RESTORE-011 forbids. A query
        # added to UnorderedItemsView lands in BOTH measurements and cancels
        # — plan-audit SPEC-ORDER-018-review-1 (D2) leaked an extra query
        # into the view and (a) still passed. Pinning the absolute number
        # makes any added query fail, which is what "no existing endpoint
        # issues a different number of database queries as a result of this
        # SPEC" actually asks for.
        #
        # The 3 are: the JWT user lookup (warmed above, but still one per
        # request), plus the two this view issued before SPEC-ORDER-018.
        # To re-derive after an intentional change, temporarily assert a
        # wrong value and read the reported count.
        assert queries_without_excluded == UNORDERED_ENDPOINT_QUERY_COUNT
        assert queries_with_excluded == UNORDERED_ENDPOINT_QUERY_COUNT

        # (c) no query the unordered endpoint issues may mention an excluded
        # status. This is the clause that catches a widened
        # _reorder_candidate_filter — the failure mode REQ-RESTORE-009/010
        # guard behaviourally, caught here at the SQL level as well.
        for q in ctx_b.captured_queries:
            for status in EXCLUDED_STATUSES:
                assert f"'{status}'" not in q["sql"], (status, q["sql"])

    def test_the_new_view_is_absent_from_the_pre_existing_call_graph(
        self, auth_client
    ):
        """T7b (AC-RESTORE-007, second clause) — REQ-RESTORE-011.

        AC-RESTORE-007 also says "the new read view shall not appear in the
        call graph of any pre-existing endpoint". Nothing tested that clause
        (plan-audit SPEC-ORDER-018-review-1). A spy on the new view is the
        direct check: reusing it from an existing endpoint — the obvious way
        someone would "share" the excluded-items logic later — trips this.
        """
        order = _make_order()
        _make_line_item(
            order,
            shopify_line_item_id=1,
            sku="SKU-U0",
            quantity=1,
            purchase_status="unordered",
        )
        _make_line_item(
            order,
            shopify_line_item_id=2,
            sku="SKU-X0",
            quantity=1,
            purchase_status="on_hold",
        )

        with patch.object(
            ExcludedItemsView, "get", autospec=True
        ) as spy:
            res = auth_client.get(UNORDERED_URL)

        assert res.status_code == 200
        assert [row["sku"] for row in res.data["results"]] == ["SKU-U0"]
        spy.assert_not_called()


# ---------------------------------------------------------------------------
# T8~T11 — restore side effects on the PRE-EXISTING write endpoints
#
# These characterize what LineItemStatusUpdateView and
# LineItemBulkStatusUpdateView already do. They must pass without any backend
# production-code change (REQ-RESTORE-012). A failure here means spec.md's
# 설계 결정 C or E got a fact wrong — correct the SPEC, not the endpoint.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRestoreOrderAggregateSideEffects:
    """AC-RESTORE-008/009 — REQ-RESTORE-014."""

    def test_order_cancelled_restore_flips_ready_to_ship_and_keeps_status(
        self, auth_client
    ):
        """T8 (AC-RESTORE-008) — REQ-RESTORE-014."""
        order = _make_order()
        _make_line_item(
            order,
            shopify_line_item_id=1,
            sku="SKU-READY",
            quantity=1,
            purchase_status="unordered",
            logistics_status="received",
        )
        li_cancel = _make_line_item(
            order,
            shopify_line_item_id=2,
            sku="SKU-CANCEL",
            quantity=1,
            purchase_status="order_cancelled",
            logistics_status="not_shipped",
        )

        _recompute_order_aggregates([order.id])
        order.refresh_from_db()
        # Premise — without it the When/Then below proves nothing.
        assert order.ready_to_ship is True
        assert order.status == "partial"
        status_before = order.status

        res = auth_client.patch(
            LINE_ITEM_STATUS_URL.format(pk=li_cancel.pk),
            {"purchase_status": "unordered"},
            format="json",
        )

        assert res.status_code == 200
        order.refresh_from_db()
        # li_cancel re-enters the aggregate as not_shipped/non-in_stock.
        assert order.ready_to_ship is False
        # purchase_status plays no part in the Order.status computation.
        assert order.status == status_before == "partial"

    def test_on_hold_restore_is_inert_and_cs_required_restore_lifts_ready(
        self, auth_client
    ):
        """T9 (AC-RESTORE-009) — REQ-RESTORE-014."""
        order_hold = _make_order(shopify_order_id=918201, name="#91821")
        li_hold = _make_line_item(
            order_hold,
            shopify_line_item_id=1,
            sku="SKU-HOLD",
            quantity=1,
            purchase_status="on_hold",
            logistics_status="received",
        )
        order_cs = _make_order(shopify_order_id=918202, name="#91822")
        li_cs = _make_line_item(
            order_cs,
            shopify_line_item_id=1,
            sku="SKU-CS",
            quantity=1,
            purchase_status="cs_required",
            logistics_status="received",
        )
        _make_line_item(
            order_cs,
            shopify_line_item_id=2,
            sku="SKU-PLAIN",
            quantity=1,
            purchase_status="unordered",
            logistics_status="received",
        )

        _recompute_order_aggregates([order_hold.id, order_cs.id])
        order_hold.refresh_from_db()
        order_cs.refresh_from_db()
        hold_ready_before = order_hold.ready_to_ship
        hold_status_before = order_hold.status
        cs_status_before = order_cs.status
        assert order_cs.ready_to_ship is False  # premise: any(cs_required)

        res_hold = auth_client.patch(
            LINE_ITEM_STATUS_URL.format(pk=li_hold.pk),
            {"purchase_status": "unordered"},
            format="json",
        )
        res_cs = auth_client.patch(
            LINE_ITEM_STATUS_URL.format(pk=li_cs.pk),
            {"purchase_status": "unordered"},
            format="json",
        )

        assert res_hold.status_code == 200
        assert res_cs.status_code == 200
        order_hold.refresh_from_db()
        order_cs.refresh_from_db()
        # on_hold appears in neither aggregate rule — nothing moves.
        assert order_hold.ready_to_ship == hold_ready_before
        assert order_hold.status == hold_status_before
        # cs_required's forced-False condition is gone.
        assert order_cs.ready_to_ship is True
        assert order_cs.status == cs_status_before


@pytest.mark.django_db
class TestRestoreWriteScope:
    """AC-RESTORE-010 — REQ-RESTORE-012/013/015."""

    @pytest.mark.parametrize("endpoint", ["single", "bulk"])
    def test_restore_writes_purchase_status_only_and_leaves_notes_alone(
        self, auth_client, endpoint
    ):
        """T10 (AC-RESTORE-010) — REQ-RESTORE-012/013/015."""
        order = _make_order()
        li = _make_line_item(
            order,
            shopify_line_item_id=1,
            sku=f"SKU-{endpoint.upper()}",
            quantity=2,
            purchase_status="on_hold",
            rack_number="A-01",
            confirmed_distributor="booxen",
            confirmed_price="12000.00",
            logistics_status="received",
            location="ca",
            shipped_quantity=1,
        )
        note = LineItemNote.objects.create(
            line_item=li,
            content="출판사 재고 확인 필요",
            note_type="주문보류",
            is_resolved=False,
        )

        before = LineItem.objects.filter(pk=li.pk).values().first()
        global_note_count_before = LineItemNote.objects.count()

        if endpoint == "single":
            res = auth_client.patch(
                LINE_ITEM_STATUS_URL.format(pk=li.pk),
                {"purchase_status": "unordered"},
                format="json",
            )
        else:
            res = auth_client.patch(
                BULK_STATUS_URL,
                {"ids": [li.pk], "purchase_status": "unordered"},
                format="json",
            )
        assert res.status_code == 200

        after = LineItem.objects.filter(pk=li.pk).values().first()
        assert after["purchase_status"] == "unordered"
        changed = {k for k in after if after[k] != before[k]}
        assert changed == {"purchase_status"}

        li.refresh_from_db()
        assert li.notes.count() == 1
        note.refresh_from_db()
        assert note.is_resolved is False
        assert note.content == "출판사 재고 확인 필요"
        assert note.note_type == "주문보류"
        assert LineItemNote.objects.count() == global_note_count_before


@pytest.mark.django_db
class TestPurchaseOrderLinkedRestoreLimit:
    """AC-RESTORE-011 — REQ-RESTORE-022 (known limitation, pinned on purpose)."""

    def test_po_linked_item_stays_out_of_both_lists_after_restore(self, auth_client):
        """T11 (AC-RESTORE-011) — REQ-RESTORE-022."""
        order = _make_order()
        li_linked = _make_line_item(
            order,
            shopify_line_item_id=1,
            sku="SKU-POLINKED",
            quantity=1,
            purchase_status="order_cancelled",
        )
        li_free = _make_line_item(
            order,
            shopify_line_item_id=2,
            sku="SKU-FREE",
            quantity=1,
            purchase_status="order_cancelled",
        )
        po = PurchaseOrder.objects.create(
            sku="SKU-POLINKED", title="연결 도서", distributor="booxen", quantity=1
        )
        po.line_items.add(li_linked)

        for li in (li_linked, li_free):
            res = auth_client.patch(
                LINE_ITEM_STATUS_URL.format(pk=li.pk),
                {"purchase_status": "unordered"},
                format="json",
            )
            assert res.status_code == 200

        res_unordered = auth_client.get(UNORDERED_URL)
        res_excluded = auth_client.get(EXCLUDED_URL)

        unordered_skus = {row["sku"] for row in res_unordered.data["results"]}
        excluded_skus = {row["sku"] for row in res_excluded.data["results"]}
        # The PO link keeps it out of the reorder queue (pre-existing rule) ...
        assert "SKU-FREE" in unordered_skus
        assert "SKU-POLINKED" not in unordered_skus
        # ... and the restore took it out of the excluded list too, so it is
        # now invisible in both. This SPEC does not fix that (후속 과제 2).
        assert "SKU-POLINKED" not in excluded_skus
