import json
from datetime import date

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.utils import timezone

from stock_control.sheet_logic import coerce_int, ensure_seed_data, parse_selected_date, resolve_sheet
from stocks.models import Branch, StockSheet
from stocks.pdf import build_stock_sheet_pdf
from user_access.views import get_user_branch_id
from user_access.constants import ACCOUNTING_ROLE, REPORT_ROLE
from user_access.permissions import role_required

from .account_summary_calculations import SECTION_CONFIG, calculate_totals, extract_section, parse_decimal


def get_accounting_branch_options(selected_branch_id=None, branch_queryset=None):
    ensure_seed_data()
    branches = branch_queryset if branch_queryset is not None else Branch.objects.order_by("name")
    selected_branch = branches.filter(pk=selected_branch_id).first() or branches.first()
    return branches, selected_branch


def get_existing_summary(selected_branch, selected_date):
    if not selected_branch:
        return None

    return (
        StockSheet.objects.select_related("branch", "created_by")
        .filter(branch=selected_branch, sheet_date=selected_date)
        .order_by("-updated_at", "-created_at")
        .first()
    )


def get_section_data(sheet, section_key):
    if not sheet:
        return {"values": {}, "custom_rows": []}
    if section_key == "local":
        return sheet.local_purchases
    if section_key == "market":
        return sheet.market_purchases
    if section_key == "counter":
        return sheet.counter_summary
    return sheet.total_summary


def build_summary_form_context(selected_branch, selected_date, existing_sheet=None):
    sections = {}
    for section_key, config in SECTION_CONFIG.items():
        section_data = get_section_data(existing_sheet, section_key)
        fields = []
        for field_key, label in config["fields"]:
            fields.append(
                {
                    "key": field_key,
                    "label": label,
                    "value": section_data.get("values", {}).get(field_key, "0"),
                }
            )
        custom_rows = section_data.get("custom_rows", [])
        sections[section_key] = {
            "fields": fields,
            "custom_rows": custom_rows,
            "custom_rows_json": json.dumps(custom_rows),
        }

    return {
        "title_value": existing_sheet.title if existing_sheet else "Daily Account Summary",
        "reference_number_value": existing_sheet.reference_number if existing_sheet else "",
        "system_sale_value": existing_sheet.system_sale if existing_sheet else "0",
        "sections": sections,
        "loaded_summary": existing_sheet,
        "loaded_branch_name": selected_branch.name if selected_branch else "",
        "loaded_date": selected_date.isoformat(),
    }


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
    assigned_branch_id = None if request.user.is_superuser else get_user_branch_id(request.user)
    selected_branch_id = assigned_branch_id or request.POST.get("branch") or request.GET.get("branch")
    branch_queryset = Branch.objects.filter(pk=assigned_branch_id) if assigned_branch_id else None
    branches, selected_branch = get_accounting_branch_options(selected_branch_id, branch_queryset=branch_queryset)
    selected_date = parse_selected_date(request.POST.get("sheet_date") or request.GET.get("sheet_date"))
    existing_sheet = get_existing_summary(selected_branch, selected_date)

    if request.method == "POST":
        local_data = extract_section(request.POST, "local")
        market_data = extract_section(request.POST, "market")
        counter_data = extract_section(request.POST, "counter")
        total_data = extract_section(request.POST, "total")
        totals = calculate_totals(
            request.POST.get("system_sale", "0"),
            local_data,
            market_data,
            counter_data,
            total_data,
        )
        sheet = existing_sheet or StockSheet(branch=selected_branch, sheet_date=selected_date, created_by=request.user)
        if existing_sheet:
            sheet.revision_count += 1
        sheet.title = request.POST.get("title", "Account Summary").strip() or "Account Summary"
        submitted_reference = request.POST.get("reference_number", "").strip()
        if submitted_reference:
            sheet.reference_number = submitted_reference
        elif not sheet.reference_number:
            sheet.reference_number = f"ACC-{selected_date:%Y%m%d}-B{selected_branch.pk}"
        sheet.system_sale = parse_decimal(request.POST.get("system_sale", "0"), clamp_non_negative=True)
        sheet.local_purchases = local_data
        sheet.market_purchases = market_data
        sheet.counter_summary = counter_data
        sheet.total_summary = total_data
        sheet.totals = {key: str(value) for key, value in totals.items()}
        sheet.last_updated_by = request.user
        sheet.save()
        messages.success(
            request,
            "Account summary updated successfully." if existing_sheet else "Account summary saved successfully.",
        )
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
    assigned_branch_id = None if request.user.is_superuser else get_user_branch_id(request.user)
    branch_queryset = Branch.objects.filter(pk=assigned_branch_id) if assigned_branch_id else None
    if request.method == "POST":
        context = resolve_sheet(
            request.POST.get("branch"),
            request.POST.get("date"),
            branch_queryset=branch_queryset,
            default_branch_id=assigned_branch_id,
        )
        entries_by_id = {entry.id: entry for entry in context["entries"]}
        was_existing_record = not context["daily_stock_created"]

        daily_stock = context["daily_stock"]
        if was_existing_record:
            daily_stock.revision_count += 1
        daily_stock.total_orders = coerce_int(request.POST.get("total_orders"))
        daily_stock.shop_orders = coerce_int(request.POST.get("shop_orders"))
        daily_stock.food_panda_orders = coerce_int(request.POST.get("food_panda_orders"))
        daily_stock.last_updated_by = request.user
        daily_stock.save()

        for entry_id, entry in entries_by_id.items():
            entry.stock = entry.opening + entry.received
            entry.cancelled = coerce_int(request.POST.get(f"cancelled_{entry_id}"))
            entry.ready = coerce_int(request.POST.get(f"ready_{entry_id}"))
            entry.in_hand = entry.stock - entry.sale
            entry.remaining_value = coerce_int(request.POST.get(f"remaining_{entry_id}"))
            entry.save(update_fields=["stock", "cancelled", "ready", "in_hand", "remaining_value"])

        messages.success(request, "Stock sheet finalized for PDF generation.")
        return redirect(f"{request.path}?branch={context['branch'].pk}&date={context['selected_date'].isoformat()}")

    context = resolve_sheet(
        request.GET.get("branch"),
        request.GET.get("date"),
        branch_queryset=branch_queryset,
        default_branch_id=assigned_branch_id,
    )
    context.update(
        {
            "page_title": "Accounting Stock Review",
            "page_eyebrow": "Accounting",
            "page_description": "Review the saved stock sheet, add cancelled and ready values, then generate the final PDF. InHand is calculated from stock minus sale.",
            "submit_label": "Save Accounting Review",
            "show_pdf_button": True,
            "editable_totals": True,
            "editable_fields": {"cancelled", "ready"},
        }
    )
    return render(request, "stock_control/daily_stock_sheet.html", context)
