from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render

from stocks.pdf import build_stock_sheet_pdf
from user_access.constants import ACCOUNTING_ROLE, REPORT_ROLE, STOCK_ROLE
from user_access.permissions import role_required

from .sheet_logic import coerce_int, resolve_sheet


@role_required(STOCK_ROLE)
def stock_sheet_view(request):
    if request.method == "POST":
        context = resolve_sheet(request.POST.get("branch"), request.POST.get("date"))
        entries_by_id = {entry.id: entry for entry in context["entries"]}
        was_existing_record = not context["daily_stock_created"]

        with transaction.atomic():
            daily_stock = context["daily_stock"]
            if was_existing_record:
                daily_stock.revision_count += 1
            daily_stock.total_orders = coerce_int(request.POST.get("total_orders"))
            daily_stock.shop_orders = coerce_int(request.POST.get("shop_orders"))
            daily_stock.food_panda_orders = coerce_int(request.POST.get("food_panda_orders"))
            daily_stock.last_updated_by = request.user
            daily_stock.save()

            for entry_id, entry in entries_by_id.items():
                entry.opening = coerce_int(request.POST.get(f"opening_{entry_id}"))
                entry.received = coerce_int(request.POST.get(f"received_{entry_id}"))
                entry.stock = entry.opening + entry.received
                entry.sale = coerce_int(request.POST.get(f"sale_{entry_id}"))
                entry.exchange = coerce_int(request.POST.get(f"exchange_{entry_id}"))
                entry.in_hand = entry.stock - entry.sale
                entry.remaining_value = coerce_int(request.POST.get(f"remaining_{entry_id}"))
                entry.save(update_fields=["opening", "received", "stock", "sale", "exchange", "in_hand", "remaining_value"])

        messages.success(request, "Daily stock sheet saved for accounting review.")
        return redirect(f"{request.path}?branch={context['branch'].pk}&date={context['selected_date'].isoformat()}")

    context = resolve_sheet(request.GET.get("branch"), request.GET.get("date"))
    context.update(
        {
            "page_title": "Daily Stock Sheet",
            "page_eyebrow": "Stock Control",
            "page_description": "The stock user saves opening, received, sale, exchange, and remaining. InHand is calculated from stock minus sale.",
            "submit_label": "Save For Accounting",
            "show_pdf_button": False,
            "editable_totals": True,
            "editable_fields": {"opening", "received", "sale", "exchange", "remaining"},
        }
    )
    return render(request, "stock_control/daily_stock_sheet.html", context)


@role_required(ACCOUNTING_ROLE, REPORT_ROLE)
def stock_sheet_pdf_view(request):
    context = resolve_sheet(request.GET.get("branch"), request.GET.get("date"))
    daily_stock = context["daily_stock"]
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="daily-stock-{daily_stock.branch.name}-{daily_stock.date:%Y%m%d}.pdf"'
    build_stock_sheet_pdf(daily_stock, context["entries"], context["totals"], response)
    return response
