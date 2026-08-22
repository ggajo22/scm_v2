"""SPEC-ORDER-025 M1/M2: LineItem 단건 발주처리 백엔드 엔드포인트 (TDD).

Coverage targets (REQ-LCONF-001~015):
  AC-LCONF-001     정상 발주처리(일반 행)
  AC-LCONF-002     damaged_exchange 행 순수량 계산 + 상태 자동 복귀
  AC-LCONF-003     이미 연결된 unordered 행 → 409, 부작용 없음
  AC-LCONF-004a~e  부적격 상태 5종 전수 검증
  AC-LCONF-005     전액 환불된 행(순수량 0) → 409
  AC-LCONF-006     distributor 공백 → 400
  AC-LCONF-007     distributor 21자 → 400
  AC-LCONF-008     unit_price 파싱 불가 → 400
  AC-LCONF-009     unit_price 생략 → null 저장
  AC-LCONF-010     존재하지 않는 pk → 404
  AC-LCONF-011     sku 없는 LineItem → 400
  AC-LCONF-012a    FOR UPDATE 락 결정론적 검증
  AC-LCONF-012b    동시 요청 2건 중 1건만 성공(threaded, concurrency marker)
  AC-LCONF-013     Order 집계 재계산 호출 확인(mock-spy, 간접 검증 아님)
  AC-LCONF-014     미인증 요청 → 401
  AC-LCONF-014b    뷰 수준 인증 클래스 선언 정적 확인
  AC-LCONF-015     distributor 정확히 20자 → 성공(경계값)

M2 — 발주처리 시 SKU 정정 (operator-corrected SKU at confirm time):
  AC-LCONF-SKU-001  sku 키 생략 → 기존 동작 그대로 (회귀)
  AC-LCONF-SKU-002  sku == 현재 sku → override 기록 안 됨
  AC-LCONF-SKU-003  새 sku → sku 교체 + original_sku에 이전 값 보존 + PurchaseOrder.sku 신규값
  AC-LCONF-SKU-004  2차 정정 → original_sku는 최초값 유지(중간값 아님)
  AC-LCONF-SKU-005  공백 sku → 400
  AC-LCONF-SKU-006  255자 초과 sku → 400
  AC-LCONF-SKU-007  unique_together 충돌 → 409(500 아님)
"""

import threading
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APIClient
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import LineItem, Order, PurchaseOrder, Refund

User = get_user_model()

CONFIRM_URL = "/api/purchase-orders/line-items/{pk}/confirm/"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="lconf_test_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def anon_client():
    return APIClient()


def _make_order(shopify_order_id: int, store_type: str = "gimssine", name: str | None = None) -> Order:
    return Order.objects.create(shopify_order_id=shopify_order_id, store_type=store_type, name=name)


def _make_line_item(
    order: Order,
    shopify_line_item_id: int = 1,
    sku: str | None = "ISBN-LCONF-BASE",
    title: str = "테스트도서",
    vendor: str = "출판사",
    quantity: int = 5,
    damaged_quantity: int = 0,
    purchase_status: str = "unordered",
) -> LineItem:
    return LineItem.objects.create(
        order=order,
        shopify_line_item_id=shopify_line_item_id,
        sku=sku,
        title=title,
        vendor=vendor,
        quantity=quantity,
        damaged_quantity=damaged_quantity,
        purchase_status=purchase_status,
    )


def _make_refund(order: Order, shopify_refund_id: int, line_item_id: int, quantity: int) -> Refund:
    return Refund.objects.create(
        order=order,
        shopify_refund_id=shopify_refund_id,
        line_item_id=line_item_id,
        quantity=quantity,
    )


