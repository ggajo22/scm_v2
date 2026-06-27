from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0012_lineitem_add_confirmed_fields"),
    ]

    operations = [
        # Create orders_bookseendata table
        migrations.CreateModel(
            name="BookseenData",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sku", models.CharField(max_length=255, unique=True)),
                ("available", models.BooleanField(blank=True, null=True)),
                ("price", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("stock", models.IntegerField(blank=True, null=True)),
                ("returnable", models.BooleanField(blank=True, null=True)),
                ("status", models.CharField(blank=True, max_length=50, null=True)),
                ("arrival", models.CharField(blank=True, max_length=100, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "orders_bookseendata",
            },
        ),
        migrations.AddIndex(
            model_name="bookseendata",
            index=models.Index(fields=["sku"], name="orders_book_sku_idx"),
        ),
        # Create orders_kyobodata table
        migrations.CreateModel(
            name="KyoboData",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sku", models.CharField(max_length=255, unique=True)),
                ("available", models.BooleanField(blank=True, null=True)),
                ("price", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("stock", models.IntegerField(blank=True, null=True)),
                ("returnable", models.BooleanField(blank=True, null=True)),
                ("status", models.CharField(blank=True, max_length=50, null=True)),
                ("publisher", models.CharField(blank=True, max_length=255, null=True)),
                ("ordered_qty", models.IntegerField(blank=True, null=True)),
                ("total_price", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "orders_kyobodata",
            },
        ),
        migrations.AddIndex(
            model_name="kyobodata",
            index=models.Index(fields=["sku"], name="orders_kyob_sku_idx"),
        ),
        # Remove bookseen_* columns from orders_vendorcomparison
        migrations.RemoveField(model_name="vendorcomparison", name="bookseen_available"),
        migrations.RemoveField(model_name="vendorcomparison", name="bookseen_price"),
        migrations.RemoveField(model_name="vendorcomparison", name="bookseen_stock"),
        migrations.RemoveField(model_name="vendorcomparison", name="bookseen_returnable"),
        migrations.RemoveField(model_name="vendorcomparison", name="bookseen_status"),
        migrations.RemoveField(model_name="vendorcomparison", name="bookseen_arrival"),
        # Remove kyobo_* columns from orders_vendorcomparison
        migrations.RemoveField(model_name="vendorcomparison", name="kyobo_available"),
        migrations.RemoveField(model_name="vendorcomparison", name="kyobo_price"),
        migrations.RemoveField(model_name="vendorcomparison", name="kyobo_stock"),
        migrations.RemoveField(model_name="vendorcomparison", name="kyobo_returnable"),
        migrations.RemoveField(model_name="vendorcomparison", name="kyobo_status"),
        migrations.RemoveField(model_name="vendorcomparison", name="kyobo_publisher"),
        migrations.RemoveField(model_name="vendorcomparison", name="kyobo_ordered_qty"),
        migrations.RemoveField(model_name="vendorcomparison", name="kyobo_total_price"),
    ]
