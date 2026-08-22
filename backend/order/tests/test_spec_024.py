"""SPEC-ORDER-024: Daily Review 업로드의 타출판사 확정 발주처/확정 단가 — 백엔드 TDD.

문제 정의:
  1. Daily Review 다운로드는 `auto_select_distributor` Step 0(출판사 규칙)으로
     아가페/성서유니온을 판정하지만, '선택' 셀에는 두 경우 모두 '타출판사'만
     적힌다(`_DISTRIBUTOR_CODE_TO_LABEL`). 업로드 측은 '타출판사'를 CS 분기로만
     처리해 `purchase_status="other_publisher"`만 기록하고
     `confirmed_distributor`(확정 발주처)는 비워 둔다.
  2. 아가페/성서유니온/처음교육은 전용 공급가 컬럼이 없어 확정 단가가 항상
     비어 있고, 그 결과 마진 계산의 원가 기준(`confirmed_cost_krw`)이 잡히지 않는다.

요구사항:
  REQ-OP-001  '타출판사' 선택 행은 교보 출판사 + DistributorVendorRule 로
              실제 발주처 코드(agape/sungseoyunion/choeumgoyuk)를 다시 판정해
              confirmed_distributor 에 기록한다. 규칙에 없으면 기존대로 비워 둔다.
  REQ-OP-002  타출판사 계열(아가페/성서유니온/처음교육) 확정 단가는
              BOOXEN 공급가 / YES24 공급가 / 교보 공급가 세 값 중 0을 제외한
              최소값으로 기록한다. 셋 다 0이거나 비어 있으면 기록하지 않는다.
              BOOXEN/교보/YES24 로 확정된 행은 이 규칙 대상이 아니다.
"""
import io
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import (
    DistributorVendorRule,
    KyoboData,
    LineItem,
    Order,
    PurchaseOrder,
)
from order.tests.test_daily_review_upload import (
    _make_daily_review_excel,
    _make_new_template_excel,
)

User = get_user_model()

UPLOAD_DAILY_URL = "/api/purchase-orders/upload-daily-review/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="spec024_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


def _order(shopify_order_id: int, name: str) -> Order:
    return Order.objects.create(
        shopify_order_id=shopify_order_id, store_type="gimssine", name=name
    )


def _line_item(order: Order, sku: str, quantity: int = 1) -> LineItem:
    return LineItem.objects.create(
        order=order,
        shopify_line_item_id=1,
        sku=sku,
        title="테스트 도서",
        quantity=quantity,
    )


def _upload(auth_client, file_bytes: bytes):
    file_obj = io.BytesIO(file_bytes)
    file_obj.name = "daily_review.xlsx"
    return auth_client.post(UPLOAD_DAILY_URL, data={"file": file_obj}, format="multipart")


# ---------------------------------------------------------------------------
# REQ-OP-001: 확정 발주처
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOtherPublisherConfirmedDistributor:
    def test_agape_publisher_sets_confirmed_distributor(self, auth_client):
        DistributorVendorRule.objects.create(publisher_name="아가페출판사", distributor="agape")

        sku = "9791124590001"
        li = _line_item(_order(91001, "#OP1"), sku)

        res = _upload(auth_client, _make_new_template_excel([
            {
                "sku": sku, "selected": "타출판사", "status": "아가페",
                "order_name": "#OP1", "ky_publisher": "아가페출판사",
                "bs_price": 12000, "ky_price": 11000, "yes24_price": 0,
            },
        ]))
        assert res.status_code == 201

        li.refresh_from_db()
        assert li.purchase_status == "other_publisher"
        assert li.confirmed_distributor == "agape"

    def test_sungseoyunion_publisher_sets_confirmed_distributor(self, auth_client):
        DistributorVendorRule.objects.create(
            publisher_name="성서유니온선교회", distributor="sungseoyunion"
        )

        sku = "9791124590002"
        li = _line_item(_order(91002, "#OP2"), sku)

        res = _upload(auth_client, _make_new_template_excel([
            {
                "sku": sku, "selected": "타출판사", "status": "성서유니온",
                "order_name": "#OP2", "ky_publisher": "성서유니온선교회",
                "bs_price": 8000, "ky_price": 0, "yes24_price": 0,
            },
        ]))
        assert res.status_code == 201

        li.refresh_from_db()
        assert li.confirmed_distributor == "sungseoyunion"

    def test_publisher_resolved_from_kyobo_table_when_column_absent(self, auth_client):
        """레거시 포맷(교보 출판사 컬럼 없음)에서도 KyoboData.publisher 로 판정한다."""
        DistributorVendorRule.objects.create(publisher_name="아가페출판사", distributor="agape")
        sku = "9791124590003"
        KyoboData.objects.create(sku=sku, publisher="아가페출판사")

        li = _line_item(_order(91003, "#OP3"), sku)

        res = _upload(auth_client, _make_daily_review_excel([
            {"order_name": "#OP3", "isbn": sku, "selected": "타출판사", "note": "아가페"},
        ]))
        assert res.status_code == 201

        li.refresh_from_db()
        assert li.confirmed_distributor == "agape"

    def test_unmatched_publisher_leaves_confirmed_distributor_unset(self, auth_client):
        """규칙에 없는 출판사는 기존과 동일하게 확정 발주처를 비워 둔다."""
        sku = "9791124590004"
        li = _line_item(_order(91004, "#OP4"), sku)

        res = _upload(auth_client, _make_new_template_excel([
            {
                "sku": sku, "selected": "타출판사", "status": "기타",
                "order_name": "#OP4", "ky_publisher": "무명출판사",
            },
        ]))
        assert res.status_code == 201

        li.refresh_from_db()
        assert li.purchase_status == "other_publisher"
        assert li.confirmed_distributor is None

    def test_other_cs_labels_do_not_touch_confirmed_fields(self, auth_client):
        """주문취소/주문보류/CS필요 행은 확정 발주처·단가를 건드리지 않는다."""
        DistributorVendorRule.objects.create(publisher_name="아가페출판사", distributor="agape")

        sku = "9791124590005"
        li = _line_item(_order(91005, "#OP5"), sku)
        li.confirmed_distributor = "booxen"
        li.confirmed_price = Decimal("7000")
        li.save(update_fields=["confirmed_distributor", "confirmed_price"])

        res = _upload(auth_client, _make_new_template_excel([
            {
                "sku": sku, "selected": "주문취소", "status": "고객 요청",
                "order_name": "#OP5", "ky_publisher": "아가페출판사",
                "bs_price": 3000,
            },
        ]))
        assert res.status_code == 201

        li.refresh_from_db()
        assert li.purchase_status == "order_cancelled"
        assert li.confirmed_distributor == "booxen"
        assert li.confirmed_price == Decimal("7000")

    def test_other_publisher_row_creates_no_purchase_order(self, auth_client):
        """확정 발주처만 채울 뿐, 타출판사 행의 기존 동작(발주서 미생성)은 유지한다."""
        DistributorVendorRule.objects.create(publisher_name="아가페출판사", distributor="agape")

        sku = "9791124590006"
        _line_item(_order(91006, "#OP6"), sku)

        res = _upload(auth_client, _make_new_template_excel([
            {
                "sku": sku, "selected": "타출판사", "status": "아가페",
                "order_name": "#OP6", "ky_publisher": "아가페출판사",
                "bs_price": 9000,
            },
        ]))
        assert res.status_code == 201
        assert not PurchaseOrder.objects.filter(sku=sku).exists()


