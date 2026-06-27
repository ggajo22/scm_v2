import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from order.models import WarehouseStock


@pytest.fixture
def client(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(username="testuser", password="pass")
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def stock_korea(db):
    return WarehouseStock.objects.create(isbn="9788901234567", location="korea", quantity=10)


@pytest.fixture
def stock_ca(db):
    return WarehouseStock.objects.create(isbn="9788901234567", location="ca", quantity=5)


class TestWarehouseStockList:
    def test_returns_pivoted_rows(self, client, stock_korea, stock_ca):
        res = client.get("/api/warehouse/stock/")
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == 1
        row = data["results"][0]
        assert row["isbn"] == "9788901234567"
        assert row["korea"] == 10
        assert row["ca"] == 5
        assert row["nj"] is None
        assert row["korea_pk"] == stock_korea.pk
        assert row["ca_pk"] == stock_ca.pk
        assert row["nj_pk"] is None

    def test_empty(self, client, db):
        res = client.get("/api/warehouse/stock/")
        assert res.status_code == 200
        assert res.json()["count"] == 0


class TestWarehouseStockUpsert:
    def test_create_new(self, client, db):
        res = client.post(
            "/api/warehouse/stock/upsert/",
            {"isbn": "9788901111111", "location": "nj", "quantity": 7},
            format="json",
        )
        assert res.status_code == 201
        assert WarehouseStock.objects.filter(isbn="9788901111111", location="nj").exists()

    def test_update_existing(self, client, stock_korea):
        res = client.post(
            "/api/warehouse/stock/upsert/",
            {"isbn": stock_korea.isbn, "location": "korea", "quantity": 99},
            format="json",
        )
        assert res.status_code == 200
        stock_korea.refresh_from_db()
        assert stock_korea.quantity == 99

    def test_invalid_location(self, client, db):
        res = client.post(
            "/api/warehouse/stock/upsert/",
            {"isbn": "9788901111111", "location": "invalid", "quantity": 1},
            format="json",
        )
        assert res.status_code == 400

    def test_missing_isbn(self, client, db):
        res = client.post(
            "/api/warehouse/stock/upsert/",
            {"location": "korea", "quantity": 1},
            format="json",
        )
        assert res.status_code == 400


class TestWarehouseStockBulk:
    def test_bulk_upsert(self, client, db):
        items = [
            {"isbn": "111", "location": "korea", "quantity": 10},
            {"isbn": "111", "location": "ca", "quantity": 5},
            {"isbn": "222", "location": "nj", "quantity": 3},
        ]
        res = client.post("/api/warehouse/stock/bulk/", items, format="json")
        assert res.status_code == 200
        assert res.json()["upserted_count"] == 3
        assert WarehouseStock.objects.count() == 3

    def test_skips_invalid_entries(self, client, db):
        items = [
            {"isbn": "111", "location": "bad_loc", "quantity": 10},
            {"isbn": "", "location": "korea", "quantity": 5},
            {"isbn": "222", "location": "korea", "quantity": 7},
        ]
        res = client.post("/api/warehouse/stock/bulk/", items, format="json")
        assert res.status_code == 200
        assert res.json()["upserted_count"] == 1

    def test_not_a_list(self, client, db):
        res = client.post("/api/warehouse/stock/bulk/", {"isbn": "111"}, format="json")
        assert res.status_code == 400


class TestWarehouseStockDelete:
    def test_delete(self, client, stock_korea):
        res = client.delete(f"/api/warehouse/stock/{stock_korea.pk}/")
        assert res.status_code == 204
        assert not WarehouseStock.objects.filter(pk=stock_korea.pk).exists()

    def test_not_found(self, client, db):
        res = client.delete("/api/warehouse/stock/99999/")
        assert res.status_code == 404
