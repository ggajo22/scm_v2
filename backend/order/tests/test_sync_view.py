from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from order.models import Order

User = get_user_model()
URL = "/api/orders/sync/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="sync_user", password="testpass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.mark.django_db
def test_sync_requires_auth():
    client = APIClient()
    res = client.post(URL)
    assert res.status_code == 401


@pytest.mark.django_db
def test_sync_success_both_stores(auth_client):
    success_result = {"synced_count": 3, "updated_count": 1, "error": None}
    with patch("order.views.sync_store", return_value=success_result):
        res = auth_client.post(URL)
    assert res.status_code == 200
    assert res.data["status"] == "completed"
    assert res.data["total_synced"] == 6
    assert res.data["total_updated"] == 2
    assert res.data["stores"]["booksen"]["error"] is None
    assert res.data["stores"]["etoile"]["error"] is None


@pytest.mark.django_db
def test_sync_partial_failure(auth_client):
    def side_effect(store_type):
        if store_type == "booksen":
            raise Exception("Connection refused")
        return {"synced_count": 2, "updated_count": 0, "error": None}

    with patch("order.views.sync_store", side_effect=side_effect):
        res = auth_client.post(URL)

    assert res.status_code == 200
    assert res.data["status"] == "partial"
    assert res.data["stores"]["booksen"]["error"] is not None
    assert res.data["stores"]["etoile"]["error"] is None
    assert res.data["total_synced"] == 2


@pytest.mark.django_db
def test_sync_upserts_existing_order(auth_client):
    Order.objects.create(shopify_order_id=5001, store_type="booksen")

    def side_effect(store_type):
        if store_type == "booksen":
            return {"synced_count": 0, "updated_count": 1, "error": None}
        return {"synced_count": 0, "updated_count": 0, "error": None}

    with patch("order.views.sync_store", side_effect=side_effect):
        res = auth_client.post(URL)

    assert res.status_code == 200
    assert res.data["total_updated"] == 1
    assert res.data["total_synced"] == 0
