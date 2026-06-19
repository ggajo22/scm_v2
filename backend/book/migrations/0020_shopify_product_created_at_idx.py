from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("book", "0019_info_name_fulltext_ngram"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE book_shopify_product ADD INDEX idx_shopify_created_at (created_at)",
            reverse_sql="ALTER TABLE book_shopify_product DROP INDEX idx_shopify_created_at",
        ),
    ]
