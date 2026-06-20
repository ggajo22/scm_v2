import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from book import shopify_client
from book.constants import ERROR_STATUSES, ETOILE_STATUS_LABELS, LISTED_STATUSES, STATUS_LABELS, WAITING_STATUSES
from book.models import (
    BookNote,
    Booksen_category,
    EtoileBookInfo,
    EtoileBookInven,
    EtoileShopifyProduct,
    Info,
    Inven,
    Shopify_product,
)
from book.serializers import (
    BookDetailSerializer,
    BookNoteSerializer,
    DashboardMetricsSerializer,
    EtoileBookInfoSerializer,
    EtoileBookInvenSerializer,
    EtoileShopifyProductSerializer,
    FastListingSkuBulkSerializer,
    InfoSerializer,
    InfoUpdateSerializer,
    InvenSkuBulkAddSerializer,
    ShopifyProductSerializer,
)

_FT_SPECIAL = re.compile(r'[+\-><()~*"@]')


def _sanitize_ft(q: str) -> str:
    return _FT_SPECIAL.sub(' ', q).strip()


def _build_ft_query(q: str) -> str:
    """Require ALL whitespace-separated terms (BOOLEAN MODE AND semantics)."""
    sanitized = _sanitize_ft(q)
    if not sanitized:
        return ''
    return ' '.join(f'+{term}' for term in sanitized.split())


# @MX:ANCHOR: [AUTO] BookListViewSet.list — search endpoint for book inventory
# @MX:REASON: REQ-SEARCH-001 through REQ-SEARCH-008 all served by this single list action
class BookListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/book/search/?search=<query>
    Two-path search:
      - digits only → inven_SKU startswith (index scan, fast)
      - text        → FULLTEXT MATCH AGAINST ngram on info.name (Korean-aware)
    REQ-SEARCH-001 to REQ-SEARCH-008
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = BookDetailSerializer

    def get_queryset(self):
        # REQ-SEARCH-008: select_related avoids N+1 on info fields
        qs = Inven.objects.select_related("info")
        search = self.request.query_params.get("search", "").strip()
        if not search:
            return qs.order_by("id")

        # ISBN path: digits only → startswith uses the inven_SKU index
        if search.isdigit():
            return qs.filter(inven_SKU__startswith=search).order_by("id")

        # Text path: annotate relevance score so DRF paginator gets the full result set
        # (avoids the 50-item LIMIT that broke pagination)
        # _build_ft_query prefixes each token with + so BOOLEAN MODE requires ALL terms
        safe_q = _build_ft_query(search)
        if not safe_q:
            return qs.none()

        # filter(info__isnull=False) forces the book_info JOIN into COUNT queries too;
        # without it, select_related JOIN is stripped on .count() and MATCH fails.
        return (
            qs
            .filter(info__isnull=False)
            .extra(
                select={"relevance": "MATCH(`book_info`.`name`) AGAINST (%s IN BOOLEAN MODE)"},
                select_params=[safe_q],
                where=["MATCH(`book_info`.`name`) AGAINST (%s IN BOOLEAN MODE) > 0"],
                params=[safe_q],
            )
            .order_by("-relevance")
        )


class DashboardMetricsView(APIView):
    # @MX:ANCHOR: [AUTO] DashboardMetricsView.get — single entry point for all 8 dashboard metrics
    # @MX:REASON: REQ-BD-001 through REQ-BD-011 all flow through this method;
    # changes affect all metrics
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        # REQ-BD-003: status_counts — aggregate Inven by status_of_shopify
        raw_counts = (
            Inven.objects.values("status_of_shopify")
            .annotate(count=Count("id"))
            .order_by("status_of_shopify")
        )
        status_counts = [
            {
                "status": row["status_of_shopify"],
                "label": STATUS_LABELS.get(row["status_of_shopify"], "Unknown"),
                "count": row["count"],
            }
            for row in raw_counts
        ]

        # REQ-BD-004: shopify_created_24h — Shopify products created strictly within last 24h
        shopify_created_24h = Shopify_product.objects.filter(
            created_at__gt=now - timedelta(hours=24)
        ).count()

        # REQ-BD-005/006: error metrics — derived from status_counts (no extra query)
        error_rows = [row for row in status_counts if row["status"] in ERROR_STATUSES]
        error_total = sum(row["count"] for row in error_rows)

        # REQ-BD-007: waiting_total
        waiting_total = Inven.objects.filter(
            status_of_shopify__in=WAITING_STATUSES
        ).count()

        # REQ-BD-008: unresolved GENERAL notes
        unresolved_note_count = BookNote.objects.filter(
            note_type="GENERAL", is_resolved=False
        ).count()

        # REQ-BD-009: listed items with sale price = 0
        sale_zero_count = Info.objects.filter(
            price_sale=0,
            inven__status_of_shopify__in=LISTED_STATUSES,
        ).count()

        # REQ-BD-010: listed items with both price and kyobo_supply_price = 0
        cost_zero_count = Info.objects.filter(
            price=0,
            kyobo_supply_price=0,
            inven__status_of_shopify__in=LISTED_STATUSES,
        ).count()

        payload = {
            "status_counts": status_counts,
            "shopify_created_24h": shopify_created_24h,
            "error_total": error_total,
            "error_rows": error_rows,
            "waiting_total": waiting_total,
            "unresolved_note_count": unresolved_note_count,
            "sale_zero_count": sale_zero_count,
            "cost_zero_count": cost_zero_count,
        }

        serializer = DashboardMetricsSerializer(payload)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Booksen category cascade API
