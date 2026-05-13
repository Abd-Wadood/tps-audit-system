from django import forms
from decimal import Decimal

from .models import Item, StockTransaction


class StockTransactionForm(forms.Form):
    item = forms.ModelChoiceField(queryset=Item.objects.none())
    transaction_type = forms.ChoiceField(choices=StockTransaction.TRANSACTION_TYPES)
    quantity = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    rate = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    received_from = forms.CharField(max_length=255, required=False)
    issued_to = forms.CharField(max_length=255, required=False)
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["item"].queryset = Item.objects.filter(branch=branch).order_by("name") if branch else Item.objects.none()
        self.fields["item"].empty_label = "Select item"
        self.fields["rate"].label = "Rate Per Unit"
        self.fields["quantity"].widget.attrs.update({"step": "0.01", "min": "0.01"})
        self.fields["rate"].widget.attrs.update({"step": "0.01", "min": "0"})
        self.fields["received_from"].widget.attrs.update({"placeholder": "Supplier name"})
        self.fields["issued_to"].widget.attrs.update({"placeholder": "Kitchen / department"})

    def clean(self):
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get("transaction_type")
        received_from = (cleaned_data.get("received_from") or "").strip()
        issued_to = (cleaned_data.get("issued_to") or "").strip()

        if transaction_type == StockTransaction.IN and not received_from:
            self.add_error("received_from", "Supplier name is required for stock in.")
        if transaction_type == StockTransaction.OUT and not issued_to:
            self.add_error("issued_to", "Kitchen or department name is required for stock out.")
        if transaction_type == StockTransaction.OUT:
            cleaned_data["rate"] = None
            cleaned_data["received_from"] = ""
        return cleaned_data


class StockRegisterItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ("branch", "name", "unit")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].label = "Register Item Name"
        self.fields["name"].widget.attrs.update({"placeholder": "Add stock register item"})
        self.fields["unit"].widget.attrs.update({"placeholder": "kg, pcs, liter"})
        self.fields["branch"].label = "Branch Store"
        self.fields["branch"].queryset = self.fields["branch"].queryset.order_by("name")

    def clean(self):
        cleaned_data = super().clean()
        branch = cleaned_data.get("branch")
        name = (cleaned_data.get("name") or "").strip()
        if branch and name and Item.objects.filter(branch=branch, name__iexact=name).exists():
            self.add_error("name", "This stock register item already exists for this branch.")
        return cleaned_data

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Register item name is required.")
        return name
