"""SPEC-ORDER-016: 강제 출고 처리 (TDD).

Coverage targets:
  T1  후보 배치 조회 — 1회 요청 배치, 빈 집합 빈 결과, 무쓰기
      (REQ-FORCE-003, AC-FORCE-003)
  T2  후보 제외(취소/NULL SKU) + 필드 구성 + 잔여 용량 표시 + 결정적 정렬
      (REQ-FORCE-005, REQ-FORCE-006, AC-FORCE-005)
  T3  동명 주문 tie-break는 최저 pk (후보 조회 + 강제 반영 공통)
      (REQ-FORCE-004, AC-FORCE-004)
  T4  후보 조회 인증 관례 (REQ-FORCE-017, AC-FORCE-017)
  T5  사전 게이트 7종 위반 → 요청 전체 HTTP 400, 유효 행도 미반영
      (REQ-FORCE-002, AC-FORCE-002)
  T6  두 경로 결과 동일성 + 0 수량의 유일한 편차(그룹 미형성)
      (REQ-FORCE-007, AC-FORCE-006)
  T7  동일 대상 2행 합산 — 초과 시 무변경 + 병합 초과 1건
      (REQ-FORCE-008, REQ-FORCE-010, AC-FORCE-007)
  T8  동일 대상 2행 합산 — 성공 시 1회 증가 + 병합 matched 1건(sku는 대상 자신의 값)
      (REQ-FORCE-008, REQ-FORCE-009, REQ-FORCE-016, AC-FORCE-008)
  T9  임계 미달 단일 행 반영 (REQ-FORCE-009, AC-FORCE-009)
  T10 quantity=null 대상에 대한 양수 요청 → 무변경 + quantity_exceeded
      (REQ-FORCE-010, AC-FORCE-010)
  T11 음수/0/판독불가 거부 + 그룹 미형성 + 합산 제외
      (REQ-FORCE-008, REQ-FORCE-011, AC-FORCE-011)
  T12 shipped_quantity 불감소 (REQ-FORCE-012, AC-FORCE-012)
  T13 쓰기 대상 3필드 제한 + 재계산 spy 미호출 (REQ-FORCE-013, AC-FORCE-013)
  T14 원자성 — 배치 중간 고장 주입 시 전량 롤백 (REQ-FORCE-014, AC-FORCE-014)
  T15 응답 계약 — 기존 3분류 필드 그대로 재사용 (REQ-FORCE-016, AC-FORCE-016)
  T16 인증 관례 — 두 엔드포인트 공통 (REQ-FORCE-017, AC-FORCE-017)
  T17 기존 출고 엔드포인트 계약·쿼리 수 무변경 회귀 (REQ-FORCE-018, AC-FORCE-018)
  T18 URL 등록 확인
  T19 강제 경로 행 잠금 — 결정적 FOR UPDATE 검증 + 동시 실행 2건 한도 보호
      (REQ-FORCE-025, AC-FORCE-023)
  T20 동명 주문 tie-break — 강제 반영(쓰기) 경로. T3(후보 조회)와 별개로,
      기록 자체가 최저 pk Order의 LineItem에 남는지 검증
      (REQ-FORCE-004, AC-FORCE-004)
  T21 사전 게이트 — line_item_id 타입 오류(문자열 / bool) 거부
      (REQ-FORCE-002, AC-FORCE-002)
  T22 강제 반영 엔드포인트 — rows가 list가 아니면 400
      (REQ-FORCE-015 계약 방어, T18의 URL 등록과 별개로 뷰 자체의 입력 검증)
"""

import threading
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from freezegun import freeze_time
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import LineItem, Order, Refund
from order.purchase_order_views import (
    ForceOutboundGateViolation,
    _process_force_outbound_rows,
    _process_outbound_rows,
)

CANDIDATES_URL = "/api/purchase-orders/line-items/outbound-force-candidates/"
FORCE_PROCESS_URL = "/api/purchase-orders/line-items/outbound-force-process/"
OUTBOUND_PROCESS_URL = "/api/purchase-orders/line-items/outbound-process/"


def _make_order(shopify_order_id: int = 600001, store_type: str = "gimssine", **kwargs) -> Order:
    return Order.objects.create(shopify_order_id=shopify_order_id, store_type=store_type, **kwargs)


def _make_line_item(
    order: Order, shopify_line_item_id: int = 1, sku: str = "ISBN001", **kwargs
) -> LineItem:
    defaults = {"quantity": 10, "title": "Test Book"}
    defaults.update(kwargs)
    return LineItem.objects.create(
        order=order, shopify_line_item_id=shopify_line_item_id, sku=sku, **defaults
    )


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="spec016_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def anon_client():
    return APIClient()