# ---------------------------------------------------------------------------
# REQ-OP-002: 확정 단가 = 세 공급가 중 0 제외 최소값
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOtherPublisherConfirmedPrice:
    def test_min_nonzero_price_across_three_columns(self, auth_client):
        DistributorVendorRule.objects.create(publisher_name="아가페출판사", distributor="agape")

        sku = "9791124590011"
        li = _line_item(_order(91011, "#OP11"), sku)

        res = _upload(auth_client, _make_new_template_excel([
            {
                "sku": sku, "selected": "타출판사", "status": "아가페",
                "order_name": "#OP11", "ky_publisher": "아가페출판사",
                "bs_price": 12000, "yes24_price": 9500, "ky_price": 11000,
            },
        ]))
        assert res.status_code == 201

        li.refresh_from_db()
        assert li.confirmed_price == Decimal("9500")

    def test_zero_values_excluded_from_minimum(self, auth_client):
        DistributorVendorRule.objects.create(publisher_name="아가페출판사", distributor="agape")

        sku = "9791124590012"
        li = _line_item(_order(91012, "#OP12"), sku)

        res = _upload(auth_client, _make_new_template_excel([
            {
                "sku": sku, "selected": "타출판사", "status": "아가페",
                "order_name": "#OP12", "ky_publisher": "아가페출판사",
                "bs_price": 0, "yes24_price": 0, "ky_price": 13000,
            },
        ]))
        assert res.status_code == 201

        li.refresh_from_db()
        assert li.confirmed_price == Decimal("13000")

    def test_all_zero_leaves_price_unset(self, auth_client):
        DistributorVendorRule.objects.create(publisher_name="아가페출판사", distributor="agape")

        sku = "9791124590013"
        li = _line_item(_order(91013, "#OP13"), sku)

        res = _upload(auth_client, _make_new_template_excel([
            {
                "sku": sku, "selected": "타출판사", "status": "아가페",
                "order_name": "#OP13", "ky_publisher": "아가페출판사",
                "bs_price": 0, "yes24_price": 0, "ky_price": 0,
            },
        ]))
        assert res.status_code == 201

        li.refresh_from_db()
        assert li.confirmed_distributor == "agape"
        assert li.confirmed_price is None

    def test_choeumgoyuk_selection_uses_min_nonzero_price(self, auth_client):
        """'처음교육' 선택은 기존처럼 발주서를 만들되, 단가는 0 제외 최소값을 쓴다."""
        sku = "9791124590014"
        li = _line_item(_order(91014, "#OP14"), sku, quantity=2)

        res = _upload(auth_client, _make_new_template_excel([
            {
                "sku": sku, "selected": "처음교육", "status": "",
                "order_name": "#OP14",
                "bs_price": 0, "yes24_price": 0, "ky_price": 10500,
            },
        ]))
        assert res.status_code == 201

        li.refresh_from_db()
        assert li.confirmed_distributor == "choeumgoyuk"
        assert li.confirmed_price == Decimal("10500")

        po = PurchaseOrder.objects.get(sku=sku)
        assert po.distributor == "choeumgoyuk"
        assert po.unit_price == Decimal("10500")

    def test_booxen_selection_still_uses_own_supply_price(self, auth_client):
        """회귀 방지: BOOXEN/교보/YES24 확정 행은 최소값 규칙 대상이 아니다."""
        sku = "9791124590015"
        li = _line_item(_order(91015, "#OP15"), sku)

        res = _upload(auth_client, _make_new_template_excel([
            {
                "sku": sku, "selected": "BOOXEN", "status": "",
                "order_name": "#OP15",
                "bs_price": 12000, "yes24_price": 9500, "ky_price": 11000,
            },
        ]))
        assert res.status_code == 201

        li.refresh_from_db()
        assert li.confirmed_distributor == "booxen"
        assert li.confirmed_price == Decimal("12000")
