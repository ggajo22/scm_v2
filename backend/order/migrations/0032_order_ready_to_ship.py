# SPEC-ORDER-012 REQ-RTS-001: add Order.ready_to_ship as a new column
# (BooleanField(null=True, blank=True), no choices, no default) — mirrors
# 0030_lineitem_logistics_status_alter_order_status.py's single-AddField
# style. Unlike Order.status (SPEC-ORDER-011), this is a brand-new column,
# not a redefinition of an existing one — every pre-existing row gets NULL
# at the DB level (MySQL applies no explicit default for a nullable column
# added without one). Data backfill happens separately in
# 0033_backfill_order_ready_to_ship.py (REQ-RTS-006), mirroring the
# 0030/0031 schema/backfill split.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0031_backfill_order_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='ready_to_ship',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
