from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0033_backfill_order_ready_to_ship"),
    ]

    operations = [
        migrations.AddField(
            model_name="lineitem",
            name="rack_number",
            field=models.CharField(blank=True, default="", max_length=10),
        ),
    ]
