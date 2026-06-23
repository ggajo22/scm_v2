"""
TDD tests for SPEC-AUTO-DIST-001: auto_select_distributor() business logic.

Test scenarios cover all 5 decision steps:
  Step 0  - DistributorVendorRule override (agape / choeumgoyuk)
  Step 1  - Warehouse stock priority (korea / west)
  Step 2A - Both vendors have enough stock → price & return comparison
  Step 2B - Only bookseen has stock
  Step 2C - Only kyobo has stock
  Step 2D - Neither has stock → status/price heuristics
  Step 2E - Kyobo-returnable override after Step 2D
  Step 3  - price_diff_alert calculation
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from order.excel_utils import auto_select_distributor


def _vc(**kwargs) -> SimpleNamespace:
    """Helper: create a SimpleNamespace mimicking vendor comparison fields."""
    defaults = {
        "bookseen_available": None,
        "bookseen_price": None,
        "bookseen_stock": None,
        "bookseen_returnable": None,
        "bookseen_status": None,
        "kyobo_available": None,
        "kyobo_price": None,
        "kyobo_stock": None,
        "kyobo_returnable": None,
        "kyobo_status": None,
        "kyobo_publisher": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Step 0: DistributorVendorRule override
# ---------------------------------------------------------------------------


class TestStep0VendorRuleOverride:
    """REQ-AD-001: DistributorVendorRule takes priority over all other steps."""

    def test_agape_rule_when_kyobo_publisher_contains_agape(self):
        """kyobo_publisher에 '아가페'가 포함되면 agape로 선택되어야 한다."""
        vc = _vc(kyobo_publisher="아가페출판사")
        vendor_rules = [("아가페출판사", "agape")]
        result = auto_select_distributor(vc=vc, total_qty=5, vendor_rules=vendor_rules)
        assert result["selected_distributor"] == "agape"
        assert result["candidate_basis"] == "아가페규칙"
        assert result["price_diff_alert"] is False

    def test_agape_rule_partial_match(self):
        """kyobo_publisher가 '아가페'를 포함하는 부분 문자열이어도 agape로 선택되어야 한다."""
        vc = _vc(kyobo_publisher="어린이아가페")
        vendor_rules = [("other", "agape")]
        result = auto_select_distributor(vc=vc, total_qty=3, vendor_rules=vendor_rules)
        assert result["selected_distributor"] == "agape"
        assert result["candidate_basis"] == "아가페규칙"

    def test_choeumgoyuk_rule_exact_match(self):
        """kyobo_publisher가 정확히 '처음교육'이면 choeumgoyuk으로 선택되어야 한다."""
        vc = _vc(kyobo_publisher="처음교육")
        vendor_rules = [("처음교육", "choeumgoyuk")]
        result = auto_select_distributor(vc=vc, total_qty=2, vendor_rules=vendor_rules)
        assert result["selected_distributor"] == "choeumgoyuk"
        assert result["candidate_basis"] == "처음교육규칙"
        assert result["price_diff_alert"] is False

    def test_choeumgoyuk_rule_no_partial_match(self):
        """kyobo_publisher가 '처음교육'을 포함하지만 정확히 일치하지 않으면 적용되지 않아야 한다."""
        vc = _vc(
            kyobo_publisher="처음교육출판",
            bookseen_stock=10,
            kyobo_stock=10,
            bookseen_price=Decimal("10000"),
            kyobo_price=Decimal("10000"),
        )
        vendor_rules = [("처음교육", "choeumgoyuk")]
        result = auto_select_distributor(vc=vc, total_qty=5, vendor_rules=vendor_rules)
        # choeumgoyuk 규칙이 적용되지 않아야 함 (Step 2A로 진행)
        assert result["selected_distributor"] != "choeumgoyuk"

    def test_no_vendor_rules_skips_step0(self):
        """vendor_rules가 None이면 Step 0을 건너뛰어야 한다."""
        vc = _vc(
            kyobo_publisher="처음교육",
            bookseen_stock=10,
            bookseen_price=Decimal("10000"),
            kyobo_stock=0,
        )
        result = auto_select_distributor(vc=vc, total_qty=5, vendor_rules=None)
        # Step 0 건너뜀 → Step 2B (북센만 재고)
        assert result["selected_distributor"] == "bookseen"


# ---------------------------------------------------------------------------
# Step 1: Warehouse stock priority
# ---------------------------------------------------------------------------


class TestStep1WarehouseStock:
    """REQ-AD-002: 창고 재고가 충분하면 벤더 비교 전에 창고로 선택."""

    def test_korea_stock_sufficient_returns_warehouse(self):
        """한국 창고 재고가 total_qty 이상이면 'warehouse'를 반환해야 한다."""
        vc = _vc(
            bookseen_price=Decimal("15000"),
            kyobo_price=Decimal("14000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5, korea_stock=5)
        assert result["selected_distributor"] == "warehouse"
        assert result["candidate_basis"] == "재고우선"

    def test_korea_stock_more_than_sufficient(self):
        """한국 창고 재고가 total_qty를 초과해도 'warehouse'를 반환해야 한다."""
        vc = _vc()
        result = auto_select_distributor(vc=vc, total_qty=3, korea_stock=100)
        assert result["selected_distributor"] == "warehouse"

    def test_ca_stock_sufficient_returns_warehouse_west(self):
        """한국 재고 부족 시 CA 창고 재고가 충분하면 'warehouse_west'를 반환해야 한다."""
        vc = _vc(
            bookseen_price=Decimal("15000"),
            kyobo_price=Decimal("14000"),
        )
        result = auto_select_distributor(
            vc=vc, total_qty=5, korea_stock=2, ca_stock=5
        )
        assert result["selected_distributor"] == "warehouse_west"
        assert result["candidate_basis"] == "서부창고확인"

    def test_nj_stock_sufficient_returns_warehouse_west(self):
        """한국 재고 부족 시 NJ 창고 재고가 충분하면 'warehouse_west'를 반환해야 한다."""
        vc = _vc()
        result = auto_select_distributor(
            vc=vc, total_qty=5, korea_stock=0, ca_stock=0, nj_stock=10
        )
        assert result["selected_distributor"] == "warehouse_west"
        assert result["candidate_basis"] == "서부창고확인"

    def test_no_warehouse_stock_proceeds_to_vendor_comparison(self):
        """창고 재고가 모두 부족하면 벤더 비교 단계로 진행해야 한다."""
        vc = _vc(
            bookseen_stock=10,
            kyobo_stock=10,
            bookseen_price=Decimal("10000"),
            kyobo_price=Decimal("11000"),
        )
        result = auto_select_distributor(
            vc=vc, total_qty=5, korea_stock=0, ca_stock=0, nj_stock=0
        )
        # 창고 선택이 아닌 벤더 선택으로 진행
        assert result["selected_distributor"] not in ("warehouse", "warehouse_west")


# ---------------------------------------------------------------------------
# Step 2A: Both vendors have sufficient stock
# ---------------------------------------------------------------------------


class TestStep2ABothVendorsHaveStock:
    """REQ-AD-003: 양사 재고 충분 시 가격·반품 기준 선택."""

    def test_bookseen_cheaper_selects_bookseen(self):
        """북센 가격이 더 저렴하면 bookseen을 선택해야 한다."""
        vc = _vc(
            bookseen_stock=10,
            kyobo_stock=10,
            bookseen_price=Decimal("9000"),
            kyobo_price=Decimal("10000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "bookseen"
        assert result["candidate_basis"] == "양사재고/북센저가"

    def test_kyobo_cheaper_selects_kyobo(self):
        """교보 가격이 더 저렴하면 kyobo를 선택해야 한다."""
        vc = _vc(
            bookseen_stock=10,
            kyobo_stock=10,
            bookseen_price=Decimal("10000"),
            kyobo_price=Decimal("9000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "kyobo"
        assert result["candidate_basis"] == "양사재고/교보저가"

    def test_same_price_bookseen_returnable_selects_bookseen(self):
        """동가이고 북센만 반품 가능하면 bookseen을 선택해야 한다."""
        vc = _vc(
            bookseen_stock=10,
            kyobo_stock=10,
            bookseen_price=Decimal("10000"),
            kyobo_price=Decimal("10000"),
            bookseen_returnable=True,
            kyobo_returnable=False,
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "bookseen"
        assert result["candidate_basis"] == "양사재고/동가/북센반품"

    def test_same_price_kyobo_returnable_selects_kyobo(self):
        """동가이고 교보만 반품 가능하면 kyobo를 선택해야 한다."""
        vc = _vc(
            bookseen_stock=10,
            kyobo_stock=10,
            bookseen_price=Decimal("10000"),
            kyobo_price=Decimal("10000"),
            bookseen_returnable=False,
            kyobo_returnable=True,
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "kyobo"
        assert result["candidate_basis"] == "양사재고/동가/교보반품"

    def test_same_price_same_returnability_selects_bookseen(self):
        """동가이고 반품 조건도 동일하면 bookseen을 선택해야 한다."""
        vc = _vc(
            bookseen_stock=10,
            kyobo_stock=10,
            bookseen_price=Decimal("10000"),
            kyobo_price=Decimal("10000"),
            bookseen_returnable=True,
            kyobo_returnable=True,
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "bookseen"
        assert result["candidate_basis"] == "양사재고/동가/반품동일"

    def test_only_kyobo_price_available(self):
        """교보 가격만 있고 북센 가격이 없으면 교보를 선택해야 한다."""
        vc = _vc(
            bookseen_stock=10,
            kyobo_stock=10,
            bookseen_price=None,
            kyobo_price=Decimal("10000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "kyobo"
        assert result["candidate_basis"] == "양사재고/교보가격만확인"

    def test_only_bookseen_price_available(self):
        """북센 가격만 있고 교보 가격이 없으면 북센을 선택해야 한다."""
        vc = _vc(
            bookseen_stock=10,
            kyobo_stock=10,
            bookseen_price=Decimal("10000"),
            kyobo_price=None,
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "bookseen"
        assert result["candidate_basis"] == "양사재고/북센가격만확인"

    def test_no_prices_available_defaults_to_bookseen(self):
        """양사 모두 가격이 없으면 bookseen을 기본 선택해야 한다."""
        vc = _vc(
            bookseen_stock=10,
            kyobo_stock=10,
            bookseen_price=None,
            kyobo_price=None,
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "bookseen"
        assert result["candidate_basis"] == "양사재고/가격없음"


# ---------------------------------------------------------------------------
# Step 2B/2C: Only one vendor has sufficient stock
# ---------------------------------------------------------------------------


class TestStep2BCSingleVendorStock:
    """REQ-AD-004: 단독 재고 기준 선택."""

    def test_only_bookseen_stock_selects_bookseen(self):
        """북센만 재고가 충분하면 bookseen을 선택해야 한다."""
        vc = _vc(
            bookseen_stock=10,
            kyobo_stock=3,
            bookseen_price=Decimal("12000"),
            kyobo_price=Decimal("10000"),  # 교보가 더 저렴해도 재고 우선
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "bookseen"
        assert result["candidate_basis"] == "북센재고우선"

    def test_only_kyobo_stock_selects_kyobo(self):
        """교보만 재고가 충분하면 kyobo를 선택해야 한다."""
        vc = _vc(
            bookseen_stock=2,
            kyobo_stock=10,
            bookseen_price=Decimal("9000"),  # 북센이 더 저렴해도 재고 우선
            kyobo_price=Decimal("12000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "kyobo"
        assert result["candidate_basis"] == "교보재고우선"


# ---------------------------------------------------------------------------
# Step 2D: Neither vendor has sufficient stock
# ---------------------------------------------------------------------------


class TestStep2DNoStock:
    """REQ-AD-005: 양사 재고 없음 시 상태·가격 우위 기반 선택."""

    def test_bookseen_normal_and_cheaper_selects_bookseen(self):
        """북센 상태 정상이고 북센 가격이 저렴하면 bookseen을 선택해야 한다."""
        vc = _vc(
            bookseen_stock=2,
            kyobo_stock=2,
            bookseen_status="정상",
            kyobo_status="정상",
            bookseen_price=Decimal("9000"),
            kyobo_price=Decimal("10000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "bookseen"
        assert result["candidate_basis"] == "양사재고없음"

    def test_bookseen_normal_but_kyobo_cheaper_kyobo_normal_selects_kyobo(self):
        """북센 상태 정상이나 교보가 더 저렴하고 교보도 정상이면 kyobo를 선택해야 한다."""
        vc = _vc(
            bookseen_stock=2,
            kyobo_stock=2,
            bookseen_status="정상",
            kyobo_status="정상",
            bookseen_price=Decimal("11000"),
            kyobo_price=Decimal("10000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "kyobo"
        assert result["candidate_basis"] == "양사재고없음"

    def test_bookseen_normal_kyobo_cheaper_but_kyobo_not_normal_selects_check_required(
        self,
    ):
        """북센 정상이나 교보가 저렴하고 교보 상태 비정상이면 check_required를 선택해야 한다."""
        vc = _vc(
            bookseen_stock=2,
            kyobo_stock=2,
            bookseen_status="정상",
            kyobo_status="품절",
            bookseen_price=Decimal("11000"),
            kyobo_price=Decimal("10000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "check_required"
        assert result["candidate_basis"] == "양사재고없음"

    def test_bookseen_not_normal_kyobo_normal_selects_kyobo(self):
        """북센 비정상이고 교보 상태 정상이면 kyobo를 선택해야 한다."""
        vc = _vc(
            bookseen_stock=2,
            kyobo_stock=2,
            bookseen_status="품절",
            kyobo_status="정상",
            bookseen_price=Decimal("9000"),
            kyobo_price=Decimal("10000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "kyobo"
        assert result["candidate_basis"] == "양사재고없음"

    def test_bookseen_not_normal_kyobo_order_sale_selects_kyobo(self):
        """북센 비정상이고 교보 상태 '주문판매'이면 kyobo를 선택해야 한다."""
        vc = _vc(
            bookseen_stock=0,
            kyobo_stock=0,
            bookseen_status="절판",
            kyobo_status="주문판매",
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "kyobo"
        assert result["candidate_basis"] == "양사재고없음"

    def test_both_not_normal_selects_check_required(self):
        """양사 모두 비정상이면 check_required를 선택해야 한다."""
        vc = _vc(
            bookseen_stock=0,
            kyobo_stock=0,
            bookseen_status="품절",
            kyobo_status="품절",
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "check_required"
        assert result["candidate_basis"] == "양사재고없음"


# ---------------------------------------------------------------------------
# Step 2E: Kyobo-returnable override
# ---------------------------------------------------------------------------


class TestStep2EReturnableOverride:
    """REQ-AD-006: 교보 반품 가능 시 Step 2D 결과 오버라이드."""

    def test_kyobo_returnable_and_kyobo_normal_overrides_to_kyobo(self):
        """Step 2D 결과와 무관하게 교보만 반품 가능하고 교보 정상이면 kyobo로 오버라이드해야 한다."""
        # Step 2D → bookseen (북센 정상, 북센 저렴)
        vc = _vc(
            bookseen_stock=2,
            kyobo_stock=2,
            bookseen_status="정상",
            kyobo_status="정상",
            bookseen_price=Decimal("9000"),
            kyobo_price=Decimal("10000"),
            bookseen_returnable=False,
            kyobo_returnable=True,
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        # Step 2E 오버라이드: kyobo_returnable=True, bs_ret!=True, ky_status="정상" → kyobo
        assert result["selected_distributor"] == "kyobo"

    def test_kyobo_returnable_but_kyobo_not_normal_overrides_to_check_required(self):
        """교보만 반품 가능하지만 교보 상태 비정상이면 check_required로 오버라이드해야 한다."""
        vc = _vc(
            bookseen_stock=2,
            kyobo_stock=2,
            bookseen_status="정상",
            kyobo_status="품절",
            bookseen_price=Decimal("9000"),
            kyobo_price=Decimal("10000"),
            bookseen_returnable=False,
            kyobo_returnable=True,
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "check_required"

    def test_both_returnable_no_override(self):
        """양사 모두 반품 가능하면 Step 2E 오버라이드가 적용되지 않아야 한다."""
        vc = _vc(
            bookseen_stock=2,
            kyobo_stock=2,
            bookseen_status="정상",
            kyobo_status="정상",
            bookseen_price=Decimal("9000"),
            kyobo_price=Decimal("10000"),
            bookseen_returnable=True,
            kyobo_returnable=True,
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        # 오버라이드 없음 → Step 2D 결과 유지 (bookseen 저렴)
        assert result["selected_distributor"] == "bookseen"


# ---------------------------------------------------------------------------
# Price diff and alert
# ---------------------------------------------------------------------------


class TestPriceDiffAlert:
    """REQ-AD-007: 가격차이 알림 계산."""

    def test_price_diff_calculated_correctly(self):
        """price_diff = bookseen_price - kyobo_price 로 계산되어야 한다."""
        vc = _vc(
            bookseen_stock=10,
            kyobo_stock=10,
            bookseen_price=Decimal("15000"),
            kyobo_price=Decimal("12000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["price_diff"] == Decimal("3000")

    def test_price_diff_none_when_bookseen_price_none(self):
        """북센 가격이 없으면 price_diff는 None이어야 한다."""
        vc = _vc(
            bookseen_stock=10,
            kyobo_stock=10,
            bookseen_price=None,
            kyobo_price=Decimal("10000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["price_diff"] is None

    def test_price_diff_alert_true_when_check_required_and_large_diff(self):
        """check_required이고 가격차이 >= 3000이면 price_diff_alert=True이어야 한다."""
        vc = _vc(
            bookseen_stock=0,
            kyobo_stock=0,
            bookseen_status="품절",
            kyobo_status="품절",
            bookseen_price=Decimal("15000"),
            kyobo_price=Decimal("10000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "check_required"
        assert result["price_diff_alert"] is True

    def test_price_diff_alert_false_when_diff_below_threshold(self):
        """가격차이 < 3000이면 price_diff_alert=False이어야 한다."""
        vc = _vc(
            bookseen_stock=0,
            kyobo_stock=0,
            bookseen_status="품절",
            kyobo_status="품절",
            bookseen_price=Decimal("12000"),
            kyobo_price=Decimal("10000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["price_diff_alert"] is False

    def test_price_diff_alert_true_when_bookseen_selected_but_kyobo_cheaper(self):
        """bookseen 선택되었으나 북센 가격이 더 비싸고 차이 >= 3000이면 alert=True이어야 한다."""
        # Step 2B: bookseen만 재고 있음 → bookseen 선택
        vc = _vc(
            bookseen_stock=10,
            kyobo_stock=0,
            bookseen_price=Decimal("15000"),
            kyobo_price=Decimal("10000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "bookseen"
        assert result["price_diff_alert"] is True

    def test_price_diff_alert_false_when_bookseen_selected_and_bookseen_cheaper(self):
        """bookseen 선택되고 북센 가격이 더 저렴하면 alert=False이어야 한다."""
        vc = _vc(
            bookseen_stock=10,
            kyobo_stock=10,
            bookseen_price=Decimal("9000"),
            kyobo_price=Decimal("15000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "bookseen"
        assert result["price_diff_alert"] is False

    def test_price_diff_alert_true_when_kyobo_selected_but_kyobo_more_expensive(self):
        """kyobo 선택되었으나 교보 가격이 더 비싸고 차이 >= 3000이면 alert=True이어야 한다."""
        # Step 2C: kyobo만 재고 있음 → kyobo 선택
        vc = _vc(
            bookseen_stock=0,
            kyobo_stock=10,
            bookseen_price=Decimal("10000"),
            kyobo_price=Decimal("15000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert result["selected_distributor"] == "kyobo"
        assert result["price_diff_alert"] is True


# ---------------------------------------------------------------------------
# Return value structure
# ---------------------------------------------------------------------------


class TestReturnValueStructure:
    """REQ-AD-008: 반환값에 candidate_basis가 항상 포함되어야 한다."""

    def test_return_dict_has_all_required_keys(self):
        """반환 딕셔너리에 4개 필수 키가 모두 있어야 한다."""
        vc = _vc(bookseen_stock=10, kyobo_stock=10)
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert "selected_distributor" in result
        assert "candidate_basis" in result
        assert "price_diff" in result
        assert "price_diff_alert" in result

    def test_candidate_basis_always_non_empty_string(self):
        """candidate_basis는 항상 비어있지 않은 문자열이어야 한다."""
        vc = _vc(
            bookseen_stock=10,
            kyobo_stock=10,
            bookseen_price=Decimal("10000"),
            kyobo_price=Decimal("10000"),
        )
        result = auto_select_distributor(vc=vc, total_qty=5)
        assert isinstance(result["candidate_basis"], str)
        assert len(result["candidate_basis"]) > 0
