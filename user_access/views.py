from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date

from stock_register.models import Item as StockRegisterItem
from stock_control.sheet_logic import ensure_seed_data
from accounting_app.account_summary_calculations import SECTION_CONFIG
from stocks.models import Branch, Item, StockSheet
from .access import get_branch_aware_url, get_user_branch_id
from .constants import ACCOUNTING_ROLE, REPORT_ROLE, STOCK_ROLE
from .forms import OwnerStockItemForm, OwnerStockRegisterItemForm, OwnerUserCreateForm, OwnerUserRoleForm, SignInForm
from .models import UserWorkspace
from .permissions import role_flags
from .pdf import build_accounting_range_pdf


def parse_non_negative_decimal(value):
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")
    return max(parsed, Decimal("0"))


def parse_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def parse_optional_int(value):
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def get_summary_range(branch_id, date_from, date_to):
    summaries = (
        StockSheet.objects.select_related("branch", "created_by")
        .filter(sheet_date__gte=date_from, sheet_date__lte=date_to)
        .order_by("sheet_date", "branch__name", "reference_number")
    )
    if branch_id:
        summaries = summaries.filter(branch_id=branch_id)
    return summaries


def sum_summary_values(summaries, value_getter, *, clamp_non_negative=False):
    total = Decimal("0")
    parser = parse_non_negative_decimal if clamp_non_negative else parse_decimal
    for summary in summaries:
        total += parser(value_getter(summary))
    return total


def get_summary_total(summary, key, fallback=None):
    value = summary.totals.get(key)
    if value in (None, "") and fallback is not None:
        value = fallback(summary)
    return value


SECTION_DATA_FIELDS = {
    "local": "local_purchases",
    "market": "market_purchases",
    "counter": "counter_summary",
    "total": "total_summary",
}

REPORT_CHOICES = [
    ("sales", "Sales & Purchase Totals"),
    ("local", "Local Purchases"),
    ("market", "Market Purchase"),
    ("counter", "Counter Summary"),
    ("total", "Total Summary Purchases"),
]


def build_section_breakdown(summaries, section_name):
    config = SECTION_CONFIG[section_name]
    breakdown = [{"key": key, "label": label, "total": Decimal("0")} for key, label in config["fields"]]
    lookup = {entry["key"]: entry for entry in breakdown}
    custom_totals = {}

    for summary in summaries:
        section_data = getattr(summary, SECTION_DATA_FIELDS[section_name]) or {}
        values = section_data.get("values", {})
        for key in lookup:
            lookup[key]["total"] += parse_non_negative_decimal(values.get(key, "0"))
        for row in section_data.get("custom_rows", []):
            label = str(row.get("label", "")).strip()
            if not label:
                continue
            custom_totals[label] = custom_totals.get(label, Decimal("0")) + parse_non_negative_decimal(row.get("value", "0"))

    for label, total in custom_totals.items():
        breakdown.append({"key": f"custom_{label}", "label": label, "total": total})

    return breakdown


def build_sales_breakdown(summaries):
    return [
        {
            "key": "system_sale",
            "label": "System Sale",
            "total": sum_summary_values(
                summaries,
                lambda summary: get_summary_total(summary, "system_sale", lambda sheet: sheet.system_sale),
            ),
        },
        {
            "key": "counter_sale",
            "label": "Counter Sale",
            "total": sum_summary_values(
                summaries,
                lambda summary: get_summary_total(
                    summary,
                    "counter_sale",
                    lambda sheet: sheet.counter_summary.get("values", {}).get("counter_sale", "0"),
                ),
            ),
        },
        {
            "key": "total_sale",
            "label": "Total Sale",
            "total": sum_summary_values(
                summaries,
                lambda summary: get_summary_total(summary, "total_sale", lambda sheet: sheet.total_sale),
            ),
        },
        {
            "key": "total_purchase",
            "label": "Total Purchase",
            "total": sum_summary_values(
                summaries,
                lambda summary: get_summary_total(summary, "total_purchase", lambda sheet: sheet.total_purchase),
            ),
        },
    ]


