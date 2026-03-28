from django.contrib import admin

from .models import Branch, DailyStock, Item, StockEntry, StockSheet


class StockEntryInline(admin.TabularInline):
    model = StockEntry
    extra = 0


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(DailyStock)
class DailyStockAdmin(admin.ModelAdmin):
    list_display = ("date", "branch", "total_orders", "shop_orders", "food_panda_orders")
    list_filter = ("date", "branch")
    search_fields = ("branch__name",)
    inlines = [StockEntryInline]


@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ("daily_stock", "item", "opening", "received", "sale", "cancelled", "exchange", "ready")
    list_filter = ("daily_stock__date", "daily_stock__branch")
    search_fields = ("item__name", "daily_stock__branch__name")


@admin.register(StockSheet)
class StockSheetAdmin(admin.ModelAdmin):
    list_display = ("reference_number", "title", "sheet_date", "branch", "system_sale", "created_by")
    list_filter = ("sheet_date", "branch")
    search_fields = ("reference_number", "title", "branch__name", "created_by__username")
