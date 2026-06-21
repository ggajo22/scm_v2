from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import WarehouseStock

_VALID_LOCATIONS = {"korea", "ca", "nj"}


# @MX:NOTE: [AUTO] Response is pivoted by location — one row per ISBN with korea/ca/nj columns
# each with its own PK for targeted delete. Flat rows (one per isbn+location) are stored in DB.
class WarehouseStockListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stocks = WarehouseStock.objects.all().order_by("isbn", "location")

        isbn_map: dict[str, dict] = {}
        for s in stocks:
            if s.isbn not in isbn_map:
                isbn_map[s.isbn] = {
                    "isbn": s.isbn,
                    "korea": None, "korea_pk": None,
                    "ca": None, "ca_pk": None,
                    "nj": None, "nj_pk": None,
                }
            isbn_map[s.isbn][s.location] = s.quantity
            isbn_map[s.isbn][f"{s.location}_pk"] = s.pk

        results = list(isbn_map.values())
        return Response({"count": len(results), "results": results})


class WarehouseStockUpsertView(APIView):
    """Create or update a single (isbn, location) entry."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        isbn = str(request.data.get("isbn", "")).strip()
        location = str(request.data.get("location", "")).strip()
        raw_qty = request.data.get("quantity")

        if not isbn or not location:
            return Response(
                {"error": "isbn and location are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if location not in _VALID_LOCATIONS:
            return Response(
                {"error": f"location must be one of {sorted(_VALID_LOCATIONS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            quantity = int(raw_qty)
        except (TypeError, ValueError):
            return Response(
                {"error": "quantity must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj, created = WarehouseStock.objects.update_or_create(
            isbn=isbn,
            location=location,
            defaults={"quantity": quantity},
        )
        return Response(
            {"id": obj.pk, "isbn": obj.isbn, "location": obj.location, "quantity": obj.quantity},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class WarehouseStockBulkView(APIView):
    """Bulk create-or-update entries. Body: [{isbn, location, quantity}, ...]."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        items = request.data
        if not isinstance(items, list):
            return Response({"error": "Expected a list"}, status=status.HTTP_400_BAD_REQUEST)

        upserted = 0
        for item in items:
            isbn = str(item.get("isbn", "")).strip()
            location = str(item.get("location", "")).strip()
            try:
                quantity = int(item.get("quantity", 0))
            except (TypeError, ValueError):
                continue
            if not isbn or location not in _VALID_LOCATIONS:
                continue
            WarehouseStock.objects.update_or_create(
                isbn=isbn,
                location=location,
                defaults={"quantity": quantity},
            )
            upserted += 1

        return Response({"upserted_count": upserted})


class WarehouseStockDeleteView(APIView):
    """Delete a single stock row by primary key."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            obj = WarehouseStock.objects.get(pk=pk)
        except WarehouseStock.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