def build_accounting_range_report(summaries, report_type):
    if report_type == "sales":
        breakdown = build_sales_breakdown(summaries)
        return {
            "title": "Sales & Purchase Totals",
            "total_label": "Total Purchase",
            "breakdown": breakdown,
            "total": next((entry["total"] for entry in breakdown if entry["key"] == "total_purchase"), Decimal("0")),
        }

    config = SECTION_CONFIG[report_type]
    breakdown = build_section_breakdown(summaries, report_type)
    return {
        "title": config["title"],
        "total_label": config["total_label"],
        "breakdown": breakdown,
        "total": sum(entry["total"] for entry in breakdown),
    }


def build_full_accounting_range_report(summaries):
    sales_breakdown = build_sales_breakdown(summaries)
    sales = {entry["key"]: entry["total"] for entry in sales_breakdown}
    return {
        "summary_count": len(summaries),
        "balance": sum_summary_values(summaries, lambda summary: summary.balance),
        "sales": sales,
        "sections": [
            build_accounting_range_report(summaries, "local"),
            build_accounting_range_report(summaries, "market"),
            build_accounting_range_report(summaries, "counter"),
            build_accounting_range_report(summaries, "total"),
        ],
    }


def get_branch_label(branch_id):
    if not branch_id:
        return "All Branches"
    branch = Branch.objects.filter(pk=branch_id).first()
    return branch.name if branch else "Selected Branch"


class WorkspaceLoginView(LoginView):
    template_name = "user_access/login.html"
    authentication_form = SignInForm

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session.set_expiry(60 * 60 * 24)
        return response

    def get_success_url(self):
        flags = role_flags(self.request.user)
        if flags["is_superuser"]:
            return reverse("user_access:workspace_home")
        if flags["is_report_user"]:
            return reverse("reports_center:dashboard")
        if flags["is_stock_registrar"] and not (flags["is_stock_user"] or flags["is_accounting_user"] or flags["is_report_user"]):
            return get_branch_aware_url("stock_register:register", self.request.user)
        if flags["is_stock_user"] and not flags["is_accounting_user"]:
            return get_branch_aware_url("stock_control:stock_sheet", self.request.user)
        if flags["is_accounting_user"] and not flags["is_stock_user"]:
            return get_branch_aware_url("accounting_app:summary_create", self.request.user)
        return reverse("user_access:workspace_home")

def signup_view(request):
    messages.info(request, "Accounts are created by the owner or admin from the admin panel.")
    return redirect("login")


def workspace_home(request):
    if not request.user.is_authenticated:
        return redirect("login")

    flags = role_flags(request.user)
    role_count = sum(
        1
        for allowed in [
            flags["is_stock_user"],
            flags["is_accounting_user"],
            flags["is_report_user"],
            flags["is_stock_registrar"],
            flags["is_superuser"],
        ]
        if allowed
    )
    if not flags["is_superuser"] and role_count == 1:
        if flags["is_stock_registrar"]:
            return redirect(get_branch_aware_url("stock_register:register", request.user))
        if flags["is_stock_user"]:
            return redirect(get_branch_aware_url("stock_control:stock_sheet", request.user))
        if flags["is_accounting_user"]:
            return redirect(get_branch_aware_url("accounting_app:summary_create", request.user))
        if flags["is_report_user"]:
            return redirect("reports_center:dashboard")

    return render(
        request,
        "user_access/workspace_home.html",
        {
            "flags": flags,
            "has_any_workspace_access": (
                flags["is_superuser"]
                or flags["is_stock_user"]
                or flags["is_accounting_user"]
                or flags["is_report_user"]
                or flags["is_stock_registrar"]
            ),
        },
    )