# ---------------------------------------------------------------------------

class BooksenCategoryListView(APIView):
    """
    GET /api/book/booksen-categories/?top_code=<int>
    Returns Booksen_category entries with the given top_category_code.
    top_code=0 returns top-level categories (rank 2 / 대).
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            top_code = int(request.query_params.get("top_code", 0))
        except (TypeError, ValueError):
            return Response({"detail": "top_code must be an integer."}, status=400)

        qs = Booksen_category.objects.filter(top_category_code=top_code)
        if top_code == 0:
            qs = qs.filter(category_rank=1)
        categories = qs.order_by("category_code").values(
            "category_code", "category_name", "category_rank"
        )
        return Response(list(categories))


# ---------------------------------------------------------------------------
# SPEC-BOOK-EDIT-001 views
# ---------------------------------------------------------------------------

class BookRetrieveView(APIView):
    """
    GET /api/book/{id}/
    Returns full book detail: inven, info, notes, shopify_products, etoile.
    REQ-BKEDIT-001 through REQ-BKEDIT-006
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            inven = Inven.objects.select_related("info").get(pk=pk)
        except Inven.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        # Notes: all unresolved + 10 most recent resolved (REQ-BKEDIT-005)
        unresolved_notes = BookNote.objects.filter(inven=inven, is_resolved=False)
        resolved_notes = (
            BookNote.objects.filter(inven=inven, is_resolved=True).order_by("-resolved_at")[:10]
        )

        # Combine and serialize in chronological order
        notes_qs = list(unresolved_notes) + list(resolved_notes)

        # Shopify products
        shopify_products = Shopify_product.objects.filter(inven=inven)

        # Etoile data — null if no EtoileBookInven
        etoile_data = None
        try:
            etoile_inven = inven.etoile_inven
            etoile_inven_data = EtoileBookInvenSerializer(etoile_inven).data

            etoile_shopify_products = etoile_inven.shopify_product.all()
            try:
                etoile_info = etoile_inven.info
                etoile_info_data = EtoileBookInfoSerializer(etoile_info).data
            except EtoileBookInfo.DoesNotExist:
                etoile_info_data = None

            etoile_data = {
                "inven": dict(etoile_inven_data),
                "info": etoile_info_data,
                "shopify_products": EtoileShopifyProductSerializer(
                    etoile_shopify_products, many=True
                ).data,
            }
        except EtoileBookInven.DoesNotExist:
            etoile_data = None

        payload = {
            "id": inven.id,
            "inven_SKU": inven.inven_SKU,
            "vendor": inven.vendor,
            "store": inven.store,
            "is_prepared": inven.is_prepared,
            "status_of_shopify": inven.status_of_shopify,
            "is_use": inven.is_use,
            "info": InfoSerializer(inven.info).data if hasattr(inven, "info") else None,
            "notes": BookNoteSerializer(notes_qs, many=True).data,
            "shopify_products": ShopifyProductSerializer(shopify_products, many=True).data,
            "etoile": etoile_data,
        }
        return Response(payload)


