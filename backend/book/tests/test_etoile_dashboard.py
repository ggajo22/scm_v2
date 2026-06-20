"""
Tests for GET /api/book/etoile/dashboard/ — SPEC-ETOILE-DASHBOARD-001
REQ-ETD-001 through REQ-ETD-007
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from book.models import EtoileBookInven, Inven

User = get_user_model()

URL = "/api/book/etoile/dashboard/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="etoile_user", password="testpass123")


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


def make_etoile(sku: str, etoile_status=0) -> EtoileBookInven:
    inven = make_inven(sku, status=0)
    return EtoileBookInven.objects.create(inven=inven, status_of_shopify=etoile_status)


# REQ-ETD-002 / REQ-ETD-003: 인증 필수
def test_unauthenticated_returns_401(db):
    client = APIClient()
    res = client.get(URL)
    assert res.status_code == 401


# REQ-ETD-001: 엔드포인트 존재 및 정상 응답 구조
def test_authenticated_returns_200_with_structure(auth_client, db):
    res = auth_client.get(URL)
    assert res.status_code == 200
    assert "status_counts" in res.data
    assert "total" in res.data


# REQ-ETD-004: 상태별 건수 집계 정확성
def test_status_counts_aggregation(auth_client, db):
    make_etoile("ETL-001", etoile_status=0)
    make_etoile("ETL-002", etoile_status=0)
    make_etoile("ETL-003", etoile_status=80)

    res = auth_client.get(URL)
    assert res.status_code == 200

    counts = {row["status"]: row["count"] for row in res.data["status_counts"]}
    assert counts[0] == 2
    assert counts[80] == 1
    assert res.data["total"] == 3


# REQ-ETD-005: 레이블 매핑 — 정의된 상태
def test_known_status_labels(auth_client, db):
    make_etoile("ETL-011", etoile_status=-1)
    make_etoile("ETL-012", etoile_status=0)
    make_etoile("ETL-013", etoile_status=12)
    make_etoile("ETL-014", etoile_status=80)

    res = auth_client.get(URL)
    labels = {row["status"]: row["label"] for row in res.data["status_counts"]}
    assert labels[-1] == "gimssine 등록 대기"
    assert labels[0] == "리스팅 준비"
    assert labels[12] == "리스팅 제외 - 컨셉"
    assert labels[80] == "리스팅 완료"


# REQ-ETD-005: 미정의 상태 레이블
def test_unknown_status_label(auth_client, db):
    make_etoile("ETL-021", etoile_status=99)

    res = auth_client.get(URL)
    row = next(r for r in res.data["status_counts"] if r["status"] == 99)
    assert row["label"] == "정의되지 않은 상태"


# REQ-ETD-005: null status → "상태 없음"
def test_null_status_label(auth_client, db):
    inven = make_inven("ETL-031", status=0)
    EtoileBookInven.objects.create(inven=inven, status_of_shopify=None)

    res = auth_client.get(URL)
    null_rows = [r for r in res.data["status_counts"] if r["status"] is None]
    assert len(null_rows) == 1
    assert null_rows[0]["label"] == "상태 없음"
    assert null_rows[0]["count"] == 1


# REQ-ETD-004: total = 전체 합산
def test_total_equals_sum_of_counts(auth_client, db):
    make_etoile("ETL-041", etoile_status=0)
    make_etoile("ETL-042", etoile_status=80)
    inven = make_inven("ETL-043", status=0)
    EtoileBookInven.objects.create(inven=inven, status_of_shopify=None)

    res = auth_client.get(URL)
    expected_total = sum(r["count"] for r in res.data["status_counts"])
    assert res.data["total"] == expected_total == 3


# REQ-ETD-004: null status는 정렬 시 맨 마지막
def test_null_status_sorted_last(auth_client, db):
    inven_null = make_inven("ETL-051", status=0)
    EtoileBookInven.objects.create(inven=inven_null, status_of_shopify=None)
    make_etoile("ETL-052", etoile_status=0)
    make_etoile("ETL-053", etoile_status=80)

    res = auth_client.get(URL)
    statuses = [r["status"] for r in res.data["status_counts"]]
    assert statuses[-1] is None


# REQ-ETD-006: 데이터 없을 때 빈 배열 + total=0
def test_empty_etoile_table(auth_client, db):
    res = auth_client.get(URL)
    assert res.status_code == 200
    assert res.data["status_counts"] == []
    assert res.data["total"] == 0
