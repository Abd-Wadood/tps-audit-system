from django.contrib import admin

from .models import Item, StockTransaction


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("branch", "name", "unit", "current_stock", "created_at")
    list_filter = ("branch",)
    search_fields = ("name", "unit", "branch__name")
    readonly_fields = ("current_stock", "created_at")


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "branch", "item", "transaction_type", "quantity", "rate", "total_amount", "balance_after", "received_from", "issued_to", "created_by")
    list_filter = ("item__branch", "transaction_type", "created_at")
    search_fields = ("item__name", "item__branch__name", "received_from", "issued_to", "notes", "created_by__username")
    readonly_fields = ("balance_after", "total_amount", "created_at")

    @admin.display(ordering="item__branch__name")
    def branch(self, obj):
        return obj.item.branch
