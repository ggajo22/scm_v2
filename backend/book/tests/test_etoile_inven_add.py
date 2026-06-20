"""
Tests for POST /api/book/etoile-inven-skus/ — SPEC-ETOILE-INVEN-ADD-001
REQ-EIA-001 through REQ-EIA-015
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from book.models import EtoileBookInven, Inven

User = get_user_model()

URL = "/api/book/etoile-inven-skus/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="etoile_add_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


def make_inven(sku: str, status: int = 0) -> Inven:
    return Inven.objects.create(
        inven_SKU=sku, vendor="북센", store="책방",
        is_prepared=0, status_of_shopify=status, is_use=1,
    )


def make_etoile(inven: Inven, etoile_status: int = 0) -> EtoileBookInven:
    return EtoileBookInven.objects.create(inven=inven, status_of_shopify=etoile_status)


# REQ-EIA-002 / REQ-EIA-003: JWT 인증 필수
def test_unauthenticated_returns_401(db):
    """인증 없이 요청 시 HTTP 401 반환."""
    client = APIClient()
    res = client.post(URL, {"skus": ["9791234567890"]}, format="json")
    assert res.status_code == 401


# REQ-EIA-004: skus 필드 누락 시 400
def test_missing_skus_field_returns_400(auth_client, db):
    """skus 필드가 없으면 HTTP 400 반환."""
    res = auth_client.post(URL, {}, format="json")
    assert res.status_code == 400


# REQ-EIA-004: skus 빈 배열 시 400
def test_empty_skus_array_returns_400(auth_client, db):
    """skus가 빈 배열이면 HTTP 400 반환."""
    res = auth_client.post(URL, {"skus": []}, format="json")
    assert res.status_code == 400


# REQ-EIA-006 / REQ-EIA-014: 모든 SKU가 이미 EtoileBookInven에 존재
def test_all_skus_already_in_etoile(auth_client, db):
    """모든 SKU가 이미 EtoileBookInven에 존재하면 etoile_existing_skus에 포함, 신규 레코드 없음."""
    inven1 = make_inven("ETL-EXIST-001")
    inven2 = make_inven("ETL-EXIST-002")
    make_etoile(inven1)
    make_etoile(inven2)

    res = auth_client.post(URL, {"skus": ["ETL-EXIST-001", "ETL-EXIST-002"]}, format="json")
    assert res.status_code == 200

    data = res.data
    assert set(data["etoile_existing_skus"]) == {"ETL-EXIST-001", "ETL-EXIST-002"}
    assert data["etoile_existing_count"] == 2
    assert data["book_created_skus"] == []
    assert data["etoile_created_new_book_skus"] == []
    assert data["etoile_created_existing_book_skus"] == []
    assert data["book_created_count"] == 0
    assert data["etoile_created_new_book_count"] == 0
    assert data["etoile_created_existing_book_count"] == 0

    # DB에 추가 레코드 없음
    assert EtoileBookInven.objects.count() == 2


# REQ-EIA-007 / REQ-EIA-008 / REQ-EIA-009: 모든 SKU가 Inven에도 Etoile에도 없는 경우
def test_all_skus_missing_from_inven_and_etoile(auth_client, db):
    """모든 SKU가 본관에도 Etoile에도 없으면 Inven + EtoileBookInven 신규 생성, status_of_shopify=-1."""
    skus = ["NEW-001", "NEW-002"]
    res = auth_client.post(URL, {"skus": skus}, format="json")
    assert res.status_code == 200

    data = res.data
    assert set(data["book_created_skus"]) == set(skus)
    assert set(data["etoile_created_new_book_skus"]) == set(skus)
    assert data["etoile_created_existing_book_skus"] == []
    assert data["etoile_existing_skus"] == []
    assert data["book_created_count"] == 2
    assert data["etoile_created_new_book_count"] == 2
    assert data["etoile_created_existing_book_count"] == 0
    assert data["etoile_existing_count"] == 0

    # Inven 레코드 생성 확인
    assert Inven.objects.filter(inven_SKU__in=skus).count() == 2
    inven_new = Inven.objects.get(inven_SKU="NEW-001")
    assert inven_new.vendor == "북센"
    assert inven_new.store == "책방"
    assert inven_new.is_prepared == 0
    assert inven_new.is_use == 1

    # EtoileBookInven status_of_shopify=-1 확인
    etoile_records = EtoileBookInven.objects.filter(inven__inven_SKU__in=skus)
    assert etoile_records.count() == 2
    for record in etoile_records:
        assert record.status_of_shopify == -1


# REQ-EIA-007 / REQ-EIA-010: 모든 SKU가 본관에 있고 Etoile에 없는 경우
def test_all_skus_in_inven_but_not_in_etoile(auth_client, db):
    """모든 SKU가 본관에 있고 Etoile에 없으면 EtoileBookInven만 생성, status_of_shopify=0."""
    make_inven("INVEN-ONLY-001")
    make_inven("INVEN-ONLY-002")

    res = auth_client.post(URL, {"skus": ["INVEN-ONLY-001", "INVEN-ONLY-002"]}, format="json")
    assert res.status_code == 200

    data = res.data
    assert data["book_created_skus"] == []
    assert data["etoile_created_new_book_skus"] == []
    assert set(data["etoile_created_existing_book_skus"]) == {"INVEN-ONLY-001", "INVEN-ONLY-002"}
    assert data["etoile_existing_skus"] == []
    assert data["book_created_count"] == 0
    assert data["etoile_created_new_book_count"] == 0
    assert data["etoile_created_existing_book_count"] == 2
    assert data["etoile_existing_count"] == 0

    # EtoileBookInven status_of_shopify=0 확인
    etoile_records = EtoileBookInven.objects.filter(
        inven__inven_SKU__in=["INVEN-ONLY-001", "INVEN-ONLY-002"]
    )
    assert etoile_records.count() == 2
    for record in etoile_records:
        assert record.status_of_shopify == 0

    # Inven 레코드는 신규 생성 없음 (기존 2개만)
    assert Inven.objects.count() == 2


# REQ-EIA-006 ~ REQ-EIA-010: 혼합 케이스 (3가지 상황 동시)
def test_mixed_case_all_three_scenarios(auth_client, db):
    """혼합 케이스: Etoile 기존 / 본관만 있음 / 둘 다 없음이 동시에 존재."""
    # SKU_A: 이미 EtoileBookInven에 존재
    inven_a = make_inven("MIX-A")
    make_etoile(inven_a)

    # SKU_B: 본관에 있고 Etoile에 없음
    make_inven("MIX-B")

    # SKU_C: 둘 다 없음
    skus = ["MIX-A", "MIX-B", "MIX-C"]
    res = auth_client.post(URL, {"skus": skus}, format="json")
    assert res.status_code == 200

    data = res.data
    assert data["etoile_existing_skus"] == ["MIX-A"]
    assert data["etoile_existing_count"] == 1

    assert data["etoile_created_existing_book_skus"] == ["MIX-B"]
    assert data["etoile_created_existing_book_count"] == 1

    assert data["book_created_skus"] == ["MIX-C"]
    assert data["etoile_created_new_book_skus"] == ["MIX-C"]
    assert data["book_created_count"] == 1
    assert data["etoile_created_new_book_count"] == 1

    # EtoileBookInven 레코드 확인
    assert EtoileBookInven.objects.filter(inven__inven_SKU="MIX-A").exists()  # 기존
    etoile_b = EtoileBookInven.objects.get(inven__inven_SKU="MIX-B")
    assert etoile_b.status_of_shopify == 0
    etoile_c = EtoileBookInven.objects.get(inven__inven_SKU="MIX-C")
    assert etoile_c.status_of_shopify == -1


# REQ-EIA-005: 중복 SKU 입력 → 중복 제거 후 1회만 처리
def test_duplicate_skus_are_deduplicated(auth_client, db):
    """중복 SKU 입력 시 중복 제거 후 1회만 처리."""
    skus = ["DUP-001", "DUP-001", "DUP-001"]
    res = auth_client.post(URL, {"skus": skus}, format="json")
    assert res.status_code == 200

    data = res.data
    assert data["book_created_count"] == 1
    assert data["etoile_created_new_book_count"] == 1
    assert Inven.objects.filter(inven_SKU="DUP-001").count() == 1
    assert EtoileBookInven.objects.filter(inven__inven_SKU="DUP-001").count() == 1


# REQ-EIA-005: 공백 포함 SKU → strip 후 정상 처리
def test_skus_with_whitespace_are_stripped(auth_client, db):
    """공백 포함 SKU는 strip 후 정상 처리."""
    skus = ["  SPACE-001  ", "  SPACE-002"]
    res = auth_client.post(URL, {"skus": skus}, format="json")
    assert res.status_code == 200

    data = res.data
    assert data["book_created_count"] == 2
    assert Inven.objects.filter(inven_SKU="SPACE-001").exists()
    assert Inven.objects.filter(inven_SKU="SPACE-002").exists()


# REQ-EIA-011 / REQ-EIA-012: DB 오류 → 트랜잭션 롤백, HTTP 500
def test_db_error_causes_rollback_and_500(auth_client, db, monkeypatch):
    """DB 오류 발생 시 트랜잭션 롤백 및 HTTP 500 반환."""
    from django.db import DatabaseError
    from book import views as book_views

    original_bulk_create = Inven.objects.bulk_create

    def failing_bulk_create(objs, **kwargs):
        raise DatabaseError("Simulated DB error")

    monkeypatch.setattr(
        "book.views.Inven.objects.bulk_create",
        failing_bulk_create,
    )

    skus = ["FAIL-001", "FAIL-002"]
    res = auth_client.post(URL, {"skus": skus}, format="json")
    assert res.status_code == 500

    # 롤백 확인 — DB에 레코드 없음
    assert Inven.objects.filter(inven_SKU__in=skus).count() == 0
    assert EtoileBookInven.objects.filter(inven__inven_SKU__in=skus).count() == 0
