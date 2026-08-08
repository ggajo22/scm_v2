# SPEC-ORDER-011 REQ-LOGI-001/008: add LineItem.logistics_status (5-value
# choices, mirrors 0011_lineitem_add_purchase_status.py's single-AddField-
# with-inline-choices style) and widen Order.status with the same 5 values
# plus "partial" (bundling the two related field changes in one migration,
# mirroring 0029_lineitem_damaged_exchange_status.py's convention). Both
# operations are additive/choices-only:
#   - AddField(logistics_status, default="not_shipped") backfills every
#     existing LineItem row with the default at the DB level (MySQL applies
#     the AddField default as a static value during ALTER TABLE ADD COLUMN).
#   - AlterField(Order.status, choices=[...]) is a metadata-only change — the
#     column (max_length=50, null=True, blank=True) and any existing stored
#     values are unchanged; only the declared choices list is added.
# No data migration for Order.status recomputation happens here — see
# 0031_backfill_order_status.py (REQ-LOGI-012).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0029_lineitem_damaged_exchange_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='lineitem',
            name='logistics_status',
            field=models.CharField(choices=[('not_shipped', '미입고'), ('shipment_confirmed', '입고예정'), ('received', '입고'), ('outbound_scheduled', '출고예정'), ('shipped', '출고')], default='not_shipped', max_length=20),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(blank=True, choices=[('not_shipped', '미입고'), ('shipment_confirmed', '입고예정'), ('received', '입고'), ('outbound_scheduled', '출고예정'), ('shipped', '출고'), ('partial', '부분입고')], max_length=50, null=True),
        ),
    ]
