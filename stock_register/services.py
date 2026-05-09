from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404

from stocks.models import Branch
from user_access.access import get_accessible_branches, get_user_branch_id
from .models import Item, StockTransaction


def coerce_quantity(value):
    try:
        parsed = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("Enter a valid quantity.")

    if parsed <= 0:
        raise ValidationError("Quantity must be greater than zero.")
    return parsed


def coerce_optional_rate(value):
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("Enter a valid rate.")

    if parsed < 0:
        raise ValidationError("Rate cannot be negative.")
    return parsed


def calculate_total_amount(quantity, rate):
    if rate is None:
        return Decimal("0.00")
    return (quantity * rate).quantize(Decimal("0.01"))


def process_stock_transaction(
    item_id,
    transaction_type,
    quantity,
    user,
    rate=None,
    received_from=None,
    issued_to=None,
    notes="",
):
    """Record one locked stock movement and update the item's running balance."""
    quantity = coerce_quantity(quantity)
    rate = coerce_optional_rate(rate)

    if transaction_type not in {StockTransaction.IN, StockTransaction.OUT}:
        raise ValidationError("Choose a valid stock action.")

    with transaction.atomic():
        item = Item.objects.select_for_update().get(pk=item_id)
        current_stock = item.current_stock

        if transaction_type == StockTransaction.IN:
            new_stock = current_stock + quantity
        else:
            if quantity > current_stock:
                raise ValidationError(
                    f"Cannot issue {quantity} {item.unit}; only {current_stock} {item.unit} available."
                )
            new_stock = current_stock - quantity

        movement = StockTransaction.objects.create(
            item=item,
            transaction_type=transaction_type,
            quantity=quantity,
            rate=rate,
            total_amount=calculate_total_amount(quantity, rate),
            balance_after=new_stock,
            received_from=(received_from or "").strip(),
            issued_to=(issued_to or "").strip(),
            notes=(notes or "").strip(),
            created_by=user if getattr(user, "is_authenticated", False) else None,
        )
        item.current_stock = new_stock
        item.save(update_fields=["current_stock"])

    return movement


def resolve_branch_for_user(user, branch_id=None):
    branches = get_accessible_branches(user)
    branch = branches.filter(pk=branch_id).first() if branch_id else None
    default_branch_id = None if user.is_superuser else get_user_branch_id(user)
    if branch is None and default_branch_id:
        branch = branches.filter(pk=default_branch_id).first()
    if branch is None:
        branch = branches.first()
    if branch is None:
        branch = get_object_or_404(Branch.objects.all(), pk=0)
    return branches, branch


def get_stock_register_context(user, branch_id=None):
    branches, branch = resolve_branch_for_user(user, branch_id)
    return {
        "branches": branches,
        "branch": branch,
        "items": Item.objects.filter(branch=branch).order_by("name"),
        "transactions": (
            StockTransaction.objects.select_related("item", "item__branch", "created_by")
            .filter(item__branch=branch)
            .order_by("-created_at")[:50]
        ),
    }