# ---------------------------------------------------------------------------
# T1/T2 — candidate batch lookup (REQ-FORCE-003/005/006, AC-FORCE-003/005)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestForceCandidateBatchLookup:
    def test_single_request_returns_candidates_for_every_requested_order(self, auth_client):
        """AC-FORCE-003(a): 5개 주문에 걸친 후보가 1회 왕복으로 반환된다."""
        names = []
        for i in range(5):
            order = _make_order(shopify_order_id=600100 + i, name=f"#F{600100 + i}")
            _make_line_item(order, sku=f"ISBN-F{i}", quantity=10)
            names.append(order.name)

        response = auth_client.post(
            CANDIDATES_URL, {"order_names": names}, format="json"
        )

        assert response.status_code == 200
        assert len(response.data["results"]) == 5
        returned_names = {r["order_name"] for r in response.data["results"]}
        assert returned_names == set(names)
        for entry in response.data["results"]:
            assert len(entry["candidates"]) == 1

    def test_empty_order_name_set_returns_empty_result_and_writes_nothing(self, auth_client):
        """AC-FORCE-003(b): 빈 집합은 오류가 아니라 빈 결과이며 무쓰기."""
        order = _make_order(shopify_order_id=600200, name="#F600200")
        li = _make_line_item(order, sku="ISBN-EMPTY", quantity=10)

        response = auth_client.post(CANDIDATES_URL, {"order_names": []}, format="json")

        assert response.status_code == 200
        assert response.data["results"] == []
        li.refresh_from_db()
        assert li.shipped_quantity == 0

    def test_order_names_must_be_a_list(self, auth_client):
        response = auth_client.post(
            CANDIDATES_URL, {"order_names": "not-a-list"}, format="json"
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestForceCandidateExclusionsAndAttributes:
    """AC-FORCE-005: 취소·NULL SKU 후보 제외, 잔여 용량 표시, 필드 구성, 결정적 정렬."""

    def test_candidate_list_excludes_cancelled_and_null_sku_shows_capacity_and_is_deterministic(
        self, auth_client
    ):
        order = _make_order(shopify_order_id=600300, name="#F600300")
        normal = _make_line_item(
            order, shopify_line_item_id=1, sku="ISBN-DUP", quantity=10, shipped_quantity=0
        )
        _make_line_item(
            order,
            shopify_line_item_id=2,
            sku="ISBN-CANCELLED",
            quantity=10,
            purchase_status="order_cancelled",
        )
        _make_line_item(order, shopify_line_item_id=3, sku=None, quantity=10)
        null_qty = _make_line_item(order, shopify_line_item_id=4, sku="ISBN-NULLQTY", quantity=None)
        full = _make_line_item(
            order,
            shopify_line_item_id=5,
            sku="ISBN-DUP",
            quantity=5,
            shipped_quantity=5,
            title="Test Book",
        )

        first = auth_client.post(CANDIDATES_URL, {"order_names": ["#F600300"]}, format="json")
        second = auth_client.post(CANDIDATES_URL, {"order_names": ["#F600300"]}, format="json")

        assert first.status_code == second.status_code == 200
        candidates = first.data["results"][0]["candidates"]
        assert len(candidates) == 3
        returned_ids = {c["line_item_id"] for c in candidates}
        assert returned_ids == {normal.id, null_qty.id, full.id}

        by_id = {c["line_item_id"]: c for c in candidates}
        assert by_id[normal.id]["no_remaining_capacity"] is False
        assert by_id[null_qty.id]["no_remaining_capacity"] is True
        assert by_id[full.id]["no_remaining_capacity"] is True
        for c in candidates:
            for field in (
                "line_item_id",
                "title",
                "sku",
                "quantity",
                "shipped_quantity",
                "logistics_status",
                "no_remaining_capacity",
            ):
                assert field in c

        assert [c["line_item_id"] for c in first.data["results"][0]["candidates"]] == [
            c["line_item_id"] for c in second.data["results"][0]["candidates"]
        ]


@pytest.mark.django_db
class TestForceCandidateOrderResolutionTieBreak:
    """AC-FORCE-004: 동명 주문 tie-break는 최저 pk, 생성 일시 순서는 무관."""

    def test_lowest_pk_wins_even_when_created_later(self, auth_client):
        """`Order.name` carries no uniqueness constraint. Rather than
        fighting MySQL's auto_increment sequence to force an artificial pk
        ordering, this inverts `created_at` (via a bare `.update()`, which
        bypasses `auto_now_add`) so the naturally lower-pk order looks
        "created later" than its sibling — proving the tie-break truly keys
        off `pk`, not creation timestamp."""
        winner_by_pk = _make_order(shopify_order_id=600401, name="#F600400")
        loser_by_pk = _make_order(shopify_order_id=600402, name="#F600400")
        assert winner_by_pk.pk < loser_by_pk.pk

        Order.objects.filter(pk=winner_by_pk.pk).update(
            created_at=timezone.now()
        )
        Order.objects.filter(pk=loser_by_pk.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )

        winner_li = _make_line_item(winner_by_pk, sku="ISBN-WIN", quantity=10)
        _make_line_item(loser_by_pk, sku="ISBN-LOSE", quantity=10)

        response = auth_client.post(
            CANDIDATES_URL, {"order_names": ["#F600400"]}, format="json"
        )

        assert response.status_code == 200
        candidates = response.data["results"][0]["candidates"]
        assert len(candidates) == 1
        assert candidates[0]["line_item_id"] == winner_li.id


@pytest.mark.django_db
class TestForceProcessOrderResolutionTieBreak:
    """AC-FORCE-004 write-side gap: "강제 실행의 기록도 O1(최저 pk)의
    LineItem에 남는다" — the candidate lookup resolving to the right Order
    (T3 above) is not sufficient evidence that the force-APPLY write also
    lands there. Both code paths call the same `_resolve_orders_by_name`
    helper, but sharing a helper is a structural fact, not a behavioral
    test — this exercises the write endpoint directly."""

    def test_force_write_lands_on_the_lowest_pk_order_even_when_created_later(
        self, auth_client
    ):
        winner_by_pk = _make_order(shopify_order_id=610401, name="#F700400")
        loser_by_pk = _make_order(shopify_order_id=610402, name="#F700400")
        assert winner_by_pk.pk < loser_by_pk.pk

        # Same technique as TestForceCandidateOrderResolutionTieBreak: invert
        # created_at so pk order and creation-time order diverge, per
        # AC-FORCE-004 ("pk가 더 작은 O1을 더 나중에 생성해 pk 순서와 생성
        # 일시 순서를 어긋나게 만든다").
        Order.objects.filter(pk=winner_by_pk.pk).update(created_at=timezone.now())
        Order.objects.filter(pk=loser_by_pk.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )

        winner_li = _make_line_item(
            winner_by_pk,
            shopify_line_item_id=1,
            sku="ISBN-WWIN",
            quantity=10,
            shipped_quantity=0,
        )
        loser_li = _make_line_item(
            loser_by_pk,
            shopify_line_item_id=1,
            sku="ISBN-WLOSE",
            quantity=10,
            shipped_quantity=0,
        )

        response = auth_client.post(
            FORCE_PROCESS_URL,
            {
                "rows": [
                    {
                        "name": "#F700400",
                        "sku": "ISBN-WWIN",
                        "total": 3,
                        "line_item_id": winner_li.id,
                    }
                ]
            },
            format="json",
        )

        # If order resolution had picked loser_by_pk instead of winner_by_pk,
        # the gate's ownership check (target.order_id != order.id,
        # REQ-FORCE-002) would reject this whole request as a cross-order
        # violation (HTTP 400) rather than succeed — winner_li belongs only
        # to winner_by_pk. A 200 here is direct proof the write resolved
        # against, and landed on, the lowest-pk Order.
        assert response.status_code == 200
        assert response.data["matched"][0]["line_item_id"] == winner_li.id

        winner_li.refresh_from_db()
        loser_li.refresh_from_db()
        assert winner_li.shipped_quantity == 3
        assert loser_li.shipped_quantity == 0


@pytest.mark.django_db
class TestForceCandidateAuth:
    def test_candidate_lookup_requires_authentication(self, anon_client):
        response = anon_client.post(
            CANDIDATES_URL, {"order_names": ["#X"]}, format="json"
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# T5 — pre-gate: 7 violation kinds (REQ-FORCE-002, AC-FORCE-002)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestForceProcessGate:
    """AC-FORCE-002: 위반 행 1건 + 유효 행 1건을 함께 제출 -> 요청 전체 400,
    LA/LC/LN/L2 어느 것도 변경되지 않는다."""

    def _fixture(self):
        o1 = _make_order(shopify_order_id=610001, name="#37349")
        la = _make_line_item(o1, shopify_line_item_id=1, sku="ISBN-LA", quantity=10)
        lc = _make_line_item(
            o1,
            shopify_line_item_id=2,
            sku="ISBN-LC",
            quantity=10,
            purchase_status="order_cancelled",
        )
        ln = _make_line_item(o1, shopify_line_item_id=3, sku=None, quantity=10)
        o2 = _make_order(shopify_order_id=610002, name="#40000")
        l2 = _make_line_item(o2, shopify_line_item_id=1, sku="ISBN-L2", quantity=10)
        return o1, la, lc, ln, o2, l2

    def _valid_row(self, l2):
        return {"name": "#40000", "sku": "ISBN-L2", "total": 3, "line_item_id": l2.id}

    @pytest.mark.parametrize(
        "case",
        [
            "malformed",
            "no_target",
            "nonexistent_target",
            "order_not_found",
            "cross_order",
            "cancelled_target",
            "null_sku_target",
            "string_target",
            "bool_target",
        ],
    )
    def test_each_gate_violation_rejects_the_whole_request(self, auth_client, case):
        o1, la, lc, ln, o2, l2 = self._fixture()

        bad_row_by_case = {
            "malformed": "not-a-dict",
            "no_target": {"name": "#37349", "sku": "ISBN-LA", "total": 4},
            "nonexistent_target": {
                "name": "#37349", "sku": "ISBN-LA", "total": 4, "line_item_id": 999999999,
            },
            "order_not_found": {
                "name": "#NOPE", "sku": "ISBN-X", "total": 4, "line_item_id": la.id,
            },
            "cross_order": {
                "name": "#37349", "sku": "ISBN-L2", "total": 4, "line_item_id": l2.id,
            },
            "cancelled_target": {
                "name": "#37349", "sku": "ISBN-LC", "total": 4, "line_item_id": lc.id,
            },
            "null_sku_target": {
                "name": "#37349", "sku": "", "total": 4, "line_item_id": ln.id,
            },
            # T21: exercises the `not isinstance(target_id, int) or
            # isinstance(target_id, bool)` type guard in
            # _force_outbound_gate_violated (purchase_order_views.py
            # ~2968-2969). A wrong-typed line_item_id must never reach the
            # `targets_by_id` dict lookup as if it were a real pk.
            "string_target": {
                "name": "#37349", "sku": "ISBN-LA", "total": 4, "line_item_id": "abc",
            },
            # `True` is an `int` subclass in Python (`isinstance(True, int)
            # is True`) and would otherwise slip through as pk=1 without the
            # explicit `isinstance(target_id, bool)` half of the guard.
            "bool_target": {
                "name": "#37349", "sku": "ISBN-LA", "total": 4, "line_item_id": True,
            },
        }
        bad_row = bad_row_by_case[case]

        response = auth_client.post(
            FORCE_PROCESS_URL,
            {"rows": [bad_row, self._valid_row(l2)]},
            format="json",
        )

        assert response.status_code == 400
        for item in (la, lc, ln, l2):
            item.refresh_from_db()
        assert la.shipped_quantity == 0
        assert lc.shipped_quantity == 0
        assert ln.shipped_quantity == 0
        assert l2.shipped_quantity == 0

    def test_gate_violation_does_not_auto_select_the_only_candidate(self, auth_client):
        """AC-FORCE-002 (b): O1의 유일한 유효 후보 LA가 대상 미지정 시 자동
        선택되지 않는다 — LC/LN은 후보 자격이 없으므로 O1의 유효 후보는 LA뿐."""
        o1, la, lc, ln, o2, l2 = self._fixture()

        response = auth_client.post(
            FORCE_PROCESS_URL,
            {
                "rows": [
                    {"name": "#37349", "sku": "ISBN-LA", "total": 4},
                    self._valid_row(l2),
                ]
            },
            format="json",
        )

        assert response.status_code == 400
        la.refresh_from_db()
        assert la.shipped_quantity == 0


# ---------------------------------------------------------------------------
# T6 — deviation from normal path is exactly two things (REQ-FORCE-007,
# AC-FORCE-006)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestForceMatchesNormalPathExceptForTheDeclaredDeviations:
    def test_positive_quantity_within_capacity_yields_identical_state_via_either_path(
        self, auth_client
    ):
        """AC-FORCE-006(a): 동일 초기 상태의 L1(정상 경로)·L2(강제 경로)에
        같은 수량을 반영하면 shipped_quantity/logistics_status가 동일하다."""
        order = _make_order(shopify_order_id=620001, name="#37349")
        l1 = _make_line_item(
            order, shopify_line_item_id=1, sku="ISBN-L1", quantity=10, shipped_quantity=2
        )
        l2 = _make_line_item(
            order, shopify_line_item_id=2, sku="ISBN-L2", quantity=10, shipped_quantity=2
        )

        _process_outbound_rows([{"name": "#37349", "sku": "ISBN-L1", "total": 3}])
        auth_client.post(
            FORCE_PROCESS_URL,
            {"rows": [{"name": "#37349", "sku": "ISBN-L2", "total": 3, "line_item_id": l2.id}]},
            format="json",
        )

        l1.refresh_from_db()
        l2.refresh_from_db()
        assert l1.shipped_quantity == l2.shipped_quantity == 5
        assert l1.logistics_status == l2.logistics_status

    def test_zero_quantity_forms_no_group_and_leaves_the_target_untouched(self, auth_client):
        """AC-FORCE-006(b): 정상 경로는 미국창고 완료 신호로 L3를 완료
        처리하지만, 강제 경로는 0 수량 행이 그룹화 이전에 제거되어 그룹조차
        형성되지 않는다 — L3는 무변경이며 어떤 응답 목록에도 나타나지 않는다."""
        order = _make_order(shopify_order_id=620002, name="#37349")
        l3 = _make_line_item(
            order,
            shopify_line_item_id=3,
            sku="ISBN-L3",
            quantity=10,
            shipped_quantity=0,
            confirmed_distributor="warehouse_ca",
        )

        response = auth_client.post(
            FORCE_PROCESS_URL,
            {"rows": [{"name": "#37349", "sku": "ISBN-L3", "total": 0, "line_item_id": l3.id}]},
            format="json",
        )

        assert response.status_code == 200
        l3.refresh_from_db()
        assert l3.shipped_quantity == 0
        assert l3.shipped_at is None
        assert l3.logistics_status != "shipped"
        matched_ids = {m["line_item_id"] for m in response.data["matched"]}
        exceeded_ids = {m["line_item_id"] for m in response.data["quantity_exceeded"]}
        assert l3.id not in matched_ids
        assert l3.id not in exceeded_ids
        assert response.data["unmatched"][0]["reason"] == "invalid_total"


# ---------------------------------------------------------------------------
# T7/T8 — per-target aggregation (REQ-FORCE-008/009/010/016,
# AC-FORCE-007/008)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestForceProcessSameTargetAggregation:
    def test_two_rows_same_target_summing_over_capacity_yields_one_exceeded_item(
        self, auth_client
    ):
        """AC-FORCE-007: 6+5=11 > 10 -> 무변경 + 초과 항목 정확히 1건."""
        order = _make_order(shopify_order_id=630001, name="#37349")
        target = _make_line_item(
            order, shopify_line_item_id=1, sku="ISBN-TARGET", quantity=10, shipped_quantity=0
        )

        response = auth_client.post(
            FORCE_PROCESS_URL,
            {
                "rows": [
                    {"name": "#37349", "sku": "ISBN-X", "total": 6, "line_item_id": target.id},
                    {"name": "#37349", "sku": "ISBN-Y", "total": 5, "line_item_id": target.id},
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        target.refresh_from_db()
        assert target.shipped_quantity == 0
        assert len(response.data["quantity_exceeded"]) == 1
        assert response.data["matched"] == []

    def test_two_rows_same_target_summing_to_capacity_yields_one_merged_matched_item(
        self, auth_client
    ):
        """AC-FORCE-008: sku="ISBN-TARGET" 대상에 4+6 -> 한 번만 증가,
        "shipped" 전이, matched 1건이며 sku는 요청 행이 아니라 대상 자신의 값."""
        order = _make_order(shopify_order_id=630002, name="#37349")
        target = _make_line_item(
            order, shopify_line_item_id=1, sku="ISBN-TARGET", quantity=10, shipped_quantity=0
        )

        response = auth_client.post(
            FORCE_PROCESS_URL,
            {
                "rows": [
                    {"name": "#37349", "sku": "ISBN-X", "total": 4, "line_item_id": target.id},
                    {"name": "#37349", "sku": "ISBN-Y", "total": 6, "line_item_id": target.id},
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        target.refresh_from_db()
        assert target.shipped_quantity == 10
        assert target.logistics_status == "shipped"
        assert len(response.data["matched"]) == 1
        item = response.data["matched"][0]
        assert item["line_item_id"] == target.id
        assert item["sku"] == "ISBN-TARGET"
        assert item["total"] == 10


@pytest.mark.django_db
class TestForceProcessBelowThreshold:
    def test_single_row_below_threshold_increases_quantity_and_stamps_shipped_at_only(
        self,
    ):
        """AC-FORCE-009."""
        order = _make_order(shopify_order_id=640001, name="#37349")
        target = _make_line_item(
            order,
            sku="ISBN-BELOW",
            quantity=10,
            shipped_quantity=3,
            logistics_status="received",
        )

        # The JWT auth client is built INSIDE the frozen-time block: a token
        # minted at the real wall-clock "now" carries an `iat` claim that
        # freeze_time's frozen (earlier-in-the-day) clock would see as
        # issued in the future, which SimpleJWT rejects as not-yet-valid
        # (401) — a freezegun/JWT interaction, not a force-outbound bug.
        with freeze_time("2026-08-12 09:00:00"):
            test_user = get_user_model().objects.create_user(
                username="spec016_freeze_user", password="testpass123"
            )
            client = APIClient()
            refresh = RefreshToken.for_user(test_user)
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

            response = client.post(
                FORCE_PROCESS_URL,
                {
                    "rows": [
                        {
                            "name": "#37349",
                            "sku": "ISBN-BELOW",
                            "total": 2,
                            "line_item_id": target.id,
                        }
                    ]
                },
                format="json",
            )

        assert response.status_code == 200
        target.refresh_from_db()
        assert target.shipped_quantity == 5
        assert target.shipped_at is not None
        assert target.logistics_status == "received"


@pytest.mark.django_db
class TestForceProcessNullQuantityExceeded:
    def test_positive_request_against_null_quantity_target_is_exceeded(self, auth_client):
        """AC-FORCE-010."""
        order = _make_order(shopify_order_id=650001, name="#37349")
        target = _make_line_item(order, sku="ISBN-NULLQ", quantity=None, shipped_quantity=0)

        response = auth_client.post(
            FORCE_PROCESS_URL,
            {
                "rows": [
                    {"name": "#37349", "sku": "ISBN-NULLQ", "total": 1, "line_item_id": target.id}
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        target.refresh_from_db()
        assert target.shipped_quantity == 0
        assert len(response.data["quantity_exceeded"]) == 1


# ---------------------------------------------------------------------------
# T11 — negative/zero/unreadable pre-grouping rejection (REQ-FORCE-008/011,
# AC-FORCE-011)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestForceProcessInvalidTotalRemovedBeforeGrouping:
    def test_six_invalid_rows_all_reported_and_all_targets_left_untouched(self, auth_client):
        order = _make_order(shopify_order_id=660001, name="#37349")
        la = _make_line_item(
            order, shopify_line_item_id=1, sku="ISBN-LA", quantity=10, shipped_quantity=8
        )
        lb = _make_line_item(
            order,
            shopify_line_item_id=2,
            sku="ISBN-LB",
            quantity=10,
            shipped_quantity=0,
            confirmed_distributor="warehouse_ca",
        )
        ld = _make_line_item(
            order, shopify_line_item_id=3, sku="ISBN-LD", quantity=None, shipped_quantity=0
        )
        le = _make_line_item(
            order, shopify_line_item_id=4, sku="ISBN-LE", quantity=5, shipped_quantity=5
        )
        lc = _make_line_item(
            order, shopify_line_item_id=5, sku="ISBN-LC", quantity=10, shipped_quantity=0
        )

        before = {
            item.id: (item.shipped_at, item.logistics_status)
            for item in (la, lb, ld, le)
        }

        response = auth_client.post(
            FORCE_PROCESS_URL,
            {
                "rows": [
                    {"name": "#37349", "sku": "ISBN-LA", "total": -5, "line_item_id": la.id},
                    {"name": "#37349", "sku": "ISBN-LA", "total": 0, "line_item_id": la.id},
                    {"name": "#37349", "sku": "ISBN-LA", "total": "abc", "line_item_id": la.id},
                    {"name": "#37349", "sku": "ISBN-LB", "total": 0, "line_item_id": lb.id},
                    {"name": "#37349", "sku": "ISBN-LD", "total": 0, "line_item_id": ld.id},
                    {"name": "#37349", "sku": "ISBN-LE", "total": 0, "line_item_id": le.id},
                    {"name": "#37349", "sku": "ISBN-LC", "total": 3, "line_item_id": lc.id},
                    {"name": "#37349", "sku": "ISBN-LC", "total": -5, "line_item_id": lc.id},
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        invalid_reasons = [
            u["reason"] for u in response.data["unmatched"]
        ]
        # 7, not 6: the AC-FORCE-011 fixture's six invalid rows (a)-(f) plus
        # LC's own negative companion row (h) — the valid LC row (g, +3) is
        # the only row in this batch that is NOT invalid_total.
        assert invalid_reasons.count("invalid_total") == 7

        la.refresh_from_db()
        lb.refresh_from_db()
        ld.refresh_from_db()
        le.refresh_from_db()
        lc.refresh_from_db()

        assert la.shipped_quantity == 8
        assert lb.shipped_quantity == 0
        assert ld.shipped_quantity == 0
        assert le.shipped_quantity == 5
        for item in (la, lb, ld, le):
            assert (item.shipped_at, item.logistics_status) == before[item.id]

        matched_or_exceeded_ids = {
            m["line_item_id"] for m in response.data["matched"] + response.data["quantity_exceeded"]
        }
        assert la.id not in matched_or_exceeded_ids
        assert lb.id not in matched_or_exceeded_ids
        assert ld.id not in matched_or_exceeded_ids
        assert le.id not in matched_or_exceeded_ids

        # LC: negative row excluded from the sum, only the +3 row counts.
        assert lc.shipped_quantity == 3


# ---------------------------------------------------------------------------
# T12 — non-decreasing shipped_quantity (REQ-FORCE-012, AC-FORCE-012)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestForceProcessNonDecreasing:
    def test_shipped_quantity_never_drops_below_its_starting_value(self, auth_client):
        order = _make_order(shopify_order_id=670001, name="#37349")
        target = _make_line_item(order, sku="ISBN-NODEC", quantity=100, shipped_quantity=6)

        sequences = [
            [{"name": "#37349", "sku": "ISBN-NODEC", "total": 3, "line_item_id": target.id}],
            [{"name": "#37349", "sku": "ISBN-NODEC", "total": -2, "line_item_id": target.id}],
            [{"name": "#37349", "sku": "ISBN-NODEC", "total": 200, "line_item_id": target.id}],
            [{"name": "#37349", "sku": "ISBN-NODEC", "total": 0, "line_item_id": target.id}],
        ]

        for rows in sequences:
            auth_client.post(FORCE_PROCESS_URL, {"rows": rows}, format="json")
            target.refresh_from_db()
            assert target.shipped_quantity >= 6


# ---------------------------------------------------------------------------
# T13 — write surface + no aggregate recompute (REQ-FORCE-013, AC-FORCE-013)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestForceProcessWriteSurface:
    def test_only_three_fields_change_and_recompute_is_never_called(self, auth_client):
        order = _make_order(shopify_order_id=680001, name="#37349")
        target = _make_line_item(
            order, shopify_line_item_id=1, sku="ISBN-W1", quantity=5, shipped_quantity=0
        )
        sibling_a = _make_line_item(order, shopify_line_item_id=2, sku="ISBN-W2", quantity=10)
        sibling_b = _make_line_item(order, shopify_line_item_id=3, sku="ISBN-W3", quantity=10)
        order.refresh_from_db()
        before_status = order.status
        before_ready = order.ready_to_ship

        with patch("order.purchase_order_views._recompute_order_aggregates") as spy:
            response = auth_client.post(
                FORCE_PROCESS_URL,
                {
                    "rows": [
                        {"name": "#37349", "sku": "ISBN-W1", "total": 5, "line_item_id": target.id}
                    ]
                },
                format="json",
            )
            spy.assert_not_called()

        assert response.status_code == 200
        target.refresh_from_db()
        sibling_a.refresh_from_db()
        sibling_b.refresh_from_db()
        order.refresh_from_db()

        assert target.logistics_status == "shipped"
        assert order.line_items.count() == 3
        for item in (target, sibling_a, sibling_b):
            assert item.sku in ("ISBN-W1", "ISBN-W2", "ISBN-W3")
            assert item.title == "Test Book"
        assert sibling_a.quantity == 10
        assert sibling_b.quantity == 10
        assert order.status == before_status
        assert order.ready_to_ship == before_ready


# ---------------------------------------------------------------------------
# T14 — atomicity fault injection (REQ-FORCE-014, AC-FORCE-014)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestForceProcessAtomicity:
    def test_mid_batch_exception_rolls_back_the_whole_batch(self):
        order = _make_order(shopify_order_id=690001, name="#37349")
        t1 = _make_line_item(order, shopify_line_item_id=1, sku="ISBN-A1", quantity=10)
        t2 = _make_line_item(order, shopify_line_item_id=2, sku="ISBN-A2", quantity=10)
        t3 = _make_line_item(order, shopify_line_item_id=3, sku="ISBN-A3", quantity=10)

        real_bulk_update = LineItem.objects.bulk_update

        def flaky_bulk_update(objs, fields, **kwargs):
            real_bulk_update(objs, fields, **kwargs)
            raise RuntimeError("simulated failure after the batch was written")

        rows = [
            {"name": "#37349", "sku": "ISBN-A1", "total": 3, "line_item_id": t1.id},
            {"name": "#37349", "sku": "ISBN-A2", "total": 4, "line_item_id": t2.id},
            {"name": "#37349", "sku": "ISBN-A3", "total": 5, "line_item_id": t3.id},
        ]

        with patch.object(LineItem.objects, "bulk_update", flaky_bulk_update):
            with pytest.raises(RuntimeError):
                _process_force_outbound_rows(rows)

        t1.refresh_from_db()
        t2.refresh_from_db()
        t3.refresh_from_db()
        assert t1.shipped_quantity == 0
        assert t2.shipped_quantity == 0
        assert t3.shipped_quantity == 0

    def test_view_surfaces_the_failure_as_500_without_partial_writes(self, auth_client):
        order = _make_order(shopify_order_id=690002, name="#37350")
        target = _make_line_item(order, sku="ISBN-A500", quantity=10)

        def raising_bulk_update(objs, fields, **kwargs):
            raise RuntimeError("boom")

        with patch.object(LineItem.objects, "bulk_update", raising_bulk_update):
            response = auth_client.post(
                FORCE_PROCESS_URL,
                {
                    "rows": [
                        {
                            "name": "#37350",
                            "sku": "ISBN-A500",
                            "total": 3,
                            "line_item_id": target.id,
                        }
                    ]
                },
                format="json",
            )

        assert response.status_code == 500
        target.refresh_from_db()
        assert target.shipped_quantity == 0


# ---------------------------------------------------------------------------
# T15 — response contract (REQ-FORCE-016, AC-FORCE-016)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestForceProcessResponseContract:
    def test_response_matches_existing_three_category_field_contract(self, auth_client):
        order = _make_order(shopify_order_id=700001, name="#37349")
        matched_target = _make_line_item(
            order, shopify_line_item_id=1, sku="ISBN-M", quantity=10, shipped_quantity=0
        )
        exceeded_target = _make_line_item(
            order, shopify_line_item_id=2, sku="ISBN-E", quantity=5, shipped_quantity=0
        )

        response = auth_client.post(
            FORCE_PROCESS_URL,
            {
                "rows": [
                    {
                        "name": "#37349",
                        "sku": "ISBN-M",
                        "total": 4,
                        "line_item_id": matched_target.id,
                    },
                    {
                        "name": "#37349",
                        "sku": "ISBN-E",
                        "total": 9,
                        "line_item_id": exceeded_target.id,
                    },
                    {
                        "name": "#37349",
                        "sku": "ISBN-BAD",
                        "total": -1,
                        "line_item_id": matched_target.id,
                    },
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        for category in ("matched", "unmatched", "quantity_exceeded"):
            assert category in response.data
            assert f"{category}_count" in response.data
            assert len(response.data[category]) == response.data[f"{category}_count"]

        matched_item = next(
            m for m in response.data["matched"] if m["line_item_id"] == matched_target.id
        )
        matched_fields = (
            "name", "sku", "total", "line_item_id", "shipped_quantity", "quantity",
            "logistics_status",
        )
        for field in matched_fields:
            assert field in matched_item

        exceeded_item = response.data["quantity_exceeded"][0]
        exceeded_fields = (
            "name", "sku", "total", "line_item_id", "shipped_quantity", "quantity", "reason",
        )
        for field in exceeded_fields:
            assert field in exceeded_item

        unmatched_item = response.data["unmatched"][0]
        for field in ("name", "sku", "total", "reason"):
            assert field in unmatched_item


# ---------------------------------------------------------------------------
# T16 — auth convention shared by both endpoints (REQ-FORCE-017,
# AC-FORCE-017)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestForceProcessAuth:
    def test_force_process_requires_authentication(self, anon_client):
        response = anon_client.post(FORCE_PROCESS_URL, {"rows": []}, format="json")
        assert response.status_code in (401, 403)

    def test_force_process_accepts_authenticated_request_with_no_extra_role_check(
        self, auth_client
    ):
        response = auth_client.post(FORCE_PROCESS_URL, {"rows": []}, format="json")
        assert response.status_code == 200


@pytest.mark.django_db
class TestForceProcessRejectsNonListRows:
    """T22: mirrors TestForceCandidateBatchLookup.test_order_names_must_be_a_list
    for the sibling write endpoint — OutboundForceProcessView.post()'s own
    "rows must be a list" branch (purchase_order_views.py ~3213-3217) had no
    direct test."""

    def test_force_process_rejects_a_non_list_rows_value(self, auth_client):
        response = auth_client.post(
            FORCE_PROCESS_URL, {"rows": "not-a-list"}, format="json"
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# T17 — existing endpoints unaffected (REQ-FORCE-018, AC-FORCE-018)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExistingOutboundEndpointsUnaffected:
    def test_normal_outbound_query_count_still_bounded(self):
        """REQ-FORCE-018: the force endpoints are fully separate — this SPEC
        must add zero queries to `_process_outbound_rows`."""
        order = _make_order(shopify_order_id=710001, name="#37349")
        _make_line_item(order, sku="ISBN-REG", quantity=10)

        with CaptureQueriesContext(connection) as ctx:
            _process_outbound_rows([{"name": "#37349", "sku": "ISBN-REG", "total": 3}])

        assert len(ctx.captured_queries) <= 6

    def test_normal_outbound_endpoint_payload_has_no_candidate_list(self, auth_client):
        order = _make_order(shopify_order_id=710002, name="#37351")
        _make_line_item(order, sku="ISBN-NOFORCE", quantity=10)

        response = auth_client.post(
            OUTBOUND_PROCESS_URL,
            {"rows": [{"name": "#99999", "sku": "ISBN-MISSING", "total": 1}]},
            format="json",
        )

        assert response.status_code == 200
        assert "candidates" not in response.data["unmatched"][0]


# ---------------------------------------------------------------------------
# T18 — URL registration
# ---------------------------------------------------------------------------


class TestForceURLRegistration:
    def test_candidate_and_process_urls_resolve(self):
        from django.urls import resolve

        assert resolve(CANDIDATES_URL).view_name == "po-line-item-outbound-force-candidates"
        assert resolve(FORCE_PROCESS_URL).view_name == "po-line-item-outbound-force-process"


# ---------------------------------------------------------------------------
# T19 — row-level locking (REQ-FORCE-025, AC-FORCE-023)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestForceProcessLockingDeterministic:
    def test_target_select_uses_for_update(self):
        """Fast, deterministic companion to the threaded test below: if the
        lock is ever accidentally removed, this fails immediately instead of
        relying on a possibly-flaky concurrency test."""
        order = _make_order(shopify_order_id=720001, name="#37349")
        target = _make_line_item(order, sku="ISBN-LOCK", quantity=10, shipped_quantity=0)

        with CaptureQueriesContext(connection) as ctx:
            _process_force_outbound_rows(
                [{"name": "#37349", "sku": "ISBN-LOCK", "total": 3, "line_item_id": target.id}]
            )

        target_queries = [q for q in ctx.captured_queries if "orders_line_item" in q["sql"]]
        assert any("FOR UPDATE" in q["sql"].upper() for q in target_queries)


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
class TestForceProcessLockingConcurrent:
    def test_two_concurrent_requests_cannot_both_pass_the_limit(self):
        """AC-FORCE-023: quantity=10, shipped_quantity=0. Two concurrent
        requests each ask for 6 — individually within capacity, jointly not.
        Exactly one must succeed."""
        order = _make_order(shopify_order_id=730001, name="#CONC1")
        target = _make_line_item(order, sku="ISBN-CONC", quantity=10, shipped_quantity=0)

        rows = [{"name": "#CONC1", "sku": "ISBN-CONC", "total": 6, "line_item_id": target.id}]
        barrier = threading.Barrier(2)
        results: dict[str, dict] = {}
        errors: dict[str, Exception] = {}

        def worker(key: str) -> None:
            try:
                barrier.wait(timeout=10)
                results[key] = _process_force_outbound_rows(list(rows))
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

        target.refresh_from_db()
        assert target.shipped_quantity == 6
        assert target.shipped_quantity <= target.quantity

        matched_total = sum(len(r["matched"]) for r in results.values())
        exceeded_total = sum(len(r["quantity_exceeded"]) for r in results.values())
        assert matched_total == 1
        assert exceeded_total == 1


# ---------------------------------------------------------------------------
# Regression — a fully refunded LineItem is never a force outbound target
# ---------------------------------------------------------------------------


def _refund_fully(order, line_item, shopify_refund_id=800001):
    return Refund.objects.create(
        order=order,
        shopify_refund_id=shopify_refund_id,
        line_item_id=line_item.shopify_line_item_id,
        quantity=line_item.quantity,
    )


@pytest.mark.django_db
class TestFullyRefundedTargetExclusion:
    """A fully refunded item is as cancelled as purchase_status="order_cancelled"
    — the customer is not owed it, so force-shipping it would send goods for a
    refunded sale. The candidate picker must not offer it and the apply gate
    must not accept it, or the two would disagree about what is a valid
    target."""

    def test_fully_refunded_line_item_is_not_a_candidate(self, auth_client):
        order = _make_order(name="#600901")
        refunded = _make_line_item(order, shopify_line_item_id=1, sku="ISBN-REF", quantity=2)
        _make_line_item(order, shopify_line_item_id=2, sku="ISBN-OK", quantity=2)
        _refund_fully(order, refunded)

        response = auth_client.post(
            CANDIDATES_URL, {"order_names": ["#600901"]}, format="json"
        )

        assert response.status_code == 200
        skus = {c["sku"] for c in response.json()["results"][0]["candidates"]}
        assert "ISBN-REF" not in skus
        assert "ISBN-OK" in skus

    def test_partially_refunded_line_item_is_still_a_candidate(self, auth_client):
        order = _make_order(shopify_order_id=600902, name="#600902")
        li = _make_line_item(order, shopify_line_item_id=3, sku="ISBN-PART", quantity=3)
        Refund.objects.create(
            order=order,
            shopify_refund_id=800002,
            line_item_id=li.shopify_line_item_id,
            quantity=1,
        )

        response = auth_client.post(
            CANDIDATES_URL, {"order_names": ["#600902"]}, format="json"
        )

        skus = {c["sku"] for c in response.json()["results"][0]["candidates"]}
        assert "ISBN-PART" in skus

    def test_force_apply_rejects_a_fully_refunded_target(self):
        order = _make_order(shopify_order_id=600903, name="#600903")
        refunded = _make_line_item(order, shopify_line_item_id=4, sku="ISBN-REF2", quantity=2)
        _refund_fully(order, refunded, shopify_refund_id=800003)

        with pytest.raises(ForceOutboundGateViolation):
            _process_force_outbound_rows(
                [{"name": "#600903", "sku": "ISBN-REF2", "total": 1, "line_item_id": refunded.id}]
            )

        refunded.refresh_from_db()
        assert refunded.shipped_quantity == 0
        assert refunded.logistics_status != "shipped"


# ---------------------------------------------------------------------------
# 환불(취소) 수량 차감 — 강제 출고 경로도 일반 경로와 같은 용량을 본다.
# 두 경로의 수량 계산은 반드시 일치해야 한다 (_fully_refunded_line_item_ids
# 주석 참조): 한쪽만 차감하면 남은 출고 가능 수량에 대해 서로 다른 답을 낸다.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestForceOutboundRefundNetting:
    def test_partial_refund_reduces_capacity_on_force_path(self):
        order = _make_order(shopify_order_id=610101, name="#610101")
        li = _make_line_item(order, sku="ISBN-FPR", quantity=3)
        Refund.objects.create(
            order=order,
            shopify_refund_id=610901,
            line_item_id=li.shopify_line_item_id,
            quantity=1,
        )

        result = _process_force_outbound_rows(
            [{"line_item_id": li.id, "name": "#610101", "sku": "ISBN-FPR", "total": 2}]
        )

        li.refresh_from_db()
        assert result["matched_count"] == 1
        assert result["quantity_exceeded_count"] == 0
        assert li.shipped_quantity == 2
        assert li.logistics_status == "shipped"
