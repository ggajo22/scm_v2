from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0015_lineitem_add_note"),
    ]

    operations = [
        migrations.AlterField(
            model_name="distributorvendorrule",
            name="distributor",
            field=models.CharField(
                choices=[
                    ("choeumgoyuk", "처음교육"),
                    ("agape", "아가페"),
                    ("sungseoyunion", "성서유니온"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="purchaseorder",
            name="distributor",
            field=models.CharField(
                choices=[
                    ("bookseen", "북센"),
                    ("kyobo", "교보"),
                    ("choeumgoyuk", "처음교육"),
                    ("agape", "아가페"),
                    ("sungseoyunion", "성서유니온"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="vendorcomparison",
            name="selected_distributor",
            field=models.CharField(
                blank=True,
                choices=[
                    ("bookseen", "북센"),
                    ("kyobo", "교보"),
                    ("warehouse", "재고"),
                    ("warehouse_west", "재고-서부확인"),
                    ("check_required", "확인필요"),
                    ("choeumgoyuk", "처음교육"),
                    ("agape", "아가페"),
                    ("sungseoyunion", "성서유니온"),
                ],
                max_length=20,
                null=True,
            ),
        ),
    ]
