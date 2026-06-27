from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0013_split_vendor_data"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="bookseendata",
            table="orders_booksendata",
        ),
    ]