def owner_user_management_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_superuser:
        return redirect("user_access:workspace_home")

    ensure_seed_data()
    create_form = OwnerUserCreateForm()
    stock_item_form = OwnerStockItemForm()
    stock_register_item_form = OwnerStockRegisterItemForm()
    stock_item_query = request.GET.get("item_query", "").strip()
    stock_register_item_query = request.GET.get("register_item_query", "").strip()
    if request.method == "POST":
        action = request.POST.get("action")
        redirect_url = reverse("user_access:user_management")
        redirect_params = []
        redirect_item_query = request.POST.get("item_query", "").strip()
        redirect_register_item_query = request.POST.get("register_item_query", "").strip()
        if redirect_item_query:
            redirect_params.append(f"item_query={redirect_item_query}")
        if redirect_register_item_query:
            redirect_params.append(f"register_item_query={redirect_register_item_query}")
        if redirect_params:
            redirect_url = f"{redirect_url}?{'&'.join(redirect_params)}"
        if action == "create_user":
            create_form = OwnerUserCreateForm(request.POST)
            if create_form.is_valid():
                role = create_form.cleaned_data.pop("role")
                branch = create_form.cleaned_data.pop("branch")
                password = create_form.cleaned_data.pop("password")
                user = User.objects.create(**create_form.cleaned_data, is_active=True)
                user.set_password(password)
                user.save()
                user.groups.set([Group.objects.get(name=role)])
                UserWorkspace.objects.update_or_create(user=user, defaults={"branch": branch})
                messages.success(request, f"User {user.username} created successfully.")
                return redirect(redirect_url)
        elif action == "update_role":
            role_form = OwnerUserRoleForm(request.POST)
            if role_form.is_valid():
                managed_user = get_object_or_404(User, pk=role_form.cleaned_data["user_id"])
                if managed_user.is_superuser:
                    messages.info(request, "Owner/Admin roles stay managed by the system.")
                else:
                    managed_user.groups.set([Group.objects.get(name=role_form.cleaned_data["role"])])
                    UserWorkspace.objects.update_or_create(
                        user=managed_user,
                        defaults={"branch": role_form.cleaned_data["branch"]},
                    )
                    messages.success(request, f"Updated role for {managed_user.username}.")
                return redirect(redirect_url)
        elif action == "delete_user":
            managed_user = get_object_or_404(User, pk=request.POST.get("user_id"))
            if managed_user.is_superuser:
                messages.info(request, "Owner/Admin users cannot be deleted from this screen.")
            else:
                username = managed_user.username
                managed_user.delete()
                messages.success(request, f"Deleted user {username}.")
            return redirect(redirect_url)
        elif action == "create_item":
            stock_item_form = OwnerStockItemForm(request.POST)
            if stock_item_form.is_valid():
                item = stock_item_form.save()
                messages.success(request, f"Stock item {item.name} added successfully.")
                return redirect(redirect_url)
        elif action == "delete_item":
            item = get_object_or_404(Item, pk=request.POST.get("item_id"))
            item_name = item.name
            item.delete()
            messages.success(request, f"Stock item {item_name} removed successfully.")
            return redirect(redirect_url)
        elif action == "create_register_item":
            stock_register_item_form = OwnerStockRegisterItemForm(request.POST)
            if stock_register_item_form.is_valid():
                item = stock_register_item_form.save()
                messages.success(request, f"Stock register item {item.name} added successfully.")
                return redirect(redirect_url)
        elif action == "delete_register_item":
            item = get_object_or_404(StockRegisterItem, pk=request.POST.get("register_item_id"))
            item_name = item.name
            try:
                item.delete()
            except ProtectedError:
                messages.error(request, f"Stock register item {item_name} has transaction history and cannot be removed.")
            else:
                messages.success(request, f"Stock register item {item_name} removed successfully.")
            return redirect(redirect_url)

    managed_users = User.objects.select_related("workspace__branch").order_by("username")
    stock_items = Item.objects.none()
    if stock_item_query:
        stock_items = Item.objects.filter(name__icontains=stock_item_query).order_by("name")
    stock_register_items = StockRegisterItem.objects.none()
    if stock_register_item_query:
        stock_register_items = StockRegisterItem.objects.select_related("branch").filter(name__icontains=stock_register_item_query).order_by("branch__name", "name")
    user_role_forms = []
    for managed_user in managed_users:
        initial_role = managed_user.groups.values_list("name", flat=True).first() or STOCK_ROLE
        user_role_forms.append(
            {
                "managed_user": managed_user,
                "form": OwnerUserRoleForm(
                    initial={
                        "user_id": managed_user.id,
                        "role": initial_role,
                        "branch": get_user_branch_id(managed_user),
                    }
                ),
            }
        )

    return render(
        request,
        "user_access/user_management.html",
        {
            "create_form": create_form,
            "stock_item_form": stock_item_form,
            "stock_register_item_form": stock_register_item_form,
            "stock_items": stock_items,
            "stock_register_items": stock_register_items,
            "stock_item_query": stock_item_query,
            "stock_register_item_query": stock_register_item_query,
            "user_role_forms": user_role_forms,
        },
    )