# ---------------------------------------------------------------------------
# AC-LCONF-001 / 002 — normal confirmation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLineItemConfirmNormal:
    def test_confirm_creates_purchase_order_for_ordinary_row(self, auth_client):
        """AC-LCONF-001."""
        order = _make_order(shopify_order_id=960001)
        li = _make_line_item(order, sku="ISBN-A", quantity=5)
        url = CONFIRM_URL.format(pk=li.pk)

        res = auth_client.post(
            url, data={"distributor": "북센직접입력", "unit_price": "12000"}, format="json"
        )

        assert res.status_code == 201
        assert PurchaseOrder.objects.filter(line_items=li).count() == 1
        po = PurchaseOrder.objects.get(line_items=li)
        assert po.status == "confirmed"
        assert po.distributor == "북센직접입력"
        assert po.quantity == 5
        assert po.unit_price == Decimal("12000")
        li.refresh_from_db()
        assert li.confirmed_distributor == "북센직접입력"
        assert li.confirmed_price == Decimal("12000")
        assert li.purchase_status == "unordered"

    def test_confirm_damaged_exchange_uses_damaged_quantity_and_resets_status(self, auth_client):
        """AC-LCONF-002."""
        order = _make_order(shopify_order_id=960002)
        li = _make_line_item(
            order,
            sku="ISBN-B",
            quantity=10,
            damaged_quantity=3,
            purchase_status="damaged_exchange",
        )
        # Pre-existing (irrelevant) PO linkage from before the damage — must
        # NOT block confirmation for a damaged_exchange row (REQ-LCONF-004).
        old_po = PurchaseOrder.objects.create(
            sku="ISBN-B", title="구발주", distributor="kyobo", quantity=10, status="confirmed"
        )
        old_po.line_items.add(li)

        url = CONFIRM_URL.format(pk=li.pk)
        res = auth_client.post(url, data={"distributor": "kyobo", "unit_price": None}, format="json")

        assert res.status_code == 201
        new_po = PurchaseOrder.objects.filter(line_items=li).exclude(pk=old_po.pk).get()
        assert new_po.quantity == 3
        assert new_po.unit_price is None
        li.refresh_from_db()
        assert li.purchase_status == "unordered"


# ---------------------------------------------------------------------------
# AC-LCONF-003 / 004a~e / 005 — conflicts
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLineItemConfirmConflicts:
    def test_confirm_already_linked_unordered_returns_409_no_side_effects(self, auth_client):
        """AC-LCONF-003."""
        order = _make_order(shopify_order_id=960010)
        li = _make_line_item(order, sku="ISBN-C", quantity=5)
        po = PurchaseOrder.objects.create(
            sku="ISBN-C", title="t", distributor="kyobo", quantity=5, status="confirmed"
        )
        po.line_items.add(li)
        before_count = PurchaseOrder.objects.count()
        before_distributor = li.confirmed_distributor

        url = CONFIRM_URL.format(pk=li.pk)
        res = auth_client.post(url, data={"distributor": "booxen"}, format="json")

        assert res.status_code == 409
        assert PurchaseOrder.objects.count() == before_count
        li.refresh_from_db()
        assert li.confirmed_distributor == before_distributor

    _INELIGIBLE_ORDER_IDS = {
        "on_hold": 960021,
        "order_cancelled": 960022,
        "cs_required": 960023,
        "other_publisher": 960024,
        "in_stock": 960025,
    }

    @pytest.mark.parametrize(
        "ineligible_status",
        ["on_hold", "order_cancelled", "cs_required", "other_publisher", "in_stock"],
    )
    def test_confirm_ineligible_status_returns_409(self, auth_client, ineligible_status):
        """AC-LCONF-004a~e — full parametrized sweep of the 5 ineligible
        statuses so a single-value blacklist implementation cannot pass."""
        order = _make_order(shopify_order_id=self._INELIGIBLE_ORDER_IDS[ineligible_status])
        li = _make_line_item(order, sku=f"ISBN-{ineligible_status}", purchase_status=ineligible_status)
        url = CONFIRM_URL.format(pk=li.pk)

        res = auth_client.post(url, data={"distributor": "booxen"}, format="json")

        assert res.status_code == 409
        assert PurchaseOrder.objects.filter(line_items=li).count() == 0

    def test_confirm_fully_refunded_returns_409(self, auth_client):
        """AC-LCONF-005."""
        order = _make_order(shopify_order_id=960030)
        li = _make_line_item(order, shopify_line_item_id=501, sku="ISBN-REFUND", quantity=2)
        _make_refund(order, shopify_refund_id=9001, line_item_id=501, quantity=2)

        url = CONFIRM_URL.format(pk=li.pk)
        res = auth_client.post(url, data={"distributor": "booxen"}, format="json")

        assert res.status_code == 409
        assert PurchaseOrder.objects.filter(line_items=li).count() == 0


