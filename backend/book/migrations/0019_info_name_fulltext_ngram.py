"""
Migration: Replace existing FULLTEXT index on Info.name with ngram parser.
Existing ft_book_info_name uses the default (whitespace) parser — not suitable for Korean.
This drops it and recreates with ngram parser for n-gram tokenization.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("book", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE book_info DROP INDEX ft_book_info_name",
                "ALTER TABLE book_info ADD FULLTEXT INDEX ft_info_name_ngram (name) WITH PARSER ngram",
            ],
            reverse_sql=[
                "ALTER TABLE book_info DROP INDEX ft_info_name_ngram",
                "ALTER TABLE book_info ADD FULLTEXT INDEX ft_book_info_name (name)",
            ],
        ),
    ]