def owner_balance_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_superuser:
        return redirect("user_access:workspace_home")

    branches = Branch.objects.order_by("name")
    balance_from_raw = request.GET.get("balance_from", "").strip()
    balance_to_raw = request.GET.get("balance_to", "").strip()
    balance_branch_id = request.GET.get("balance_branch", "").strip()
    report_type = request.GET.get("report_type", "sales").strip()
    report_from_raw = request.GET.get("report_from", "").strip()
    report_to_raw = request.GET.get("report_to", "").strip()
    report_branch_id = request.GET.get("report_branch", "").strip()

    balance_from = parse_date(balance_from_raw) if balance_from_raw else None
    balance_to = parse_date(balance_to_raw) if balance_to_raw else None
    report_from = parse_date(report_from_raw) if report_from_raw else None
    report_to = parse_date(report_to_raw) if report_to_raw else None

    balance_summaries = StockSheet.objects.none()
    total_balance = Decimal("0")
    if report_type not in dict(REPORT_CHOICES):
        report_type = "sales"
    report_summaries = StockSheet.objects.none()
    accounting_range_report = build_accounting_range_report(report_summaries, report_type)
    overall_summary_count = StockSheet.objects.count()

    if balance_from and balance_to:
        balance_summaries = get_summary_range(
            balance_branch_id,
            balance_from,
            balance_to,
        )
        total_balance = sum_summary_values(balance_summaries, lambda summary: summary.balance)

    if report_from and report_to:
        report_summaries = get_summary_range(
            report_branch_id,
            report_from,
            report_to,
        )
        accounting_range_report = build_accounting_range_report(report_summaries, report_type)

    return render(
        request,
        "user_access/balance_overview.html",
        {
            "branches": branches,
            "balance_from": balance_from_raw,
            "balance_to": balance_to_raw,
            "balance_branch_id": parse_optional_int(balance_branch_id),
            "report_choices": REPORT_CHOICES,
            "report_type": report_type,
            "report_from": report_from_raw,
            "report_to": report_to_raw,
            "report_branch_id": parse_optional_int(report_branch_id),
            "balance_summaries": balance_summaries,
            "report_summaries": report_summaries,
            "accounting_range_report": accounting_range_report,
            "total_balance": total_balance,
            "overall_summary_count": overall_summary_count,
        },
    )


def accounting_range_pdf_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_superuser:
        return redirect("user_access:workspace_home")

    report_from_raw = request.GET.get("report_from", "").strip()
    report_to_raw = request.GET.get("report_to", "").strip()
    report_branch_id = request.GET.get("report_branch", "").strip()
    report_from = parse_date(report_from_raw) if report_from_raw else None
    report_to = parse_date(report_to_raw) if report_to_raw else None

    if not report_from or not report_to:
        messages.info(request, "Choose a from date and to date before downloading the accounting PDF.")
        return redirect(f"{reverse('user_access:balance_overview')}#accounting-report-section")

    summaries = get_summary_range(report_branch_id, report_from, report_to)
    report = build_full_accounting_range_report(summaries)
    branch_label = get_branch_label(report_branch_id)
    generated_by = request.user.get_full_name() or request.user.username

    response = HttpResponse(content_type="application/pdf")
    filename_branch = branch_label.lower().replace(" ", "-")
    response["Content-Disposition"] = (
        f'attachment; filename="accounting-range-{filename_branch}-{report_from:%Y%m%d}-{report_to:%Y%m%d}.pdf"'
    )
    build_accounting_range_pdf(
        buffer=response,
        report=report,
        branch_label=branch_label,
        date_from=report_from,
        date_to=report_to,
        generated_by=generated_by,
    )
    return response
