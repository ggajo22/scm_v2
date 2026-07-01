from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("book", "0021_rename_booksen_category"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Booxen_category",
            new_name="Booksen_category",
        ),
    ]