# ---------------------------------------------------------------------------
# AC-LCONF-006/007/008/009/010/011/015 — request validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLineItemConfirmValidation:
    def test_blank_distributor_returns_400(self, auth_client):
        """AC-LCONF-006."""
        order = _make_order(shopify_order_id=960040)
        li = _make_line_item(order, sku="ISBN-D")
        url = CONFIRM_URL.format(pk=li.pk)

        res = auth_client.post(url, data={"distributor": "   ", "unit_price": None}, format="json")

        assert res.status_code == 400
        assert PurchaseOrder.objects.filter(line_items=li).count() == 0

    def test_distributor_21_chars_returns_400(self, auth_client):
        """AC-LCONF-007."""
        order = _make_order(shopify_order_id=960041)
        li = _make_line_item(order, sku="ISBN-E")
        url = CONFIRM_URL.format(pk=li.pk)

        res = auth_client.post(url, data={"distributor": "가" * 21}, format="json")

        assert res.status_code == 400
        assert PurchaseOrder.objects.filter(line_items=li).count() == 0

    def test_distributor_exactly_20_chars_succeeds(self, auth_client):
        """AC-LCONF-015 — boundary companion to AC-LCONF-007 (`>` vs `>=`)."""
        order = _make_order(shopify_order_id=960042)
        li = _make_line_item(order, sku="ISBN-F")
        url = CONFIRM_URL.format(pk=li.pk)

        res = auth_client.post(url, data={"distributor": "가" * 20}, format="json")

        assert res.status_code == 201
        assert PurchaseOrder.objects.filter(line_items=li).count() == 1

    def test_unit_price_unparseable_returns_400(self, auth_client):
        """AC-LCONF-008."""
        order = _make_order(shopify_order_id=960043)
        li = _make_line_item(order, sku="ISBN-G")
        url = CONFIRM_URL.format(pk=li.pk)

        res = auth_client.post(url, data={"distributor": "booxen", "unit_price": "abc"}, format="json")

        assert res.status_code == 400
        assert PurchaseOrder.objects.filter(line_items=li).count() == 0

    def test_unit_price_omitted_stores_null(self, auth_client):
        """AC-LCONF-009."""
        order = _make_order(shopify_order_id=960044)
        li = _make_line_item(order, sku="ISBN-H")
        url = CONFIRM_URL.format(pk=li.pk)

        res = auth_client.post(url, data={"distributor": "booxen"}, format="json")

        assert res.status_code == 201
        po = PurchaseOrder.objects.get(line_items=li)
        assert po.unit_price is None

    def test_nonexistent_pk_returns_404(self, auth_client):
        """AC-LCONF-010 — response body uses the `error` key, not `detail`."""
        url = CONFIRM_URL.format(pk=999999)

        res = auth_client.post(url, data={"distributor": "booxen"}, format="json")

        assert res.status_code == 404
        assert res.data["error"] == "Not found"

    def test_missing_sku_returns_400(self, auth_client):
        """AC-LCONF-011 — defensive case, not reachable from normal UI flow."""
        order = _make_order(shopify_order_id=960045)
        li = _make_line_item(order, sku=None)
        url = CONFIRM_URL.format(pk=li.pk)

        res = auth_client.post(url, data={"distributor": "booxen"}, format="json")

        assert res.status_code == 400
        assert PurchaseOrder.objects.filter(line_items=li).count() == 0


# ---------------------------------------------------------------------------
# AC-LCONF-012a/012b — row locking
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLineItemConfirmLockingDeterministic:
    def test_target_select_uses_for_update(self, auth_client):
        """AC-LCONF-012a: deterministic companion to the threaded test below —
        SQLite (the project's default test DB engine) silently ignores
        select_for_update(), so this asserts the lock was *requested* via the
        captured SQL text, independent of the execution engine."""
        order = _make_order(shopify_order_id=960050)
        li = _make_line_item(order, sku="ISBN-LOCK")
        url = CONFIRM_URL.format(pk=li.pk)

        with CaptureQueriesContext(connection) as ctx:
            res = auth_client.post(url, data={"distributor": "booxen"}, format="json")

        assert res.status_code == 201
        target_queries = [q for q in ctx.captured_queries if "orders_line_item" in q["sql"]]
        assert any("FOR UPDATE" in q["sql"].upper() for q in target_queries)


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
class TestLineItemConfirmConcurrent:
    def test_two_concurrent_confirms_only_one_succeeds(self):
        """AC-LCONF-012b. Uses real threads against the shared remote test DB
        (see backend/pytest.ini `concurrency` marker) — must not run
        concurrently with other pytest processes."""
        order = _make_order(shopify_order_id=960051)
        li = _make_line_item(order, sku="ISBN-CONC")
        user_obj = User.objects.create_user(username="lconf_conc_user", password="pw")
        refresh = RefreshToken.for_user(user_obj)
        auth_header = f"Bearer {refresh.access_token}"

        barrier = threading.Barrier(2)
        results: dict[str, int] = {}
        errors: dict[str, Exception] = {}

        def worker(key: str) -> None:
            try:
                client = APIClient()
                client.credentials(HTTP_AUTHORIZATION=auth_header)
                barrier.wait(timeout=10)
                res = client.post(
                    CONFIRM_URL.format(pk=li.pk),
                    data={"distributor": "booxen"},
                    format="json",
                )
                results[key] = res.status_code
            except Exception as exc:  # pragma: no cover - diagnostic only
                errors[key] = exc
            finally:
                connection.close()

        t_a = threading.Thread(target=worker, args=("a",))
        t_b = threading.Thread(target=worker, args=("b",))
        t_a.start()
        t_b.start()
        t_a.join(timeout=15)
        t_b.join(timeout=15)

        assert not errors, f"worker thread raised: {errors}"
        assert set(results.keys()) == {"a", "b"}
        assert sorted(results.values()) == [201, 409]
        assert PurchaseOrder.objects.filter(line_items=li).count() == 1