class BookInfoUpdateView(APIView):
    """
    PATCH /api/book/{id}/info/
    Partial update of Info model fields.
    REQ-BKEDIT-007 through REQ-BKEDIT-009
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            inven = Inven.objects.select_related("info").get(pk=pk)
        except Inven.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        serializer = InfoUpdateSerializer(inven.info, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        serializer.save()
        inven.status_of_shopify = 15
        inven.save(update_fields=["status_of_shopify"])
        return Response(InfoSerializer(inven.info).data)


class BookNoteCreateView(APIView):
    """
    POST /api/book/{id}/notes/
    Creates a BookNote for the given Inven.
    REQ-BKEDIT-010 through REQ-BKEDIT-012
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            inven = Inven.objects.get(pk=pk)
        except Inven.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        # content is required
        content = request.data.get("content", "").strip()
        if not content:
            return Response({"detail": "content is required."}, status=400)

        note_type = request.data.get("note_type", "GENERAL")
        if note_type not in ("GENERAL", "SHIPPING"):
            return Response({"detail": "note_type must be 'GENERAL' or 'SHIPPING'."}, status=400)

        note = BookNote.objects.create(
            inven=inven,
            note_type=note_type,
            content=content,
            created_by=request.user.username,
        )
        return Response(BookNoteSerializer(note).data, status=201)


class BookNoteResolveView(APIView):
    """
    PATCH /api/book/notes/{pk}/resolve/
    Resolves a GENERAL note. Returns 400 if SHIPPING or already resolved.
    REQ-BKEDIT-013 through REQ-BKEDIT-015
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            note = BookNote.objects.get(pk=pk)
        except BookNote.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        if note.note_type == "SHIPPING":
            return Response({"detail": "SHIPPING notes cannot be resolved."}, status=400)

        if note.is_resolved:
            return Response({"detail": "Note is already resolved."}, status=400)

        note.resolve()
        return Response(BookNoteSerializer(note).data)


class BookShopifyStatusView(APIView):
    """
    PATCH /api/book/{id}/shopify-status/
    Calls Shopify API to set product status (active/draft).
    REQ-BKEDIT-016 through REQ-BKEDIT-019
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    # @MX:WARN: [AUTO] patch — Shopify API call; mutates status_of_shopify + external API
    # @MX:REASON: REQ-BKEDIT-016/017/018 require conditional DB update and external API call
    def patch(self, request, pk):
        from book import services

        try:
            inven = Inven.objects.select_related("info").get(pk=pk)
        except Inven.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        action = request.data.get("action", "")
        if action not in ("active", "draft"):
            return Response({"detail": "action must be 'active' or 'draft'."}, status=400)

        success = services.set_shopify_product_status_for_inven(inven.id, action)
        if not success:
            return Response({"detail": "Shopify API call failed."}, status=502)

        # Update local status_of_shopify based on action
        if action == "draft":
            inven.status_of_shopify = 12
        else:
            # active: 81 if kyobo_category1 set, else 80
            try:
                has_kyobo = bool(inven.info.kyobo_category1)
            except Info.DoesNotExist:
                has_kyobo = False
            inven.status_of_shopify = 81 if has_kyobo else 80

        inven.save(update_fields=["status_of_shopify"])
        return Response({"status_of_shopify": inven.status_of_shopify})


class EtoileShopifyStatusView(APIView):
    """
    PATCH /api/book/{id}/etoile-shopify-status/
    Calls Shopify API to set etoile product status.
    REQ-BKEDIT-020 through REQ-BKEDIT-021
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        from book import services

        try:
            inven = Inven.objects.get(pk=pk)
        except Inven.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        try:
            etoile_inven = inven.etoile_inven
        except EtoileBookInven.DoesNotExist:
            return Response({"detail": "EtoileBookInven not found."}, status=404)

        action = request.data.get("action", "")
        if action not in ("active", "draft"):
            return Response({"detail": "action must be 'active' or 'draft'."}, status=400)

        success = services.set_shopify_product_status_for_etoile_inven(etoile_inven.id, action)
        if not success:
            return Response({"detail": "Shopify API call failed."}, status=502)

        if action == "draft":
            etoile_inven.status_of_shopify = 12
            etoile_inven.save(update_fields=["status_of_shopify"])

        return Response({"status": "ok", "action": action})


class EtoileTagsView(APIView):
    """
    PATCH /api/book/{id}/etoile-tags/
    Saves tags to EtoileBookInfo and syncs to Shopify.
    REQ-BKEDIT-022 through REQ-BKEDIT-025
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        from book import services

        try:
            inven = Inven.objects.get(pk=pk)
        except Inven.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        try:
            etoile_inven = inven.etoile_inven
        except EtoileBookInven.DoesNotExist:
            return Response({"detail": "EtoileBookInven not found."}, status=404)

        try:
            etoile_info = etoile_inven.info
        except EtoileBookInfo.DoesNotExist:
            return Response({"detail": "EtoileBookInfo not found."}, status=404)

        tags = request.data.get("tags", [])
        if not isinstance(tags, list):
            return Response({"detail": "tags must be a list."}, status=400)

        # Save tags to DB regardless of Shopify sync result
        etoile_info.tags = tags
        etoile_info.save(update_fields=["tags"])

        # Sync to Shopify
        shopify_success = services.set_shopify_product_tags_for_etoile_inven(etoile_inven.id, tags)
        if not shopify_success:
            # 207: DB saved but Shopify sync failed
            return Response(
                {"detail": "Tags saved to DB but Shopify sync failed.", "tags": tags},
                status=207,
            )

        return Response(EtoileBookInfoSerializer(etoile_info).data)


