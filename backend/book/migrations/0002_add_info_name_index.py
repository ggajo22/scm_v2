"""
Migration: Add db_index on Info.name for search performance.
REQ-SEARCH-004
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("book", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="info",
            name="name",
            field=models.CharField(max_length=100, db_index=True),
        ),
    ]
