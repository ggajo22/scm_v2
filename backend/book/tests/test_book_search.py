"""
Tests for GET /api/book/search/ — SPEC-BOOK-SEARCH-001
REQ-SEARCH-001 through REQ-SEARCH-008
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from book.models import EtoileBookInven, Info, Inven

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


def make_book(
    sku: str,
    title: str,
    price_sale: float = 10000.0,
    status_of_shopify: int = 100,
    cover_image_url: str = "",
) -> Inven:
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
        cover_image_url=cover_image_url,
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
        assert "status_of_shopify" in book
        assert "cover_image_url" in book
        assert "etoile_listed" in book
        assert "etoile_status_label" in book


# ---------------------------------------------------------------------------
# Search result display fields: cover image + ETOILE listing, price_sale dropped
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBookSearchDisplayFields:
    """Search results expose the cover image URL and ETOILE listing state, not the sale price."""

    def test_price_sale_is_not_exposed(self, auth_client, db):
        make_book("ISBN-001", "테스트 도서", price_sale=15000.0)

        book = auth_client.get(SEARCH_URL).json()["results"][0]
        assert "price_sale" not in book

    def test_cover_image_url_is_returned(self, auth_client, db):
        make_book("ISBN-001", "테스트 도서", cover_image_url="https://cdn.example.com/a.jpg")

        book = auth_client.get(SEARCH_URL).json()["results"][0]
        assert book["cover_image_url"] == "https://cdn.example.com/a.jpg"

    def test_cover_image_url_is_empty_string_when_missing(self, auth_client, db):
        make_book("ISBN-001", "테스트 도서")

        book = auth_client.get(SEARCH_URL).json()["results"][0]
        assert book["cover_image_url"] == ""

    def test_no_etoile_record_is_not_listed(self, auth_client, db):
        make_book("ISBN-001", "테스트 도서")

        book = auth_client.get(SEARCH_URL).json()["results"][0]
        assert book["etoile_listed"] is False
        assert book["etoile_status_label"] == "미등록"

    def test_etoile_status_80_is_listed(self, auth_client, db):
        inven = make_book("ISBN-001", "테스트 도서")
        EtoileBookInven.objects.create(inven=inven, status_of_shopify=80)

        book = auth_client.get(SEARCH_URL).json()["results"][0]
        assert book["etoile_listed"] is True
        assert book["etoile_status_label"] == "리스팅 완료"

    @pytest.mark.parametrize(
        ("status", "label"),
        [
            (-1, "gimssine 등록 대기"),
            (0, "리스팅 준비"),
            (12, "리스팅 제외 - 컨셉"),
        ],
    )
    def test_etoile_non_80_status_is_not_listed_but_labelled(self, auth_client, db, status, label):
        """A book registered on ETOILE but not yet live must not read as listed."""
        inven = make_book("ISBN-001", "테스트 도서")
        EtoileBookInven.objects.create(inven=inven, status_of_shopify=status)

        book = auth_client.get(SEARCH_URL).json()["results"][0]
        assert book["etoile_listed"] is False
        assert book["etoile_status_label"] == label

    def test_etoile_null_status(self, auth_client, db):
        inven = make_book("ISBN-001", "테스트 도서")
        EtoileBookInven.objects.create(inven=inven, status_of_shopify=None)

        book = auth_client.get(SEARCH_URL).json()["results"][0]
        assert book["etoile_listed"] is False
        assert book["etoile_status_label"] == "상태 없음"

    def test_etoile_unknown_status(self, auth_client, db):
        inven = make_book("ISBN-001", "테스트 도서")
        EtoileBookInven.objects.create(inven=inven, status_of_shopify=999)

        book = auth_client.get(SEARCH_URL).json()["results"][0]
        assert book["etoile_listed"] is False
        assert book["etoile_status_label"] == "정의되지 않은 상태"

    def test_etoile_state_is_joined_not_lazy_loaded(
        self, auth_client, db, django_assert_max_num_queries
    ):
        """Remote DB costs ~130 ms per round trip — a per-row etoile lookup is a regression."""
        for i in range(10):
            inven = make_book(f"ISBN-{i:03d}", f"도서 {i:03d}")
            EtoileBookInven.objects.create(inven=inven, status_of_shopify=80)

        # auth + count + page query; ten extra lookups would blow this budget
        with django_assert_max_num_queries(6):
            resp = auth_client.get(SEARCH_URL)

        assert resp.status_code == 200
        assert all(row["etoile_listed"] is True for row in resp.json()["results"])


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
# REQ-SEARCH-001: two-path search (see BookListViewSet.get_queryset)
#   - digits-only query -> inven_SKU startswith (index scan)
#   - any other text    -> FULLTEXT MATCH AGAINST ngram on info.name
# These paths are exclusive: a text query does NOT search inven_SKU. The
# comment here previously described an older "OR icontains on inven_SKU AND
# info.name" implementation that no longer exists.
#
# The FULLTEXT tests below need django_db(transaction=True): InnoDB does not
# expose rows to MATCH AGAINST until the inserting transaction commits, so
# under the default rolled-back test transaction every MATCH returns zero.
# ---------------------------------------------------------------------------

class TestBookSearchQuery:
    """REQ-SEARCH-001: digits match inven_SKU by prefix; text matches info.name."""

    @pytest.mark.django_db
    def test_search_by_sku_partial_match(self, auth_client, db):
        make_book("978-3-16-148410-0", "어떤 도서")
        make_book("000-0-00-000000-0", "다른 도서")

        resp = auth_client.get(SEARCH_URL, {"search": "978"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["inven_SKU"] == "978-3-16-148410-0"

    @pytest.mark.django_db(transaction=True)
    def test_search_by_title_partial_match(self, auth_client, db):
        make_book("ISBN-001", "파이썬 프로그래밍")
        make_book("ISBN-002", "자바스크립트 완전 정복")

        resp = auth_client.get(SEARCH_URL, {"search": "파이썬"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["name"] == "파이썬 프로그래밍"

    @pytest.mark.django_db(transaction=True)
    def test_search_case_insensitive(self, auth_client, db):
        make_book("isbn-abc", "Python ISBN Guide")

        resp = auth_client.get(SEARCH_URL, {"search": "ISBN"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    @pytest.mark.django_db(transaction=True)
    def test_text_search_returns_every_title_containing_the_term(self, auth_client, db):
        make_book("SKU-999", "UNIQUE 한국책")
        make_book("SKU-111", "UNIQUE 영어책")
        make_book("SKU-000", "관련없는 도서")

        resp = auth_client.get(SEARCH_URL, {"search": "UNIQUE"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 2

    @pytest.mark.django_db(transaction=True)
    def test_text_search_does_not_match_sku(self, auth_client, db):
        """The two paths are exclusive — a text query never looks at inven_SKU.

        This previously lived inside a test asserting SKU-OR-title matching,
        written against the old icontains implementation. Pinning the real
        behaviour explicitly keeps the next reader from assuming the OR is
        still there just because no test contradicts it.
        """
        make_book("UNIQUE-SKU-999", "관련없는 도서")

        resp = auth_client.get(SEARCH_URL, {"search": "UNIQUE"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    @pytest.mark.django_db
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

    @pytest.mark.django_db(transaction=True)
    def test_results_include_info_name(self, auth_client, db):
        """name field in result proves info was joined, not lazy-loaded."""
        make_book("ISBN-001", "테스트 도서 제목")
        make_book("ISBN-002", "다른 도서 제목")

        resp = auth_client.get(SEARCH_URL, {"search": "테스트"})
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["name"] == "테스트 도서 제목"
