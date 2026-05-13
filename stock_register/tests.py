from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from stocks.models import Branch
from user_access.constants import STOCK_REGISTRAR_ROLE
from user_access.models import UserWorkspace

from .models import Item, StockTransaction
from .services import process_stock_transaction


class StockRegisterTests(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(name="Barki Store")
        self.other_branch = Branch.objects.create(name="Bediyan Store")
        self.item = Item.objects.create(branch=self.branch, name="Flour", unit="kg")
        self.other_item = Item.objects.create(branch=self.other_branch, name="Flour", unit="kg")
        self.group, _ = Group.objects.get_or_create(name=STOCK_REGISTRAR_ROLE)
        self.user = User.objects.create_user(username="registrar", password="testpass123")
        self.user.groups.add(self.group)
        UserWorkspace.objects.create(user=self.user, branch=self.branch)

    def test_stock_in_creates_transaction_and_increases_current_stock(self):
        movement = process_stock_transaction(
            item_id=self.item.pk,
            transaction_type=StockTransaction.IN,
            quantity=Decimal("25.00"),
            user=self.user,
            rate=Decimal("180.00"),
            received_from="Supplier A",
        )

        self.item.refresh_from_db()
        self.assertEqual(self.item.current_stock, Decimal("25.00"))
        self.assertEqual(movement.balance_after, Decimal("25.00"))
        self.assertEqual(movement.total_amount, Decimal("4500.00"))
        self.assertEqual(movement.received_from, "Supplier A")
        self.other_item.refresh_from_db()
        self.assertEqual(self.other_item.current_stock, Decimal("0.00"))

    def test_stock_out_creates_transaction_and_decreases_current_stock(self):
        process_stock_transaction(self.item.pk, StockTransaction.IN, Decimal("25.00"), self.user, received_from="Supplier A")

        movement = process_stock_transaction(
            item_id=self.item.pk,
            transaction_type=StockTransaction.OUT,
            quantity=Decimal("7.50"),
            user=self.user,
            issued_to="Kitchen",
        )

        self.item.refresh_from_db()
        self.assertEqual(self.item.current_stock, Decimal("17.50"))
        self.assertEqual(movement.balance_after, Decimal("17.50"))
        self.assertEqual(movement.issued_to, "Kitchen")

    def test_stock_out_rejects_quantity_above_available_stock(self):
        with self.assertRaises(ValidationError):
            process_stock_transaction(
                item_id=self.item.pk,
                transaction_type=StockTransaction.OUT,
                quantity=Decimal("1.00"),
                user=self.user,
                issued_to="Kitchen",
            )

        self.item.refresh_from_db()
        self.assertEqual(self.item.current_stock, Decimal("0.00"))
        self.assertFalse(StockTransaction.objects.exists())

    def test_stock_registrar_can_record_movement_from_page(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("stock_register:register"),
            {
                "branch": self.branch.pk,
                "item": self.item.pk,
                "transaction_type": StockTransaction.IN,
                "quantity": "10",
                "rate": "120",
                "received_from": "Supplier A",
                "issued_to": "",
                "notes": "Morning delivery",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.current_stock, Decimal("10.00"))
        transaction = StockTransaction.objects.get()
        self.assertEqual(transaction.total_amount, Decimal("1200.00"))

    def test_stock_out_from_page_does_not_need_rate_or_supplier(self):
        process_stock_transaction(
            self.item.pk,
            StockTransaction.IN,
            Decimal("25.00"),
            self.user,
            rate=Decimal("180.00"),
            received_from="Supplier A",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("stock_register:register"),
            {
                "branch": self.branch.pk,
                "item": self.item.pk,
                "transaction_type": StockTransaction.OUT,
                "quantity": "5",
                "rate": "999",
                "received_from": "Supplier A",
                "issued_to": "Kitchen",
                "notes": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        movement = StockTransaction.objects.filter(transaction_type=StockTransaction.OUT).get()
        self.assertIsNone(movement.rate)
        self.assertEqual(movement.total_amount, Decimal("0.00"))
        self.assertEqual(movement.received_from, "")
        self.assertEqual(movement.issued_to, "Kitchen")

    def test_page_filters_items_to_selected_branch(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("stock_register:register"), {"branch": self.branch.pk})

        self.assertEqual(response.status_code, 200)
        item_ids = list(response.context["form"].fields["item"].queryset.values_list("pk", flat=True))
        self.assertEqual(item_ids, [self.item.pk])