# ---------------------------------------------------------------------------
# AC-LCONF-013 — Order aggregate recompute spy
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLineItemConfirmAggregateRecompute:
    def test_recompute_order_aggregates_called_once_with_order_id(self, auth_client):
        """AC-LCONF-013 — direct mock-spy verification. Order.status/
        ready_to_ship are logistics_status-based aggregates that confirmation
        never touches, so observing them cannot substitute for this spy."""
        order = _make_order(shopify_order_id=960060)
        li = _make_line_item(order, sku="ISBN-SPY")
        url = CONFIRM_URL.format(pk=li.pk)

        with patch("order.purchase_order_views._recompute_order_aggregates") as spy:
            res = auth_client.post(url, data={"distributor": "booxen"}, format="json")

        assert res.status_code == 201
        spy.assert_called_once()
        call_args = spy.call_args[0][0]
        assert li.order_id in set(call_args)


# ---------------------------------------------------------------------------
# AC-LCONF-014 / 014b — authentication
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLineItemConfirmAuth:
    def test_unauthenticated_request_returns_401(self, anon_client):
        """AC-LCONF-014. The only mutation that actually breaks this
        assertion is `permission_classes = [AllowAny]` — removing the
        declaration entirely still falls back to the project-wide
        DEFAULT_PERMISSION_CLASSES=[IsAuthenticated] (base.py:106-108)."""
        order = _make_order(shopify_order_id=960070)
        li = _make_line_item(order, sku="ISBN-AUTH")
        url = CONFIRM_URL.format(pk=li.pk)

        res = anon_client.post(url, data={"distributor": "booxen"}, format="json")

        assert res.status_code == 401
        assert PurchaseOrder.objects.filter(line_items=li).count() == 0

    def test_view_declares_authentication_and_permission_classes(self):
        """AC-LCONF-014b — static check catching a dropped declaration that
        the project-wide default would otherwise mask at the response level."""
        from order.purchase_order_views import LineItemConfirmView

        assert IsAuthenticated in LineItemConfirmView.permission_classes
        assert JWTAuthentication in LineItemConfirmView.authentication_classes


