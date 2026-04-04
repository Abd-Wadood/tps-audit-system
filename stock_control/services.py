from user_access.access import get_accessible_branches, get_user_branch_id

from .sheet_logic import coerce_int, normalize_stock_value, resolve_sheet


def get_stock_sheet_context(user, branch_id=None, raw_date=None):
    return resolve_sheet(
        branch_id,
        raw_date,
        branch_queryset=get_accessible_branches(user),
        default_branch_id=None if user.is_superuser else get_user_branch_id(user),
    )


def save_stock_sheet_entries(entries_by_id, post_data):
    for entry_id, entry in entries_by_id.items():
        entry.opening = normalize_stock_value(post_data.get(f"opening_{entry_id}"), entry.item.name)
        entry.received = normalize_stock_value(post_data.get(f"received_{entry_id}"), entry.item.name)
        entry.stock = entry.opening + entry.received
        entry.sale = normalize_stock_value(post_data.get(f"sale_{entry_id}"), entry.item.name)
        entry.exchange = normalize_stock_value(post_data.get(f"exchange_{entry_id}"), entry.item.name)
        entry.in_hand = entry.stock - entry.sale + entry.cancelled
        entry.remaining_value = normalize_stock_value(post_data.get(f"remaining_{entry_id}"), entry.item.name)
        entry.save(update_fields=["opening", "received", "stock", "sale", "exchange", "in_hand", "remaining_value"])


def save_stock_totals(daily_stock, post_data, user):
    daily_stock.total_orders = coerce_int(post_data.get("total_orders"))
    daily_stock.shop_orders = coerce_int(post_data.get("shop_orders"))
    daily_stock.food_panda_orders = coerce_int(post_data.get("food_panda_orders"))
    daily_stock.last_updated_by = user
    daily_stock.save()


def save_accounting_review_entries(entries_by_id, post_data):
    for entry_id, entry in entries_by_id.items():
        entry.stock = entry.opening + entry.received
        entry.cancelled = normalize_stock_value(post_data.get(f"cancelled_{entry_id}"), entry.item.name)
        entry.ready = normalize_stock_value(post_data.get(f"ready_{entry_id}"), entry.item.name)
        entry.in_hand = entry.stock - entry.sale + entry.cancelled
        entry.remaining_value = normalize_stock_value(post_data.get(f"remaining_{entry_id}"), entry.item.name)
        entry.save(update_fields=["stock", "cancelled", "ready", "in_hand", "remaining_value"])


def prepare_accounting_review_entries(entries):
    for entry in entries:
        entry.review_base_remaining = max(entry.remaining - entry.ready, 0)
    return entries
