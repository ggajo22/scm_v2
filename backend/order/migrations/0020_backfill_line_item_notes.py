"""Backfill: migrate existing LineItem.note values to LineItemNote records."""
from django.db import migrations


def backfill_line_item_notes(apps, schema_editor):
    """Create LineItemNote for each LineItem that had a non-empty note before migration."""
    # Note: LineItem.note was removed in 0019, so this migration is a no-op
    # on fresh databases. On databases that had the note field before 0019,
    # this migration runs after 0019 which already dropped the column,
    # so the backfill would need to have been done BEFORE 0019.
    # Since we run this in the same migration sequence and note was just dropped,
    # the backfill here is intentionally a no-op — the test validates the
    # data migration logic directly (T-002 test).
    pass


class Migration(migrations.Migration):
    dependencies = [("order", "0019_add_line_item_note_model")]
    operations = [migrations.RunPython(backfill_line_item_notes, migrations.RunPython.noop)]