# SPEC-INVEN-ADD-001: ISBN bulk add
class InvenSkuBulkAddView(APIView):
    """
    POST /api/book/inven-skus/
    Bulk-create Inven records for new SKUs. Duplicates are returned separately.
    REQ-IADD-001 through REQ-IADD-010
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.db import transaction

        serializer = InvenSkuBulkAddSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        raw_skus = serializer.validated_data["skus"]

        # REQ-IADD-005: strip, remove empty, deduplicate preserving order
        seen: set = set()
        unique_skus: list = []
        for sku in raw_skus:
            s = sku.strip()
            if s and s not in seen:
                seen.add(s)
                unique_skus.append(s)

        if not unique_skus:
            return Response({"skus": ["This field may not be blank."]}, status=400)

        # REQ-IADD-006: partition existing vs new
        existing_set = set(
            Inven.objects.filter(inven_SKU__in=unique_skus).values_list("inven_SKU", flat=True)
        )
        new_skus = [s for s in unique_skus if s not in existing_set]
        duplicate_skus = [s for s in unique_skus if s in existing_set]

        # REQ-IADD-007/008: bulk insert in single transaction
        try:
            with transaction.atomic():
                if new_skus:
                    Inven.objects.bulk_create([
                        Inven(
                            inven_SKU=sku,
                            vendor="북센",
                            store="책방",
                            is_prepared=0,
                            status_of_shopify=0,
                            is_use=1,
                        )
                        for sku in new_skus
                    ])
        except Exception:
            return Response({"error": "Database error during bulk insert."}, status=500)

        return Response({
            "created": new_skus,
            "duplicates": duplicate_skus,
            "created_count": len(new_skus),
            "duplicate_count": len(duplicate_skus),
        })


# SPEC-FAST-LISTING-ADD-001: fast listing bulk add
class FastListingSkuView(APIView):
    """
    POST /api/book/fast-listing-skus/
    Bulk-set Inven records to status_of_shopify=1 (fast listing target).
    New SKUs are inserted; existing SKUs updated unless status IN (80, 81, 82).
    REQ-FLA-001 through REQ-FLA-010
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    # status values representing already-active Shopify listings — must not be overwritten
    _PROTECTED = frozenset({80, 81, 82})

    def post(self, request):
        from django.db import transaction

        serializer = FastListingSkuBulkSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        raw_skus = serializer.validated_data["skus"]

        # REQ-FLA-005: strip, remove empty, deduplicate preserving order
        seen: set = set()
        unique_skus: list = []
        for sku in raw_skus:
            s = sku.strip()
            if s and s not in seen:
                seen.add(s)
                unique_skus.append(s)

        if not unique_skus:
            return Response({"skus": ["This field may not be blank."]}, status=400)

        # Fetch existing records with their current status
        existing: dict = {
            obj.inven_SKU: obj.status_of_shopify
            for obj in Inven.objects.filter(inven_SKU__in=unique_skus).only(
                "inven_SKU", "status_of_shopify"
            )
        }

        new_skus = [s for s in unique_skus if s not in existing]
        # REQ-FLA-007: updatable only when status NOT IN (80, 81, 82)
        updatable_skus = [s for s in unique_skus if s in existing and existing[s] not in self._PROTECTED]
        # REQ-FLA-008: skip protected-status records without modification
        skipped_skus = [s for s in unique_skus if s in existing and existing[s] in self._PROTECTED]

        # REQ-FLA-006/007: all DB writes in a single atomic transaction
        try:
            with transaction.atomic():
                if new_skus:
                    Inven.objects.bulk_create([
                        Inven(
                            inven_SKU=sku,
                            vendor="북센",
                            store="책방",
                            is_prepared=0,
                            status_of_shopify=1,
                            is_use=1,
                        )
                        for sku in new_skus
                    ])
                if updatable_skus:
                    Inven.objects.filter(inven_SKU__in=updatable_skus).update(status_of_shopify=1)
        except Exception:
            return Response({"error": "Database error."}, status=500)

        return Response({
            "created": new_skus,
            "updated": updatable_skus,
            "skipped": skipped_skus,
            "created_count": len(new_skus),
            "updated_count": len(updatable_skus),
            "skipped_count": len(skipped_skus),
        })


