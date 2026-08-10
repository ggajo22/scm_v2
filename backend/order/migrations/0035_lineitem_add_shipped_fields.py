from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0034_lineitem_add_rack_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="lineitem",
            name="shipped_quantity",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="lineitem",
            name="shipped_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
