from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

from stock_control.services import (
    get_stock_sheet_context,
    prepare_accounting_review_entries,
    save_accounting_review_entries,
    save_stock_totals,
)
from stock_control.sheet_logic import ensure_seed_data, parse_selected_date
from stocks.models import Branch, StockSheet
from stocks.pdf import build_stock_sheet_pdf
from user_access.constants import ACCOUNTING_ROLE, REPORT_ROLE
from user_access.permissions import role_required

from .account_summary_calculations import SECTION_CONFIG
from .services import (
    build_summary_form_context,
    get_accounting_branch_options,
    get_existing_summary,
    get_selected_accounting_branch_id,
    save_account_summary,
)


@role_required(ACCOUNTING_ROLE, REPORT_ROLE)
def summary_list_view(request):
    ensure_seed_data()
    sheets = StockSheet.objects.select_related("branch", "created_by").order_by("-sheet_date", "branch__name", "-created_at")
    branches = Branch.objects.order_by("name")

    selected_branch_id = request.GET.get("branch")
    if selected_branch_id:
        sheets = sheets.filter(branch_id=selected_branch_id)

    selected_date_raw = request.GET.get("sheet_date", "").strip()
    if selected_date_raw:
        selected_date = parse_date(selected_date_raw)
        if selected_date:
            sheets = sheets.filter(sheet_date=selected_date)

    context = {
        "sheets": sheets,
        "branches": branches,
        "selected_branch_id": int(selected_branch_id) if selected_branch_id else None,
        "selected_sheet_date": selected_date_raw,
    }
    return render(request, "accounting_app/account_summary_list.html", context)


@role_required(ACCOUNTING_ROLE)
def summary_create_view(request):
    selected_branch_id = get_selected_accounting_branch_id(request.user, request)
    branches, selected_branch = get_accounting_branch_options(request.user, selected_branch_id)
    selected_date = parse_selected_date(request.POST.get("sheet_date") or request.GET.get("sheet_date"))
    existing_sheet = get_existing_summary(selected_branch, selected_date)

    if request.method == "POST":
        sheet = save_account_summary(request, selected_branch, selected_date, existing_sheet=existing_sheet)
        return redirect("accounting_app:summary_detail", pk=sheet.pk)

    context = {
        "section_config": SECTION_CONFIG,
        "default_date": selected_date.isoformat(),
        "branches": branches,
        "selected_branch_id": selected_branch.pk if selected_branch else None,
        **build_summary_form_context(selected_branch, selected_date, existing_sheet),
    }
    return render(request, "accounting_app/account_summary_form.html", context)


@role_required(ACCOUNTING_ROLE, REPORT_ROLE)
def summary_detail_view(request, pk):
    sheet = get_object_or_404(StockSheet.objects.select_related("branch", "created_by"), pk=pk)
    display_sections = []
    data_map = {
        "local": sheet.local_purchases,
        "market": sheet.market_purchases,
        "counter": sheet.counter_summary,
        "total": sheet.total_summary,
    }
    for section_key, config in SECTION_CONFIG.items():
        section_data = data_map[section_key]
        rows = []
        for field_key, label in config["fields"]:
            rows.append({"label": label, "value": section_data.get("values", {}).get(field_key, "0")})
        for row in section_data.get("custom_rows", []):
            rows.append({"label": row.get("label", "Custom"), "value": row.get("value", "0")})
        display_sections.append(
            {
                "title": config["title"],
                "total_label": config["total_label"],
                "total_value": sheet.totals.get(config["total_key"], "0"),
                "rows": rows,
            }
        )
    return render(request, "accounting_app/account_summary_detail.html", {"sheet": sheet, "display_sections": display_sections})


@role_required(ACCOUNTING_ROLE, REPORT_ROLE)
def summary_pdf_view(request, pk):
    sheet = get_object_or_404(StockSheet.objects.select_related("branch", "created_by"), pk=pk)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="account-summary-{sheet.reference_number}.pdf"'
    build_stock_sheet_pdf(sheet, response)
    return response


@role_required(ACCOUNTING_ROLE, REPORT_ROLE)
def stock_review_view(request):
    if request.method == "POST":
        context = get_stock_sheet_context(request.user, request.POST.get("branch"), request.POST.get("date"))
        entries_by_id = {entry.id: entry for entry in context["entries"]}
        was_existing_record = not context["daily_stock_created"]

        daily_stock = context["daily_stock"]
        if was_existing_record:
            daily_stock.revision_count += 1
        save_stock_totals(daily_stock, request.POST, request.user)
        save_accounting_review_entries(entries_by_id, request.POST)

        messages.success(request, "Stock sheet finalized for PDF generation.")
        return redirect(f"{request.path}?branch={context['branch'].pk}&date={context['selected_date'].isoformat()}")

    context = get_stock_sheet_context(request.user, request.GET.get("branch"), request.GET.get("date"))
    prepare_accounting_review_entries(context["entries"])
    context.update(
        {
            "page_title": "Accounting Stock Review",
            "page_eyebrow": "Accounting",
            "page_description": "Review the saved stock sheet, add cancelled and ready values, then generate the final PDF. InHand is calculated from stock minus sale.",
            "submit_label": "Save Accounting Review",
            "show_pdf_button": True,
            "editable_totals": True,
            "editable_fields": {"cancelled", "ready"},
            "ready_adds_to_remaining": True,
        }
    )
    return render(request, "stock_control/daily_stock_sheet.html", context)
