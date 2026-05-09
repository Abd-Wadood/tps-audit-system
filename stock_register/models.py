from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from stocks.models import Branch


class Item(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="stock_register_items")
    name = models.CharField(max_length=255)
    unit = models.CharField(max_length=50)
    current_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["branch__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "name"], name="unique_stock_register_item_per_branch"),
        ]

    def __str__(self):
        return f"{self.branch.name} - {self.name} ({self.unit})"


class StockTransaction(models.Model):
    IN = "IN"
    OUT = "OUT"
    TRANSACTION_TYPES = [
        (IN, "Stock In"),
        (OUT, "Stock Out"),
    ]

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="transactions")
    transaction_type = models.CharField(max_length=3, choices=TRANSACTION_TYPES)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    received_from = models.CharField(max_length=255, blank=True)
    issued_to = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_register_transactions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.item.name} {self.transaction_type} {self.quantity} {self.item.unit}"
