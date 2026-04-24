import json

from django.contrib import messages

from stock_control.sheet_logic import ensure_seed_data
from stocks.models import StockSheet
from user_access.access import get_accessible_branches, get_user_branch_id

from .account_summary_calculations import SECTION_CONFIG, calculate_totals, extract_section, parse_decimal


REQUIRED_SALE_FIELDS = {
    "system_sale": "System Sale",
    "counter_counter_sale": "Counter Sale",
    "counter_direct_sale": "Direct Sale",
}


def build_reference_number(selected_date, selected_branch):
    branch_token = selected_branch.pk if selected_branch else "NA"
    return f"ACC-{selected_date:%Y%m%d}-B{branch_token}"


def get_accounting_branch_options(user, selected_branch_id=None):
    ensure_seed_data()
    branches = get_accessible_branches(user)
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
    reference_number = (
        existing_sheet.reference_number
        if existing_sheet and existing_sheet.reference_number
        else build_reference_number(selected_date, selected_branch)
    )
    sections = {}
    for section_key, config in SECTION_CONFIG.items():
        section_data = get_section_data(existing_sheet, section_key)
        fields = []
        for field_key, label in config["fields"]:
            default_value = "0"
            if not existing_sheet and section_key == "counter" and field_key in {"counter_sale", "direct_sale"}:
                default_value = ""
            fields.append(
                {
                    "key": field_key,
                    "label": label,
                    "value": section_data.get("values", {}).get(field_key, default_value),
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
        "reference_number_value": reference_number,
        "system_sale_value": existing_sheet.system_sale if existing_sheet else "",
        "sections": sections,
        "loaded_summary": existing_sheet,
        "loaded_branch_name": selected_branch.name if selected_branch else "",
        "loaded_date": selected_date.isoformat(),
    }


def validate_required_summary_fields(post_data):
    field_errors = {}
    for field_name, label in REQUIRED_SALE_FIELDS.items():
        if not str(post_data.get(field_name, "")).strip():
            field_errors[field_name] = f"{label} is required."
    return field_errors


def save_account_summary(request, selected_branch, selected_date, existing_sheet=None):
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
    if not existing_sheet or not sheet.reference_number:
        sheet.reference_number = build_reference_number(selected_date, selected_branch)
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
    return sheet


def get_selected_accounting_branch_id(user, request):
    assigned_branch_id = None if user.is_superuser else get_user_branch_id(user)
    return assigned_branch_id or request.POST.get("branch") or request.GET.get("branch")
