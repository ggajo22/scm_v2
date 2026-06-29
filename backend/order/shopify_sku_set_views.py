"""
Shopify SKU Set/Bundle Mapping views for SPEC-SHOPIFY-SKU-SET-001.

Endpoints:
  GET    /api/shopify-sku-sets/              — List all bundles with member ISBNs and book titles
  POST   /api/shopify-sku-sets/              — Create a new bundle mapping
  GET    /api/shopify-sku-sets/{bundle_sku}/ — Get single bundle detail
  PUT    /api/shopify-sku-sets/{bundle_sku}/ — Replace bundle members atomically
  DELETE /api/shopify-sku-sets/{bundle_sku}/ — Delete entire bundle

# @MX:ANCHOR: [AUTO] ShopifySkuSetListCreateView — public API for SKU bundle CRUD
# @MX:REASON: Fan-in >= 3 expected: frontend settings page, tests, future admin use
"""

from collections import defaultdict

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from book.models import Inven

from .models import ShopifySkuSetMapping


def _build_title_map(isbn_list: list[str]) -> dict[str, str | None]:
    """Batch-query book titles for a list of ISBNs. Returns {isbn: title_or_None}."""
    if not isbn_list:
        return {}
    rows = (
        Inven.objects.filter(inven_SKU__in=isbn_list)
        .select_related("info")
        .values("inven_SKU", "info__name")
    )
    return {row["inven_SKU"]: row["info__name"] for row in rows}


def _group_mappings(mappings, title_map: dict) -> list[dict]:
    """Group ShopifySkuSetMapping queryset by bundle_sku for API response."""
    grouped: dict[str, list] = defaultdict(list)
    for m in mappings:
        grouped[m.bundle_sku].append(
            {
                "isbn": m.member_isbn,
                "sort_order": m.sort_order,
                "book_title": title_map.get(m.member_isbn),
            }
        )
    return [{"bundle_sku": sku, "member_isbns": items} for sku, items in grouped.items()]


class ShopifySkuSetListCreateView(APIView):
    """
    GET  /api/shopify-sku-sets/ — Returns all bundles grouped by bundle_sku.
    POST /api/shopify-sku-sets/ — Creates a new bundle mapping.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        mappings = list(ShopifySkuSetMapping.objects.all())
        all_isbns = [m.member_isbn for m in mappings]
        title_map = _build_title_map(all_isbns)
        data = _group_mappings(mappings, title_map)
        return Response(data)

    def post(self, request) -> Response:
        bundle_sku = request.data.get("bundle_sku", "").strip()
        member_isbns = request.data.get("member_isbns")

        if not bundle_sku:
            return Response({"detail": "bundle_sku is required and must not be empty."}, status=status.HTTP_400_BAD_REQUEST)
        if not member_isbns or not isinstance(member_isbns, list) or len(member_isbns) == 0:
            return Response({"detail": "member_isbns must be a non-empty list."}, status=status.HTTP_400_BAD_REQUEST)

        objs = [
            ShopifySkuSetMapping(bundle_sku=bundle_sku, member_isbn=isbn, sort_order=i)
            for i, isbn in enumerate(member_isbns)
        ]
        ShopifySkuSetMapping.objects.bulk_create(objs)

        created = list(ShopifySkuSetMapping.objects.filter(bundle_sku=bundle_sku))
        title_map = _build_title_map([m.member_isbn for m in created])
        response_data = _group_mappings(created, title_map)
        return Response(response_data[0] if response_data else {}, status=status.HTTP_201_CREATED)


class ShopifySkuSetDetailView(APIView):
    """
    GET    /api/shopify-sku-sets/{bundle_sku}/ — Get single bundle detail.
    PUT    /api/shopify-sku-sets/{bundle_sku}/ — Replace bundle members atomically.
    DELETE /api/shopify-sku-sets/{bundle_sku}/ — Delete entire bundle.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_or_404(self, bundle_sku: str) -> list:
        """Return mappings for bundle_sku or raise 404."""
        mappings = list(ShopifySkuSetMapping.objects.filter(bundle_sku=bundle_sku))
        if not mappings:
            return None
        return mappings

    def get(self, request, bundle_sku: str) -> Response:
        mappings = self._get_or_404(bundle_sku)
        if mappings is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        title_map = _build_title_map([m.member_isbn for m in mappings])
        data = _group_mappings(mappings, title_map)
        return Response(data[0])

    def put(self, request, bundle_sku: str) -> Response:
        if not ShopifySkuSetMapping.objects.filter(bundle_sku=bundle_sku).exists():
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        member_isbns = request.data.get("member_isbns")
        if not member_isbns or not isinstance(member_isbns, list):
            return Response({"detail": "member_isbns must be a non-empty list."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            ShopifySkuSetMapping.objects.filter(bundle_sku=bundle_sku).delete()
            objs = [
                ShopifySkuSetMapping(bundle_sku=bundle_sku, member_isbn=isbn, sort_order=i)
                for i, isbn in enumerate(member_isbns)
            ]
            ShopifySkuSetMapping.objects.bulk_create(objs)

        updated = list(ShopifySkuSetMapping.objects.filter(bundle_sku=bundle_sku))
        title_map = _build_title_map([m.member_isbn for m in updated])
        data = _group_mappings(updated, title_map)
        return Response(data[0])

    def delete(self, request, bundle_sku: str) -> Response:
        qs = ShopifySkuSetMapping.objects.filter(bundle_sku=bundle_sku)
        if not qs.exists():
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        qs.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
