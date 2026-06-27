"""Add note_type field to LineItemNote model."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0020_backfill_line_item_notes"),
    ]

    operations = [
        migrations.AddField(
            model_name="lineitemnote",
            name="note_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("주문취소", "주문취소"),
                    ("주문보류", "주문보류"),
                    ("CS필요", "CS필요"),
                    ("타출판사", "타출판사"),
                    ("CS요청", "CS요청"),
                    ("발주요청", "발주요청"),
                    ("발주제외", "발주제외"),
                ],
                default="",
                max_length=20,
            ),
        ),
    ]
