from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("book", "0020_shopify_product_created_at_idx"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Booksen_category",
            new_name="Booxen_category",
        ),
    ]
