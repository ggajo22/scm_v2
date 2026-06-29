"""
TDD tests for SPEC-SHOPIFY-SKU-SET-001.

Covers:
  AC-SKU-SET-001  ShopifySkuSetMapping model + unique_together constraint
  AC-SKU-SET-002  GET /api/shopify-sku-sets/ returns all bundles with book_title
  AC-SKU-SET-003  POST creates bundle
  AC-SKU-SET-004  POST validation (empty bundle_sku, empty member_isbns)
  AC-SKU-SET-005  PUT replaces bundle atomically
  AC-SKU-SET-006  DELETE removes bundle; DELETE non-existent -> 404
  AC-SKU-SET-007  UnorderedItemsView bundle expansion
  AC-SKU-SET-008  Unauthenticated access -> 401
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import LineItem, Order, ShopifySkuSetMapping

User = get_user_model()

LIST_URL = "/api/shopify-sku-sets/"
UNORDERED_URL = "/api/purchase-orders/unordered/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="sku_set_test", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def bundle_mapping(db):
    """Create a sample bundle mapping: GITANMATH-F SET -> 2 ISBNs."""
    ShopifySkuSetMapping.objects.create(bundle_sku="GITANMATH-F SET", member_isbn="9788926025451", sort_order=0)
    ShopifySkuSetMapping.objects.create(bundle_sku="GITANMATH-F SET", member_isbn="9788926025468", sort_order=1)
    return "GITANMATH-F SET"


@pytest.fixture
def order_with_bundle_lineitem(db):
    """Create Order + LineItem with bundle SKU."""
    order = Order.objects.create(
        shopify_order_id=99001,
        store_type="gimssine",
        order_number=1001,
        name="#1001",
    )
    li = LineItem.objects.create(
        order=order,
        shopify_line_item_id=88001,
        sku="GITANMATH-F SET",
        title="기탄수학 F 세트",
        quantity=2,
        purchase_status="unordered",
    )
    return order, li


# ---------------------------------------------------------------------------
# AC-SKU-SET-001: Model + unique_together constraint
# ---------------------------------------------------------------------------


class TestShopifySkuSetMappingModel:
    def test_create_mapping(self, db):
        mapping = ShopifySkuSetMapping.objects.create(
            bundle_sku="TEST-SET",
            member_isbn="1234567890",
            sort_order=0,
        )
        assert mapping.pk is not None
        assert str(mapping) == "ShopifySkuSetMapping(TEST-SET -> 1234567890)"

    def test_unique_together_constraint(self, db):
        ShopifySkuSetMapping.objects.create(bundle_sku="TEST-SET", member_isbn="1234567890")
        with pytest.raises(IntegrityError):
            ShopifySkuSetMapping.objects.create(bundle_sku="TEST-SET", member_isbn="1234567890")

    def test_ordering(self, db):
        ShopifySkuSetMapping.objects.create(bundle_sku="A-SET", member_isbn="isbn2", sort_order=1)
        ShopifySkuSetMapping.objects.create(bundle_sku="A-SET", member_isbn="isbn1", sort_order=0)
        qs = list(ShopifySkuSetMapping.objects.filter(bundle_sku="A-SET"))
        assert qs[0].sort_order == 0
        assert qs[1].sort_order == 1


# ---------------------------------------------------------------------------
# AC-SKU-SET-008: Unauthenticated access -> 401
# ---------------------------------------------------------------------------


class TestUnauthenticatedAccess:
    def test_list_requires_auth(self, db):
        client = APIClient()
        resp = client.get(LIST_URL)
        assert resp.status_code == 401

    def test_post_requires_auth(self, db):
        client = APIClient()
        resp = client.post(LIST_URL, {"bundle_sku": "X", "member_isbns": ["111"]}, format="json")
        assert resp.status_code == 401

    def test_detail_get_requires_auth(self, db):
        client = APIClient()
        resp = client.get(f"{LIST_URL}X-SET/")
        assert resp.status_code == 401

    def test_detail_put_requires_auth(self, db):
        client = APIClient()
        resp = client.put(f"{LIST_URL}X-SET/", {"member_isbns": ["111"]}, format="json")
        assert resp.status_code == 401

    def test_detail_delete_requires_auth(self, db):
        client = APIClient()
        resp = client.delete(f"{LIST_URL}X-SET/")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# AC-SKU-SET-002: GET /api/shopify-sku-sets/ returns all bundles with book_title
# ---------------------------------------------------------------------------


class TestShopifySkuSetListView:
    def test_get_empty(self, auth_client):
        resp = auth_client.get(LIST_URL)
        assert resp.status_code == 200
        assert resp.data == []

    def test_get_bundles_grouped(self, auth_client, bundle_mapping):
        resp = auth_client.get(LIST_URL)
        assert resp.status_code == 200
        data = resp.data
        assert len(data) == 1
        bundle = data[0]
        assert bundle["bundle_sku"] == "GITANMATH-F SET"
        assert len(bundle["member_isbns"]) == 2
        # ISBNs should be sorted by sort_order
        assert bundle["member_isbns"][0]["isbn"] == "9788926025451"
        assert bundle["member_isbns"][0]["sort_order"] == 0
        assert bundle["member_isbns"][1]["isbn"] == "9788926025468"

    def test_get_book_title_null_when_no_inven(self, auth_client, bundle_mapping):
        resp = auth_client.get(LIST_URL)
        assert resp.status_code == 200
        # No Inven records exist, so book_title should be null
        for item in resp.data[0]["member_isbns"]:
            assert item["book_title"] is None

    def test_get_book_title_populated_from_inven(self, auth_client, db):
        """When Inven + Info records exist, book_title should be populated."""
        from book.models import Info, Inven

        inven = Inven.objects.create(inven_SKU="9788926025451")
        Info.objects.create(inven=inven, name="기탄수학 F1")

        ShopifySkuSetMapping.objects.create(bundle_sku="TEST-SET", member_isbn="9788926025451", sort_order=0)
        ShopifySkuSetMapping.objects.create(bundle_sku="TEST-SET", member_isbn="9788926025468", sort_order=1)

        resp = auth_client.get(LIST_URL)
        assert resp.status_code == 200
        bundle = resp.data[0]
        isbn_map = {item["isbn"]: item["book_title"] for item in bundle["member_isbns"]}
        assert isbn_map["9788926025451"] == "기탄수학 F1"
        assert isbn_map["9788926025468"] is None


# ---------------------------------------------------------------------------
# AC-SKU-SET-003: POST creates bundle
# ---------------------------------------------------------------------------


class TestShopifySkuSetCreateView:
    def test_post_creates_bundle(self, auth_client, db):
        payload = {"bundle_sku": "TEST-SET", "member_isbns": ["111", "222"]}
        resp = auth_client.post(LIST_URL, payload, format="json")
        assert resp.status_code == 201
        assert ShopifySkuSetMapping.objects.filter(bundle_sku="TEST-SET").count() == 2

    def test_post_returns_bundle_data(self, auth_client, db):
        payload = {"bundle_sku": "TEST-SET", "member_isbns": ["111", "222"]}
        resp = auth_client.post(LIST_URL, payload, format="json")
        assert resp.status_code == 201
        assert resp.data["bundle_sku"] == "TEST-SET"
        assert len(resp.data["member_isbns"]) == 2

    def test_post_sets_sort_order_by_index(self, auth_client, db):
        payload = {"bundle_sku": "TEST-SET", "member_isbns": ["aaa", "bbb", "ccc"]}
        auth_client.post(LIST_URL, payload, format="json")
        mappings = list(ShopifySkuSetMapping.objects.filter(bundle_sku="TEST-SET").order_by("sort_order"))
        assert mappings[0].member_isbn == "aaa"
        assert mappings[0].sort_order == 0
        assert mappings[2].sort_order == 2


# ---------------------------------------------------------------------------
# AC-SKU-SET-004: POST validation
# ---------------------------------------------------------------------------


class TestShopifySkuSetValidation:
    def test_post_empty_bundle_sku_returns_400(self, auth_client, db):
        resp = auth_client.post(LIST_URL, {"bundle_sku": "", "member_isbns": ["111"]}, format="json")
        assert resp.status_code == 400

    def test_post_missing_bundle_sku_returns_400(self, auth_client, db):
        resp = auth_client.post(LIST_URL, {"member_isbns": ["111"]}, format="json")
        assert resp.status_code == 400

    def test_post_empty_member_isbns_returns_400(self, auth_client, db):
        resp = auth_client.post(LIST_URL, {"bundle_sku": "TEST", "member_isbns": []}, format="json")
        assert resp.status_code == 400

    def test_post_missing_member_isbns_returns_400(self, auth_client, db):
        resp = auth_client.post(LIST_URL, {"bundle_sku": "TEST"}, format="json")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# AC-SKU-SET-005: PUT replaces bundle atomically
# ---------------------------------------------------------------------------


class TestShopifySkuSetDetailPut:
    def test_put_replaces_bundle(self, auth_client, bundle_mapping):
        url = f"{LIST_URL}GITANMATH-F SET/"
        resp = auth_client.put(url, {"member_isbns": ["NEW-ISBN-1", "NEW-ISBN-2"]}, format="json")
        assert resp.status_code == 200
        remaining = list(ShopifySkuSetMapping.objects.filter(bundle_sku="GITANMATH-F SET").order_by("sort_order"))
        assert len(remaining) == 2
        assert remaining[0].member_isbn == "NEW-ISBN-1"
        assert remaining[1].member_isbn == "NEW-ISBN-2"
        # Old ISBNs should be gone
        assert not ShopifySkuSetMapping.objects.filter(member_isbn="9788926025451").exists()

    def test_put_nonexistent_returns_404(self, auth_client, db):
        resp = auth_client.put(f"{LIST_URL}NONEXISTENT-SET/", {"member_isbns": ["111"]}, format="json")
        assert resp.status_code == 404

    def test_get_detail(self, auth_client, bundle_mapping):
        resp = auth_client.get(f"{LIST_URL}GITANMATH-F SET/")
        assert resp.status_code == 200
        assert resp.data["bundle_sku"] == "GITANMATH-F SET"
        assert len(resp.data["member_isbns"]) == 2

    def test_get_detail_nonexistent_returns_404(self, auth_client, db):
        resp = auth_client.get(f"{LIST_URL}NONEXISTENT-SET/")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# AC-SKU-SET-006: DELETE removes bundle
# ---------------------------------------------------------------------------


class TestShopifySkuSetDetailDelete:
    def test_delete_bundle(self, auth_client, bundle_mapping):
        url = f"{LIST_URL}GITANMATH-F SET/"
        resp = auth_client.delete(url)
        assert resp.status_code == 204
        assert ShopifySkuSetMapping.objects.filter(bundle_sku="GITANMATH-F SET").count() == 0

    def test_delete_nonexistent_returns_404(self, auth_client, db):
        resp = auth_client.delete(f"{LIST_URL}NONEXISTENT-SET/")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# AC-SKU-SET-007: UnorderedItemsView bundle expansion
# ---------------------------------------------------------------------------


class TestUnorderedItemsBundleExpansion:
    def test_bundle_sku_expanded(self, auth_client, order_with_bundle_lineitem, bundle_mapping):
        resp = auth_client.get(UNORDERED_URL)
        assert resp.status_code == 200
        results = resp.data["results"]
        # "GITANMATH-F SET" should be expanded to 2 member ISBNs
        bundle_results = [r for r in results if r.get("bundle_sku") == "GITANMATH-F SET"]
        assert len(bundle_results) == 2
        skus = {r["sku"] for r in bundle_results}
        assert skus == {"9788926025451", "9788926025468"}
        for r in bundle_results:
            assert r["is_bundle_member"] is True
            assert r["quantity"] == 2  # Original quantity preserved

    def test_non_bundle_sku_not_expanded(self, auth_client, db):
        order = Order.objects.create(
            shopify_order_id=99002,
            store_type="gimssine",
            order_number=1002,
            name="#1002",
        )
        LineItem.objects.create(
            order=order,
            shopify_line_item_id=88002,
            sku="NORMAL-ISBN",
            title="일반 도서",
            quantity=1,
            purchase_status="unordered",
        )
        resp = auth_client.get(UNORDERED_URL)
        assert resp.status_code == 200
        results = resp.data["results"]
        normal = [r for r in results if r["sku"] == "NORMAL-ISBN"]
        assert len(normal) == 1
        assert normal[0]["is_bundle_member"] is False
        assert normal[0]["bundle_sku"] is None

    def test_bundle_count_reflects_expansion(self, auth_client, order_with_bundle_lineitem, bundle_mapping):
        resp = auth_client.get(UNORDERED_URL)
        assert resp.status_code == 200
        # count should be 2 (expanded, not 1)
        assert resp.data["count"] == 2
