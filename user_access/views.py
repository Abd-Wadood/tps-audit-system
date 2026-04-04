from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date

from stock_control.sheet_logic import ensure_seed_data
from stocks.models import Branch, StockSheet
from .access import get_branch_aware_url, get_user_branch_id
from .constants import ACCOUNTING_ROLE, REPORT_ROLE, STOCK_ROLE
from .forms import OwnerUserCreateForm, OwnerUserRoleForm, SignInForm
from .models import UserWorkspace
from .permissions import role_flags


def parse_non_negative_decimal(value):
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")
    return max(parsed, Decimal("0"))


def parse_optional_int(value):
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


class WorkspaceLoginView(LoginView):
    template_name = "user_access/login.html"
    authentication_form = SignInForm

    def get_success_url(self):
        flags = role_flags(self.request.user)
        if flags["is_superuser"]:
            return reverse("user_access:workspace_home")
        if flags["is_report_user"]:
            return reverse("reports_center:dashboard")
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
        1 for allowed in [flags["is_stock_user"], flags["is_accounting_user"], flags["is_report_user"], flags["is_superuser"]] if allowed
    )
    if not flags["is_superuser"] and role_count == 1:
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
            "has_any_workspace_access": flags["is_superuser"] or flags["is_stock_user"] or flags["is_accounting_user"] or flags["is_report_user"],
        },
    )


def owner_user_management_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_superuser:
        return redirect("user_access:workspace_home")

    ensure_seed_data()
    create_form = OwnerUserCreateForm()
    if request.method == "POST":
        action = request.POST.get("action")
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
                return redirect("user_access:user_management")
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
                return redirect("user_access:user_management")
        elif action == "delete_user":
            managed_user = get_object_or_404(User, pk=request.POST.get("user_id"))
            if managed_user.is_superuser:
                messages.info(request, "Owner/Admin users cannot be deleted from this screen.")
            else:
                username = managed_user.username
                managed_user.delete()
                messages.success(request, f"Deleted user {username}.")
            return redirect("user_access:user_management")

    managed_users = User.objects.select_related("workspace__branch").order_by("username")
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
    chicken_from_raw = request.GET.get("chicken_from", "").strip()
    chicken_to_raw = request.GET.get("chicken_to", "").strip()
    chicken_branch_id = request.GET.get("chicken_branch", "").strip()
    food_panda_from_raw = request.GET.get("food_panda_from", "").strip()
    food_panda_to_raw = request.GET.get("food_panda_to", "").strip()
    food_panda_branch_id = request.GET.get("food_panda_branch", "").strip()
    sheikh_bill_from_raw = request.GET.get("sheikh_bill_from", "").strip()
    sheikh_bill_to_raw = request.GET.get("sheikh_bill_to", "").strip()
    sheikh_bill_branch_id = request.GET.get("sheikh_bill_branch", "").strip()

    balance_from = parse_date(balance_from_raw) if balance_from_raw else None
    balance_to = parse_date(balance_to_raw) if balance_to_raw else None
    chicken_from = parse_date(chicken_from_raw) if chicken_from_raw else None
    chicken_to = parse_date(chicken_to_raw) if chicken_to_raw else None
    food_panda_from = parse_date(food_panda_from_raw) if food_panda_from_raw else None
    food_panda_to = parse_date(food_panda_to_raw) if food_panda_to_raw else None
    sheikh_bill_from = parse_date(sheikh_bill_from_raw) if sheikh_bill_from_raw else None
    sheikh_bill_to = parse_date(sheikh_bill_to_raw) if sheikh_bill_to_raw else None

    balance_summaries = StockSheet.objects.none()
    total_balance = Decimal("0")
    total_chicken_purchase = Decimal("0")
    total_food_panda = Decimal("0")
    total_sheikh_bill_purchase = Decimal("0")
    chicken_summaries = StockSheet.objects.none()
    food_panda_summaries = StockSheet.objects.none()
    sheikh_bill_summaries = StockSheet.objects.none()
    overall_summary_count = StockSheet.objects.count()

    if balance_from and balance_to:
        balance_summaries = (
            StockSheet.objects.select_related("branch", "created_by")
            .filter(sheet_date__gte=balance_from, sheet_date__lte=balance_to)
            .order_by("sheet_date", "branch__name", "reference_number")
        )
        if balance_branch_id:
            balance_summaries = balance_summaries.filter(branch_id=balance_branch_id)
        for summary in balance_summaries:
            total_balance += parse_non_negative_decimal(summary.balance)

    if chicken_from and chicken_to:
        chicken_summaries = (
            StockSheet.objects.select_related("branch", "created_by")
            .filter(sheet_date__gte=chicken_from, sheet_date__lte=chicken_to)
            .order_by("sheet_date", "branch__name", "reference_number")
        )
        if chicken_branch_id:
            chicken_summaries = chicken_summaries.filter(branch_id=chicken_branch_id)
        for summary in chicken_summaries:
            total_chicken_purchase += parse_non_negative_decimal(summary.market_purchases.get("values", {}).get("chicken", "0"))

    if food_panda_from and food_panda_to:
        food_panda_summaries = (
            StockSheet.objects.select_related("branch", "created_by")
            .filter(sheet_date__gte=food_panda_from, sheet_date__lte=food_panda_to)
            .order_by("sheet_date", "branch__name", "reference_number")
        )
        if food_panda_branch_id:
            food_panda_summaries = food_panda_summaries.filter(branch_id=food_panda_branch_id)
        for summary in food_panda_summaries:
            total_food_panda += parse_non_negative_decimal(summary.total_summary.get("values", {}).get("food_panda", "0"))

    if sheikh_bill_from and sheikh_bill_to:
        sheikh_bill_summaries = (
            StockSheet.objects.select_related("branch", "created_by")
            .filter(sheet_date__gte=sheikh_bill_from, sheet_date__lte=sheikh_bill_to)
            .order_by("sheet_date", "branch__name", "reference_number")
        )
        if sheikh_bill_branch_id:
            sheikh_bill_summaries = sheikh_bill_summaries.filter(branch_id=sheikh_bill_branch_id)
        for summary in sheikh_bill_summaries:
            total_sheikh_bill_purchase += parse_non_negative_decimal(summary.market_purchases.get("values", {}).get("sheikh_bill", "0"))

    return render(
        request,
        "user_access/balance_overview.html",
        {
            "branches": branches,
            "balance_from": balance_from_raw,
            "balance_to": balance_to_raw,
            "balance_branch_id": parse_optional_int(balance_branch_id),
            "chicken_from": chicken_from_raw,
            "chicken_to": chicken_to_raw,
            "chicken_branch_id": parse_optional_int(chicken_branch_id),
            "food_panda_from": food_panda_from_raw,
            "food_panda_to": food_panda_to_raw,
            "food_panda_branch_id": parse_optional_int(food_panda_branch_id),
            "sheikh_bill_from": sheikh_bill_from_raw,
            "sheikh_bill_to": sheikh_bill_to_raw,
            "sheikh_bill_branch_id": parse_optional_int(sheikh_bill_branch_id),
            "balance_summaries": balance_summaries,
            "chicken_summaries": chicken_summaries,
            "food_panda_summaries": food_panda_summaries,
            "sheikh_bill_summaries": sheikh_bill_summaries,
            "total_balance": total_balance,
            "total_chicken_purchase": total_chicken_purchase,
            "total_food_panda": total_food_panda,
            "total_sheikh_bill_purchase": total_sheikh_bill_purchase,
            "overall_summary_count": overall_summary_count,
        },
    )
