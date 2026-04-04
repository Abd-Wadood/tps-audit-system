from decimal import Decimal, InvalidOperation
from datetime import date

from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date

from stocks.models import Branch, DEFAULT_ITEM_NAMES, DailyStock, Item, StockEntry

STOCK_BRANCH_NAMES = ["Barki Road", "Bediyan Road"]


def coerce_int(value):
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def coerce_decimal(value):
    try:
        return max(Decimal(str(value)), Decimal("0"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def ensure_seed_data():
    for branch_name in STOCK_BRANCH_NAMES:
        Branch.objects.get_or_create(name=branch_name)

    existing_items = set(Item.objects.values_list("name", flat=True))
    missing_items = [Item(name=name) for name in DEFAULT_ITEM_NAMES if name not in existing_items]
    if missing_items:
        Item.objects.bulk_create(missing_items)


def parse_selected_date(raw_date):
    if raw_date is None:
        return date.today()

    parsed_date = parse_date(str(raw_date).strip())
    if parsed_date is None:
        return date.today()
    return parsed_date


def resolve_sheet(branch_id=None, raw_date=None, branch_queryset=None, default_branch_id=None):
    ensure_seed_data()

    branches = branch_queryset if branch_queryset is not None else Branch.objects.order_by("name")
    branch = branches.filter(pk=branch_id).first() if branch_id else None
    if branch is None and default_branch_id:
        branch = branches.filter(pk=default_branch_id).first()
    if branch is None:
        branch = branches.first()
    if branch is None:
        branch = get_object_or_404(Branch, name=STOCK_BRANCH_NAMES[0])
    selected_date = parse_selected_date(raw_date)

    daily_stock, daily_stock_created = DailyStock.objects.get_or_create(branch=branch, date=selected_date)
    items = list(Item.objects.all())
    existing_item_ids = set(daily_stock.entries.values_list("item_id", flat=True))
    missing_entries = [StockEntry(daily_stock=daily_stock, item=item) for item in items if item.id not in existing_item_ids]
    if missing_entries:
        StockEntry.objects.bulk_create(missing_entries)

    return {
        "branches": branches,
        "branch": branch,
        "selected_date": selected_date,
        "daily_stock": daily_stock,
        "daily_stock_created": daily_stock_created,
        "entries": list(daily_stock.entries.select_related("item").order_by("item_id")),
        "recent_sheets": list(DailyStock.objects.select_related("branch").order_by("-date", "branch__name")[:20]),
        "totals": {
            "total_orders": daily_stock.total_orders,
            "shop_orders": daily_stock.shop_orders,
            "food_panda_orders": daily_stock.food_panda_orders,
        },
    }
