from django.db import migrations


class Migration(migrations.Migration):
    """Fix typo: orders_booksendata -> orders_bookseendata (migration 0014 introduced the typo)."""

    dependencies = [
        ("order", "0016_add_sungseoyunion_distributor"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="bookseendata",
            table="orders_bookseendata",
        ),
    ]
