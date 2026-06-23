from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("order", "0014_rename_bookseendata_table"),
    ]

    operations = [
        migrations.AddField(
            model_name="lineitem",
            name="note",
            field=models.TextField(blank=True, null=True),
        ),
    ]
