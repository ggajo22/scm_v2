from django.db import models
from django.db.models import Q
from django.utils import timezone


class Inven(models.Model):
    inven_SKU = models.CharField(max_length=40, db_index=True)
    vendor = models.CharField(max_length=40)
    store = models.CharField(max_length=40)
    is_prepared = models.SmallIntegerField(default=0)
    status_of_shopify = models.SmallIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_use = models.SmallIntegerField(default=0)

    booxen_api_status = models.SmallIntegerField(default=0)
    kyobo_crawl_status = models.SmallIntegerField(default=0)
    yes24_crawl_status = models.SmallIntegerField(default=0)
    aladin_crawl_status = models.SmallIntegerField(default=0)

    @staticmethod
    def search(query):
        return Inven.objects.filter(
            Q(inven_SKU__icontains=query) |
            Q(vendor__icontains=query) |
            Q(store__icontains=query)
        )

    class Meta:
        indexes = [
            models.Index(fields=["inven_SKU", "status_of_shopify"]),
        ]


class Info(models.Model):
    inven = models.OneToOneField(Inven, on_delete=models.CASCADE, related_name='info')
    status = models.CharField(max_length=10)
    price_sale = models.FloatField(default=0.0)
    name = models.CharField(max_length=100)
    useruse1 = models.CharField(max_length=30)
    useruse2 = models.CharField(max_length=50)
    price = models.FloatField(default=0.0)
    opndate = models.CharField(max_length=10, default='0000-00-00')
    outrt2 = models.IntegerField(default=0)
    qty = models.IntegerField(default=0)
    retyn = models.CharField(max_length=2)
    booxen_cate_cd1 = models.IntegerField(default=0)
    booxen_cate_cd2 = models.IntegerField(default=0)
    booxen_cate_cd3 = models.IntegerField(default=0)
    page = models.IntegerField(default=0)
    weight = models.IntegerField(default=0)
    kyobo_weight = models.IntegerField(default=0)
    kyobo_status = models.CharField(max_length=10, blank=True, default='')
    kyobo_supply_price = models.IntegerField(default=0)
    yes24_weight = models.IntegerField(default=0)
    aladin_weight = models.IntegerField(default=0)
    manual_weight = models.IntegerField(default=0)
    dim1 = models.IntegerField(default=0)
    dim2 = models.IntegerField(default=0)
    dim3 = models.IntegerField(default=0)
    image_detail = models.TextField(default='')
    cover_image_url = models.TextField(default='')
    cover_image_url2 = models.TextField(default='')
    desc_table = models.TextField(default='')
    desc_pub = models.TextField(default='')
    desc_author = models.TextField(default='')
    desc_desc = models.TextField(default='')
    kyobo_category1 = models.CharField(max_length=30, blank=True, default='')
    kyobo_category2 = models.CharField(max_length=30, blank=True, default='')
    kyobo_category3 = models.CharField(max_length=30, blank=True, default='')
    kyobo_category4 = models.CharField(max_length=30, blank=True, default='')
    kyobo_category5 = models.CharField(max_length=30, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["price_sale"]),
            models.Index(fields=["price", "kyobo_supply_price"]),
        ]


class Shopify_product(models.Model):
    inven = models.ForeignKey(Inven, on_delete=models.CASCADE, related_name='shopify_product')
    product_id = models.CharField(max_length=20)
    variant_id = models.CharField(max_length=20, default='0')
    inventory_item_id = models.CharField(max_length=20, default='0')
    shopify_price = models.FloatField(default=0.0)
    is_new_arrival = models.SmallIntegerField(default=0)
    image_url = models.URLField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Booxen_category(models.Model):
    category_rank = models.SmallIntegerField(default=0)
    category_code = models.IntegerField(default=0)
    category_name = models.CharField(max_length=30)
    top_category_code = models.IntegerField(default=0)


class Collection(models.Model):
    collection_id = models.CharField(max_length=30)
    name = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Collect(models.Model):
    inven = models.ForeignKey(Inven, on_delete=models.CASCADE, related_name='collect')
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='collect')
    collect_id = models.CharField(max_length=30)
    is_use = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class BookNote(models.Model):
    NOTE_TYPE_CHOICES = [
        ("GENERAL", "도서 노트"),
        ("SHIPPING", "출고 노트"),
    ]

    inven = models.ForeignKey(Inven, on_delete=models.CASCADE, related_name="notes")
    note_type = models.CharField(max_length=20, choices=NOTE_TYPE_CHOICES, default="GENERAL")
    content = models.TextField()
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = 'book_note'

    def resolve(self):
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.save(update_fields=["is_resolved", "resolved_at"])


class EtoileBookInven(models.Model):
    inven = models.OneToOneField(
        Inven, on_delete=models.RESTRICT, related_name='etoile_inven', db_index=True
    )
    status_of_shopify = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'etoile_book_inven'


class EtoileBookInfo(models.Model):
    etoile_inven = models.OneToOneField(
        EtoileBookInven, on_delete=models.CASCADE, related_name='info'
    )
    name_en = models.CharField(max_length=255, default='')
    desc_en = models.TextField(default='')
    preview_urls = models.JSONField(default=list)
    tags = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'etoile_book_info'


class EtoileShopifyProduct(models.Model):
    etoile_inven = models.ForeignKey(
        EtoileBookInven, on_delete=models.CASCADE, related_name='shopify_product'
    )
    product_id = models.CharField(max_length=20)
    variant_id = models.CharField(max_length=20, default='0')
    inventory_item_id = models.CharField(max_length=20, default='0')
    shopify_price = models.FloatField(default=0.0)
    is_new_arrival = models.SmallIntegerField(default=0)
    image_url = models.URLField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'etoile_book_shopify_product'
