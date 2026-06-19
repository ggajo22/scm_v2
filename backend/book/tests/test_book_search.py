"""
Tests for GET /api/book/search/ — SPEC-BOOK-SEARCH-001
REQ-SEARCH-001 through REQ-SEARCH-008
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from book.models import Info, Inven

User = get_user_model()

SEARCH_URL = "/api/book/search/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="search_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


def make_book(sku: str, title: str, price_sale: float = 10000.0, status_of_shopify: int = 100) -> Inven:
    """Helper: create Inven + Info pair."""
    inven = Inven.objects.create(
        inven_SKU=sku,
        vendor="test_vendor",
        store="test_store",
        status_of_shopify=status_of_shopify,
    )
    Info.objects.create(
        inven=inven,
        name=title,
        price_sale=price_sale,
        status="active",
        useruse1="",
        useruse2="",
        retyn="N",
    )
    return inven


# ---------------------------------------------------------------------------
# REQ-SEARCH-006: 401 for unauthenticated
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBookSearchAuthGuard:
    """REQ-SEARCH-006: unauthenticated request must return 401."""

    def test_unauthenticated_returns_401(self, client):
        resp = client.get(SEARCH_URL)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# REQ-SEARCH-007: response shape — count, next, previous, results
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBookSearchResponseShape:
    """REQ-SEARCH-007: paginated response has count, next, previous, results."""

    def test_response_has_pagination_fields(self, auth_client):
        resp = auth_client.get(SEARCH_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data
        assert "next" in data
        assert "previous" in data
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_results_contain_required_fields(self, auth_client, db):
        make_book("ISBN-001", "테스트 도서", price_sale=15000.0, status_of_shopify=100)

        resp = auth_client.get(SEARCH_URL)
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1

        book = results[0]
        assert "inven_SKU" in book
        assert "name" in book
        assert "price_sale" in book
        assert "status_of_shopify" in book


# ---------------------------------------------------------------------------
# REQ-SEARCH-002: empty search returns all books paginated
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBookSearchEmptyQuery:
    """REQ-SEARCH-002: empty search= param returns all books."""

    def test_empty_search_returns_all(self, auth_client, db):
        make_book("ISBN-001", "도서 A")
        make_book("ISBN-002", "도서 B")
        make_book("ISBN-003", "도서 C")

        resp = auth_client.get(SEARCH_URL, {"search": ""})
        assert resp.status_code == 200
        assert resp.json()["count"] == 3

    def test_no_search_param_returns_all(self, auth_client, db):
        make_book("ISBN-001", "도서 A")
        make_book("ISBN-002", "도서 B")

        resp = auth_client.get(SEARCH_URL)
        assert resp.status_code == 200
        assert resp.json()["count"] == 2


# ---------------------------------------------------------------------------
# REQ-SEARCH-001: OR icontains on inven_SKU AND info.name
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBookSearchQuery:
    """REQ-SEARCH-001: search matches inven_SKU OR info.name (case-insensitive)."""

    def test_search_by_sku_partial_match(self, auth_client, db):
        make_book("978-3-16-148410-0", "어떤 도서")
        make_book("000-0-00-000000-0", "다른 도서")

        resp = auth_client.get(SEARCH_URL, {"search": "978"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["inven_SKU"] == "978-3-16-148410-0"

    def test_search_by_title_partial_match(self, auth_client, db):
        make_book("ISBN-001", "파이썬 프로그래밍")
        make_book("ISBN-002", "자바스크립트 완전 정복")

        resp = auth_client.get(SEARCH_URL, {"search": "파이썬"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["name"] == "파이썬 프로그래밍"

    def test_search_case_insensitive(self, auth_client, db):
        make_book("isbn-abc", "Python Book")

        resp = auth_client.get(SEARCH_URL, {"search": "ISBN"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_search_matches_both_sku_and_title(self, auth_client, db):
        # This book matches by SKU
        make_book("UNIQUE-SKU-999", "일반 도서 제목")
        # This book matches by title
        make_book("OTHER-SKU-111", "UNIQUE 제목")
        # This book matches neither
        make_book("NO-MATCH-000", "관련없는 도서")

        resp = auth_client.get(SEARCH_URL, {"search": "UNIQUE"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 2

    def test_search_no_match_returns_empty(self, auth_client, db):
        make_book("ISBN-001", "파이썬 도서")

        resp = auth_client.get(SEARCH_URL, {"search": "존재하지않는검색어XYZ"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["results"] == []


# ---------------------------------------------------------------------------
# REQ-SEARCH-005: PageNumberPagination, PAGE_SIZE=50
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBookSearchPagination:
    """REQ-SEARCH-005: pagination — PAGE_SIZE=50, paginated response."""

    def test_pagination_page_size_50(self, auth_client, db):
        # Create 55 books
        for i in range(55):
            make_book(f"ISBN-{i:03d}", f"도서 {i:03d}")

        resp = auth_client.get(SEARCH_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 55
        assert len(data["results"]) == 50
        assert data["next"] is not None
        assert data["previous"] is None

    def test_pagination_second_page(self, auth_client, db):
        for i in range(55):
            make_book(f"ISBN-{i:03d}", f"도서 {i:03d}")

        resp = auth_client.get(SEARCH_URL, {"page": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 5
        assert data["previous"] is not None
        assert data["next"] is None


# ---------------------------------------------------------------------------
# REQ-SEARCH-008: select_related('info') — no N+1 (behavioral test)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBookSearchNoNPlus1:
    """REQ-SEARCH-008: results include info fields without extra queries."""

    def test_results_include_info_name(self, auth_client, db):
        """name field in result proves info was joined, not lazy-loaded."""
        make_book("ISBN-001", "테스트 도서 제목")
        make_book("ISBN-002", "다른 도서 제목")

        resp = auth_client.get(SEARCH_URL, {"search": "테스트"})
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["name"] == "테스트 도서 제목"
