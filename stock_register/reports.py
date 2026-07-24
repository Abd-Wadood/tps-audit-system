from decimal import Decimal, ROUND_HALF_UP

from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce

from .models import Item, StockTransaction


TWO_PLACES = Decimal("0.01")


def calendar_month_count(date_from, date_to):
    """Return the number of calendar months touched by an inclusive date range."""
    if not date_from or not date_to or date_from > date_to:
        return 0
    return (date_to.year - date_from.year) * 12 + date_to.month - date_from.month + 1


def build_monthly_usage_rows(branch_id, date_from, date_to):
    """Summarize Stock Out quantities and their per-calendar-month average by item."""
    month_count = calendar_month_count(date_from, date_to)
    if not month_count:
        return [], 0

    usage_filter = Q(
        transactions__transaction_type=StockTransaction.OUT,
        transactions__created_at__date__gte=date_from,
        transactions__created_at__date__lte=date_to,
    )
    items = Item.objects.select_related("branch")
    if branch_id:
        items = items.filter(branch_id=branch_id)
    items = items.annotate(
        total_used=Coalesce(
            Sum("transactions__quantity", filter=usage_filter),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    ).order_by("branch__name", "name")

    rows = []
    divisor = Decimal(month_count)
    for item in items:
        total_used = item.total_used.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        rows.append(
            {
                "item": item,
                "total_used": total_used,
                "monthly_average": (total_used / divisor).quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
            }
        )
    return rows, month_count
