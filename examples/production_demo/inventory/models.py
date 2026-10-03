from django.conf import settings
from django.db import models


class Category(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    sku = models.CharField(max_length=32)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    tags = models.ManyToManyField(Tag, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("owner", "sku"),
                name="inventory_owner_sku_uniq",
            )
        ]

    def __str__(self) -> str:
        return self.sku