# @MX:ANCHOR: [AUTO] ShopifyLiveInfoView.get — real-time Shopify product info entry point
# @MX:REASON: SPEC-SHOPIFY-INFO-001 REQ-SHPINFO-001; called on every BookDetailPage load
# for both Booksen and Etoile stores simultaneously
class ShopifyLiveInfoView(APIView):
    """
    GET /api/book/{pk}/shopify-live-info/
    Returns real-time Shopify product info for Booksen and Etoile stores.
    SPEC-SHOPIFY-INFO-001: REQ-SHPINFO-001 through REQ-SHPINFO-014
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            inven = Inven.objects.get(pk=pk)
        except Inven.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        # Booksen: Inven → Shopify_product (first match)
        booksen_product = Shopify_product.objects.filter(inven=inven).first()

        # Etoile: Inven → EtoileBookInven → EtoileShopifyProduct
        etoile_sp = None
        try:
            etoile_inven = inven.etoile_inven
            etoile_sp = EtoileShopifyProduct.objects.filter(etoile_inven=etoile_inven).first()
        except EtoileBookInven.DoesNotExist:
            pass

        booksen_domain = settings.SHOPIFY_BOOKSEN_DOMAIN
        booksen_token = settings.SHOPIFY_BOOKSEN_TOKEN
        etoile_domain = settings.SHOPIFY_ETOILE_DOMAIN
        etoile_token = settings.SHOPIFY_ETOILE_TOKEN

        def get_booksen() -> dict:
            if not booksen_product:
                return {
                    "registered": False,
                    "product_id": None,
                    "variant_id": None,
                    "status": None,
                    "weight": None,
                    "weight_unit": None,
                    "error": None,
                }
            info = shopify_client.fetch_store_live_info(
                booksen_domain,
                booksen_token,
                booksen_product.product_id,
                booksen_product.variant_id,
            )
            return {
                "registered": True,
                "product_id": booksen_product.product_id,
                "variant_id": booksen_product.variant_id,
                **info,
            }

        def get_etoile() -> dict:
            if not etoile_sp:
                return {
                    "registered": False,
                    "product_id": None,
                    "variant_id": None,
                    "status": None,
                    "weight": None,
                    "weight_unit": None,
                    "error": None,
                }
            info = shopify_client.fetch_store_live_info(
                etoile_domain,
                etoile_token,
                etoile_sp.product_id,
                etoile_sp.variant_id,
            )
            return {
                "registered": True,
                "product_id": etoile_sp.product_id,
                "variant_id": etoile_sp.variant_id,
                **info,
            }

        with ThreadPoolExecutor(max_workers=2) as executor:
            f_booksen = executor.submit(get_booksen)
            f_etoile = executor.submit(get_etoile)
            booksen_data = f_booksen.result()
            etoile_data = f_etoile.result()

        return Response({"booksen": booksen_data, "etoile": etoile_data})


# SPEC-ETOILE-DASHBOARD-001: etoile inventory status dashboard
class EtoileDashboardView(APIView):
    """
    GET /api/book/etoile/dashboard/
    Aggregates EtoileBookInven by status_of_shopify.
    REQ-ETD-001 through REQ-ETD-007
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import F

        raw_counts = (
            EtoileBookInven.objects
            .values("status_of_shopify")
            .annotate(count=Count("id"))
            .order_by(F("status_of_shopify").asc(nulls_last=True))
        )

        status_counts = [
            {
                "status": row["status_of_shopify"],
                "label": (
                    ETOILE_STATUS_LABELS.get(row["status_of_shopify"], "정의되지 않은 상태")
                    if row["status_of_shopify"] is not None
                    else "상태 없음"
                ),
                "count": row["count"],
            }
            for row in raw_counts
        ]

        return Response({
            "status_counts": status_counts,
            "total": sum(row["count"] for row in status_counts),
        })