# ---------------------------------------------------------------------------
# M2 — SKU correction at confirm time (AC-LCONF-SKU-001~007)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLineItemConfirmSkuCorrection:
    def test_sku_key_absent_leaves_sku_and_original_sku_untouched(self, auth_client):
        """AC-LCONF-SKU-001 — regression companion to AC-LCONF-001: omitting
        `sku` entirely must reproduce today's behaviour exactly."""
        order = _make_order(shopify_order_id=960080)
        li = _make_line_item(order, sku="ISBN-SKU-1", quantity=4)
        url = CONFIRM_URL.format(pk=li.pk)

        res = auth_client.post(
            url, data={"distributor": "booxen", "unit_price": "1000"}, format="json"
        )

        assert res.status_code == 201
        li.refresh_from_db()
        assert li.sku == "ISBN-SKU-1"
        assert li.original_sku is None
        po = PurchaseOrder.objects.get(line_items=li)
        assert po.sku == "ISBN-SKU-1"

    def test_sku_equal_to_current_records_no_override(self, auth_client):
        """AC-LCONF-SKU-002 — a same-value `sku` must be treated identically
        to an absent key: no original_sku write."""
        order = _make_order(shopify_order_id=960081)
        li = _make_line_item(order, sku="ISBN-SKU-2", quantity=4)
        url = CONFIRM_URL.format(pk=li.pk)

        res = auth_client.post(
            url, data={"distributor": "booxen", "sku": "ISBN-SKU-2"}, format="json"
        )

        assert res.status_code == 201
        li.refresh_from_db()
        assert li.sku == "ISBN-SKU-2"
        assert li.original_sku is None

    def test_new_sku_replaces_sku_and_preserves_original(self, auth_client):
        """AC-LCONF-SKU-003 — the core correction flow: sku is replaced,
        original_sku holds the pre-correction value, and the created
        PurchaseOrder.sku uses the NEW value."""
        order = _make_order(shopify_order_id=960082)
        li = _make_line_item(order, sku="ISBN-OLD-EDITION", quantity=3)
        url = CONFIRM_URL.format(pk=li.pk)

        res = auth_client.post(
            url,
            data={"distributor": "booxen", "unit_price": "5000", "sku": "ISBN-NEW-EDITION"},
            format="json",
        )

        assert res.status_code == 201
        li.refresh_from_db()
        assert li.sku == "ISBN-NEW-EDITION"
        assert li.original_sku == "ISBN-OLD-EDITION"
        po = PurchaseOrder.objects.get(line_items=li)
        assert po.sku == "ISBN-NEW-EDITION"
        assert po.quantity == 3

    def test_second_correction_keeps_first_original_sku(self, auth_client):
        """AC-LCONF-SKU-004 — a second correction must not overwrite the
        true original with the first correction's intermediate value.
        Modelled as two separate eligible rows confirmed in sequence, since
        a single row becomes ineligible (linked) after its first confirm —
        the persistence rule under test is `original_sku` write-once, which
        this reproduces via direct model manipulation between the two
        confirm calls to simulate the row being made confirmable again."""
        order = _make_order(shopify_order_id=960083)
        li = _make_line_item(order, sku="ISBN-EDITION-1", quantity=2)
        url = CONFIRM_URL.format(pk=li.pk)

        res1 = auth_client.post(
            url, data={"distributor": "booxen", "sku": "ISBN-EDITION-2"}, format="json"
        )
        assert res1.status_code == 201
        li.refresh_from_db()
        assert li.original_sku == "ISBN-EDITION-1"

        # Simulate the row becoming eligible again (e.g. a damaged_exchange
        # cycle) without touching original_sku, then confirm a second time
        # with yet another SKU value.
        po1 = PurchaseOrder.objects.get(line_items=li)
        po1.line_items.remove(li)
        li.purchase_status = "unordered"
        li.save(update_fields=["purchase_status"])

        res2 = auth_client.post(
            url, data={"distributor": "kyobo", "sku": "ISBN-EDITION-3"}, format="json"
        )

        assert res2.status_code == 201
        li.refresh_from_db()
        assert li.sku == "ISBN-EDITION-3"
        assert li.original_sku == "ISBN-EDITION-1"  # still the FIRST original

    def test_blank_sku_returns_400(self, auth_client):
        """AC-LCONF-SKU-005."""
        order = _make_order(shopify_order_id=960084)
        li = _make_line_item(order, sku="ISBN-SKU-5", quantity=1)
        url = CONFIRM_URL.format(pk=li.pk)

        res = auth_client.post(
            url, data={"distributor": "booxen", "sku": "   "}, format="json"
        )

        assert res.status_code == 400
        li.refresh_from_db()
        assert li.sku == "ISBN-SKU-5"
        assert PurchaseOrder.objects.filter(line_items=li).count() == 0

    def test_sku_over_255_chars_returns_400(self, auth_client):
        """AC-LCONF-SKU-006."""
        order = _make_order(shopify_order_id=960085)
        li = _make_line_item(order, sku="ISBN-SKU-6", quantity=1)
        url = CONFIRM_URL.format(pk=li.pk)

        res = auth_client.post(
            url, data={"distributor": "booxen", "sku": "A" * 256}, format="json"
        )

        assert res.status_code == 400
        assert PurchaseOrder.objects.filter(line_items=li).count() == 0

    def test_sku_collision_with_sibling_returns_409_not_500(self, auth_client):
        """AC-LCONF-SKU-007 — unique_together = (order, shopify_line_item_id,
        sku) means correcting into a sibling row's sku (the bundle-expansion
        case) must surface as a 409, never an unhandled 500, and must leave
        no partial writes behind."""
        order = _make_order(shopify_order_id=960086)
        li = _make_line_item(
            order, shopify_line_item_id=42, sku="ISBN-MEMBER-A", quantity=2
        )
        # Sibling row sharing the same shopify_line_item_id (bundle-expansion
        # shape) whose sku is the correction target.
        _make_line_item(
            order, shopify_line_item_id=42, sku="ISBN-MEMBER-B", quantity=2
        )
        url = CONFIRM_URL.format(pk=li.pk)

        res = auth_client.post(
            url, data={"distributor": "booxen", "sku": "ISBN-MEMBER-B"}, format="json"
        )

        assert res.status_code == 409
        li.refresh_from_db()
        assert li.sku == "ISBN-MEMBER-A"
        assert li.original_sku is None
        assert PurchaseOrder.objects.filter(line_items=li).count() == 0
