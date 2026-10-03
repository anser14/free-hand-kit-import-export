from django.contrib import admin

from .models import Category, Product, Tag

admin.site.register(Category)
admin.site.register(Tag)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "price", "category", "owner")
    search_fields = ("sku", "name")
    list_filter = ("category",)
