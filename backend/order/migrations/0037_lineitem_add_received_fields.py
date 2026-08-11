from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0036_order_name_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="lineitem",
            name="received_quantity",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="lineitem",
            name="received_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
