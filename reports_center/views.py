from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from stock_control.sheet_logic import ensure_seed_data
from user_access.access import get_accessible_branches
from stocks.models import DailyStock, StockSheet
from user_access.constants import REPORT_ROLE
from user_access.permissions import role_required


@role_required(REPORT_ROLE)
def reports_dashboard_view(request):
    ensure_seed_data()
    branches = get_accessible_branches(request.user)
    selected_branch_id = request.GET.get("branch")
    selected_date_raw = request.GET.get("date", "").strip()
    selected_date = parse_date(selected_date_raw) if selected_date_raw else None
    default_window_end = timezone.localdate()
    default_window_start = default_window_end - timezone.timedelta(days=9)

    daily_reports = DailyStock.objects.select_related("branch").order_by("-date", "branch__name")
    account_reports = StockSheet.objects.select_related("branch", "created_by").order_by("-sheet_date", "branch__name", "-created_at")

    if selected_branch_id:
        daily_reports = daily_reports.filter(branch_id=selected_branch_id)
        account_reports = account_reports.filter(branch_id=selected_branch_id)

    if selected_date:
        daily_reports = daily_reports.filter(date=selected_date)
        account_reports = account_reports.filter(sheet_date=selected_date)
    else:
        daily_reports = daily_reports.filter(date__gte=default_window_start, date__lte=default_window_end)
        account_reports = account_reports.filter(sheet_date__gte=default_window_start, sheet_date__lte=default_window_end)

    context = {
        "daily_reports": daily_reports,
        "account_reports": account_reports,
        "branches": branches,
        "selected_branch_id": int(selected_branch_id) if selected_branch_id else None,
        "selected_date": selected_date_raw,
        "default_window_active": not bool(selected_date),
        "default_window_start": default_window_start,
        "default_window_end": default_window_end,
        "total_daily_reports": DailyStock.objects.count(),
        "total_account_reports": StockSheet.objects.count(),
    }
    return render(request, "reports_center/reports_dashboard.html", context)
