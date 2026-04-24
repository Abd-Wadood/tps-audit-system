from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from stock_control.sheet_logic import ensure_seed_data
from user_access.access import get_accessible_branches
from stocks.models import DailyStock, StockEntry, StockSheet
from user_access.constants import REPORT_ROLE
from user_access.permissions import role_required

ITEM_SALE_GROUPS = [
    {"key": "pizza_dough", "label": "Pizza Dough", "items": ["Small Dough", "Medium Dough", "Large Dough"], "color": "#d96f4a"},
    {"key": "tortia_wrap", "label": "Tortia Wrap", "items": ["Tortia Wrap"], "color": "#d7a94b"},
    {"key": "paratha_roll", "label": "Paratha Roll", "items": ["Paratha / Bread"], "color": "#7db36e"},
    {"key": "chicken_fillet_burger", "label": "Chicken Fillet Burger", "items": ["Chicken Thigh Fillet"], "color": "#4aa7a2"},
    {"key": "burger_buns", "label": "Burger Buns", "items": ["Burger Buns"], "color": "#c97a3d"},
    {"key": "chicken_piece", "label": "Chicken Piece", "items": ["Chicken Piece"], "color": "#4f86d9"},
    {"key": "chicken_wings", "label": "Chicken Wings", "items": ["Chicken Wings"], "color": "#9a67d1"},
]


def build_sales_graph_data(selected_branch_id, window_start, window_end):
    item_to_group_key = {
        item_name: group["key"]
        for group in ITEM_SALE_GROUPS
        for item_name in group["items"]
    }
    group_key_to_index = {group["key"]: index for index, group in enumerate(ITEM_SALE_GROUPS)}
    sales_filters = {
        "daily_stock__date__gte": window_start,
        "daily_stock__date__lte": window_end,
        "item__name__in": list(item_to_group_key.keys()),
    }
    if selected_branch_id:
        sales_filters["daily_stock__branch_id"] = selected_branch_id

    sale_rows = (
        StockEntry.objects.filter(**sales_filters)
        .values("daily_stock__date", "item__name")
        .annotate(total_sale=Sum("sale"))
        .order_by("daily_stock__date", "item__name")
    )

    date_rows = (
        DailyStock.objects.filter(date__gte=window_start, date__lte=window_end)
        .order_by("date")
        .values_list("date", flat=True)
        .distinct()
    )
    if selected_branch_id:
        date_rows = date_rows.filter(branch_id=selected_branch_id)

    day_map = {day: [0.0] * len(ITEM_SALE_GROUPS) for day in date_rows}
    for row in sale_rows:
        day = row["daily_stock__date"]
        item_name = row["item__name"]
        group_key = item_to_group_key[item_name]
        group_index = group_key_to_index[group_key]
        day_map.setdefault(day, [0.0] * len(ITEM_SALE_GROUPS))
        day_map[day][group_index] += float(row["total_sale"] or 0)

    days = []
    total_values = [0.0] * len(ITEM_SALE_GROUPS)
    for day, values in day_map.items():
        for index, value in enumerate(values):
            total_values[index] += value
        top_value = max(values) if values else 0
        top_index = values.index(top_value) if top_value > 0 else None
        days.append(
            {
                "date": day.isoformat(),
                "display_date": day.strftime("%d %b"),
                "values": [round(value, 2) for value in values],
                "top_label": ITEM_SALE_GROUPS[top_index]["label"] if top_index is not None else "No sales",
                "top_value": round(top_value, 2),
            }
        )

    return {
        "categories": [
            {
                "key": group["key"],
                "label": group["label"],
                "color": group["color"],
                "total": round(total_values[index], 2),
            }
            for index, group in enumerate(ITEM_SALE_GROUPS)
        ],
        "days": days,
        "has_data": bool(days),
    }


def build_reports_dashboard_context(request, graph_only_view=False):
    ensure_seed_data()
    branches = get_accessible_branches(request.user)
    selected_branch_id = request.GET.get("branch")
    selected_date_raw = request.GET.get("date", "").strip()
    selected_date_from_raw = request.GET.get("date_from", "").strip()
    selected_date_to_raw = request.GET.get("date_to", "").strip()
    selected_date = parse_date(selected_date_raw) if selected_date_raw else None
    selected_date_from = parse_date(selected_date_from_raw) if selected_date_from_raw else None
    selected_date_to = parse_date(selected_date_to_raw) if selected_date_to_raw else None
    default_window_end = timezone.localdate()
    default_window_start = default_window_end - timezone.timedelta(days=9)
    has_any_date_filter = bool(selected_date or selected_date_from or selected_date_to)

    if selected_date:
        filter_start = selected_date
        filter_end = selected_date
    elif selected_date_from and selected_date_to:
        filter_start = min(selected_date_from, selected_date_to)
        filter_end = max(selected_date_from, selected_date_to)
    elif selected_date_from:
        filter_start = selected_date_from
        filter_end = selected_date_from
    elif selected_date_to:
        filter_start = selected_date_to
        filter_end = selected_date_to
    else:
        filter_start = default_window_start
        filter_end = default_window_end

    daily_reports = DailyStock.objects.select_related("branch").order_by("-date", "branch__name")
    account_reports = StockSheet.objects.select_related("branch", "created_by").order_by("-sheet_date", "branch__name", "-created_at")

    if selected_branch_id:
        daily_reports = daily_reports.filter(branch_id=selected_branch_id)
        account_reports = account_reports.filter(branch_id=selected_branch_id)

    daily_reports = daily_reports.filter(date__gte=filter_start, date__lte=filter_end)
    account_reports = account_reports.filter(sheet_date__gte=filter_start, sheet_date__lte=filter_end)

    sales_graph = (
        build_sales_graph_data(selected_branch_id, filter_start, filter_end)
        if graph_only_view
        else {"categories": [], "days": [], "has_data": False}
    )

    context = {
        "daily_reports": daily_reports,
        "account_reports": account_reports,
        "branches": branches,
        "selected_branch_id": int(selected_branch_id) if selected_branch_id else None,
        "selected_date": selected_date_raw,
        "selected_date_from": selected_date_from_raw,
        "selected_date_to": selected_date_to_raw,
        "default_window_active": not has_any_date_filter,
        "default_window_start": default_window_start,
        "default_window_end": default_window_end,
        "report_window_start": filter_start,
        "report_window_end": filter_end,
        "sales_graph": sales_graph,
        "graph_only_view": graph_only_view,
        "graph_group_definitions": [
            {
                "label": group["label"],
                "items_text": ", ".join(group["items"]),
            }
            for group in ITEM_SALE_GROUPS
        ],
        "total_daily_reports": DailyStock.objects.count(),
        "total_account_reports": StockSheet.objects.count(),
    }
    return context


@role_required(REPORT_ROLE)
def reports_dashboard_view(request):
    context = build_reports_dashboard_context(request, graph_only_view=False)
    return render(request, "reports_center/reports_dashboard.html", context)


@role_required(REPORT_ROLE)
def sales_graph_view(request):
    context = build_reports_dashboard_context(request, graph_only_view=True)
    return render(request, "reports_center/reports_dashboard.html", context)
