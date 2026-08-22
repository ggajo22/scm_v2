# SPEC-ORDER-025 M2: additive nullable column, no data backfill needed —
# every existing LineItem simply gets original_sku=NULL, matching the
# "unused unless manually corrected" semantics. Same additive-column shape
# as 0039_lineitem_damaged_quantity.py.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0043_storesyncwatermark_last_run_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="lineitem",
            name="original_sku",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
