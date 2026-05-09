from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from user_access.constants import STOCK_REGISTRAR_ROLE
from user_access.permissions import role_required

from .forms import StockTransactionForm
from .services import get_stock_register_context, process_stock_transaction, resolve_branch_for_user


@role_required(STOCK_REGISTRAR_ROLE)
def stock_register_view(request):
    branch_id = request.POST.get("branch") if request.method == "POST" else request.GET.get("branch")
    branches, branch = resolve_branch_for_user(request.user, branch_id)
    if request.method == "POST":
        form = StockTransactionForm(request.POST, branch=branch)
        if form.is_valid():
            try:
                transaction = process_stock_transaction(
                    item_id=form.cleaned_data["item"].pk,
                    transaction_type=form.cleaned_data["transaction_type"],
                    quantity=form.cleaned_data["quantity"],
                    user=request.user,
                    rate=form.cleaned_data.get("rate"),
                    received_from=form.cleaned_data.get("received_from"),
                    issued_to=form.cleaned_data.get("issued_to"),
                    notes=form.cleaned_data.get("notes", ""),
                )
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, f"Stock movement saved. New balance: {transaction.balance_after} {transaction.item.unit}.")
                return redirect(f"{request.path}?branch={branch.pk}")
    else:
        form = StockTransactionForm(branch=branch)

    context = get_stock_register_context(request.user, branch.pk)
    context["branches"] = branches
    context["branch"] = branch
    context["form"] = form
    return render(request, "stock_register/stock_register.html", context)
