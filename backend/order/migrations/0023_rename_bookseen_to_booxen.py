from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0022_shopifyskusetmapping"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="BookseenData",
            new_name="BooxenData",
        ),
        migrations.AlterField(
            model_name="purchaseorder",
            name="distributor",
            field=models.CharField(
                choices=[
                    ("booxen", "북센"),
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
                choices=[
                    ("booxen", "북센"),
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
                blank=True,
            ),
        ),
        migrations.RunSQL(
            sql=[
                "UPDATE orders_purchaseorder SET distributor = 'booxen' WHERE distributor = 'bookseen';",
                "UPDATE orders_vendorcomparison SET selected_distributor = 'booxen' WHERE selected_distributor = 'bookseen';",
                "UPDATE orders_purchaseorderlineitem SET confirmed_distributor = 'booxen' WHERE confirmed_distributor = 'bookseen';",
            ],
            reverse_sql=[
                "UPDATE orders_purchaseorder SET distributor = 'bookseen' WHERE distributor = 'booxen';",
                "UPDATE orders_vendorcomparison SET selected_distributor = 'bookseen' WHERE selected_distributor = 'booxen';",
                "UPDATE orders_purchaseorderlineitem SET confirmed_distributor = 'bookseen' WHERE confirmed_distributor = 'booxen';",
            ],
        ),
    ]
