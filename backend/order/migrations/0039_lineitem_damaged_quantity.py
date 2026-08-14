# SPEC-PURCHASE-ORDER-011 REQ-DEX-001: additive column, safe default (0),
# no data backfill needed — every existing LineItem simply gets
# damaged_quantity=0, matching the "unused unless damaged_exchange"
# semantics (REQ-DEX-012a). Same additive-column shape as
# 0035_lineitem_add_shipped_fields.py.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0038_refund_unique_per_line_item"),
    ]

    operations = [
        migrations.AddField(
            model_name="lineitem",
            name="damaged_quantity",
            field=models.IntegerField(default=0),
        ),
    ]
