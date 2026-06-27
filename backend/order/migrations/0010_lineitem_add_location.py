from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0009_order_add_location"),
    ]

    operations = [
        migrations.AddField(
            model_name="lineitem",
            name="location",
            field=models.CharField(blank=True, default="", max_length=10),
        ),
    ]
