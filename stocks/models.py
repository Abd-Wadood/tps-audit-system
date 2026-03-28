from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


DEFAULT_ITEM_NAMES = [
    "Chicken Thigh Fillet",
    "Chicken Patty",
    "Chicken Nuggets",
    "Chicken Wings",
    "Chicken Piece",
    "Small Dough",
    "Medium Dough",
    "Large Dough",
    "Burger Buns",
    "Paratha / Bread",
    "Tortia Wrap",
    "Sandwich Bread",
    "Veggie Burger",
    "Eggs",
    "Coke 0.5L",
    "Coke 1L",
    "Coke 1.5L",
    "Coke 350L",
    "Fish Fillet",
    "Kabab",
    "Tikka",
    "Malai Boti",
    "Chargha",
]


class Branch(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Item(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class DailyStock(models.Model):
    date = models.DateField()
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="daily_stocks")
    total_orders = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    shop_orders = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    food_panda_orders = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_daily_stocks")
    revision_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-date", "branch__name"]
        constraints = [
            models.UniqueConstraint(fields=["date", "branch"], name="unique_daily_stock_per_branch"),
        ]

    def __str__(self):
        return f"{self.branch} - {self.date:%Y-%m-%d}"


class StockEntry(models.Model):
    daily_stock = models.ForeignKey(DailyStock, on_delete=models.CASCADE, related_name="entries")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="stock_entries")
    opening = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    received = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    sale = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    cancelled = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    exchange = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    ready = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    in_hand = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    remaining_value = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ["item_id"]
        constraints = [
            models.UniqueConstraint(fields=["daily_stock", "item"], name="unique_entry_per_item_per_daily_stock"),
        ]

    def __str__(self):
        return f"{self.daily_stock} - {self.item}"

    @property
    def diff_minus(self):
        return max(self.remaining - self.in_hand, 0)

    @property
    def diff_plus(self):
        return max(self.in_hand - self.remaining, 0)

    @property
    def remaining(self):
        return self.remaining_value


class StockSheet(models.Model):
    title = models.CharField(max_length=200)
    reference_number = models.CharField(max_length=50, unique=True)
    sheet_date = models.DateField()
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="account_summaries")
    system_sale = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    local_purchases = models.JSONField(default=dict, blank=True)
    market_purchases = models.JSONField(default=dict, blank=True)
    counter_summary = models.JSONField(default=dict, blank=True)
    total_summary = models.JSONField(default=dict, blank=True)
    totals = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stock_sheets")
    last_updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_stock_sheets")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    revision_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-sheet_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["sheet_date", "branch"], name="unique_account_summary_per_branch_per_day"),
        ]

    def __str__(self):
        branch_name = self.branch.name if self.branch else "Unassigned"
        return f"{self.reference_number} - {self.title} ({branch_name})"

    def get_absolute_url(self):
        return reverse("accounting_app:summary_detail", args=[self.pk])

    @property
    def total_sale(self):
        return self.totals.get("total_sale", "0.00")

    @property
    def total_purchase(self):
        return self.totals.get("total_purchase", "0.00")

    @property
    def balance(self):
        return self.totals.get("balance", "0.00")
