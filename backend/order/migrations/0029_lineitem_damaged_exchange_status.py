# SPEC-PURCHASE-ORDER-010 REQ-DMG-001/004/007: add the "damaged_exchange"
# (파손/교환) purchase_status value and its matching LineItemNote note_type,
# bundled in one migration (mirrors 0012_lineitem_add_confirmed_fields.py's
# convention of bundling related field changes in a single file). Both
# operations are choices-list widenings only — no data backfill required,
# existing LineItem/LineItemNote records are left unchanged (AC-DMG-007).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0028_kyobodata_list_price"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lineitem",
            name="purchase_status",
            field=models.CharField(
                choices=[
                    ("unordered", "미발주"),
                    ("on_hold", "주문보류"),
                    ("order_cancelled", "주문취소"),
                    ("other_publisher", "타출판사"),
                    ("cs_required", "CS필요"),
                    ("in_stock", "재고"),
                    ("damaged_exchange", "파손/교환"),
                ],
                default="unordered",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="lineitemnote",
            name="note_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("주문취소", "주문취소"),
                    ("주문보류", "주문보류"),
                    ("CS필요", "CS필요"),
                    ("타출판사", "타출판사"),
                    ("CS요청", "CS요청"),
                    ("발주요청", "발주요청"),
                    ("발주제외", "발주제외"),
                    ("파손/교환", "파손/교환"),
                ],
                default="",
                max_length=20,
            ),
        ),
    ]
