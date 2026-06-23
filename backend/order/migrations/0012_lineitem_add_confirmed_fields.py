from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0011_lineitem_add_purchase_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="lineitem",
            name="confirmed_price",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="lineitem",
            name="confirmed_distributor",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="lineitem",
            name="confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
