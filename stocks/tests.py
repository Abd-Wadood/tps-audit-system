from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .accounting import calculate_totals
from .models import Branch, DailyStock, StockSheet
from stock_control.sheet_logic import resolve_sheet
from user_access.constants import STOCK_ROLE
from user_access.models import UserWorkspace


class StockSheetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="testpass123", is_superuser=True, is_staff=True)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("stock_control:stock_sheet"))
        self.assertEqual(response.status_code, 302)

    def test_sheet_total_value(self):
        totals = calculate_totals(
            "100",
            {"values": {"cheese": "20"}, "custom_rows": []},
            {"values": {"chicken": "15"}, "custom_rows": []},
            {"values": {"counter_sale": "25", "direct_sale": "5", "credit": "10"}, "custom_rows": []},
            {"values": {"loan": "10", "extra_fee": "5", "total_wage": "20", "food_panda": "0", "discount": "3", "counter_purchase": "12"}, "custom_rows": []},
        )
        sheet = StockSheet.objects.create(
            title="Main Counter",
            reference_number="REF-001",
            sheet_date=date.today(),
            branch=Branch.objects.create(name="Test Branch"),
            system_sale=100,
            local_purchases={"values": {"cheese": "20"}, "custom_rows": []},
            market_purchases={"values": {"chicken": "15"}, "custom_rows": []},
            counter_summary={"values": {"counter_sale": "25", "direct_sale": "5", "credit": "10"}, "custom_rows": []},
            total_summary={"values": {"loan": "10", "extra_fee": "5", "total_wage": "20", "food_panda": "0", "discount": "3", "counter_purchase": "12"}, "custom_rows": []},
            totals={key: str(value) for key, value in totals.items()},
            created_by=self.user,
        )
        self.assertEqual(sheet.totals["total_purchase"], "85")
        self.assertEqual(sheet.totals["total_sale"], "30")
        self.assertEqual(sheet.totals["difference"], "-75")
        self.assertEqual(sheet.totals["balance"], "-55")

    def test_resolve_sheet_creates_distinct_records_per_date_and_branch(self):
        first_context = resolve_sheet(raw_date="2026-03-20")
        second_context = resolve_sheet(branch_id=2, raw_date="2026-03-21")
        repeated_context = resolve_sheet(branch_id=2, raw_date="2026-03-21")

        self.assertEqual(first_context["selected_date"].isoformat(), "2026-03-20")
        self.assertEqual(second_context["selected_date"].isoformat(), "2026-03-21")
        self.assertEqual(second_context["branch"].name, "Bediyan Road")
        self.assertEqual(DailyStock.objects.count(), 2)
        self.assertEqual(second_context["daily_stock"].pk, repeated_context["daily_stock"].pk)

    def test_resolve_sheet_uses_all_available_branches(self):
        branch = Branch.objects.create(name="Township")

        context = resolve_sheet(branch_id=branch.pk, raw_date="2026-03-22")

        self.assertEqual(context["branch"].pk, branch.pk)
        self.assertTrue(any(option.pk == branch.pk for option in context["branches"]))

    def test_new_sheet_opening_uses_previous_day_remaining(self):
        first_context = resolve_sheet(raw_date="2026-03-20")
        first_entry = first_context["entries"][0]
        first_entry.remaining_value = Decimal("7.00")
        first_entry.save(update_fields=["remaining_value"])

        next_context = resolve_sheet(raw_date="2026-03-21")
        next_entry = next_context["entries"][0]

        self.assertEqual(next_entry.opening, Decimal("7.00"))
        self.assertEqual(next_entry.stock, Decimal("7.00"))

    def test_daily_stock_second_save_tracks_revision_user_and_count(self):
        self.client.force_login(self.user)

        first_response = self.client.post(
            reverse("stock_control:stock_sheet"),
            {
                "branch": "1",
                "date": "2026-03-20",
                "total_orders": "10",
                "shop_orders": "5",
                "food_panda_orders": "5",
            },
        )
        second_response = self.client.post(
            reverse("stock_control:stock_sheet"),
            {
                "branch": "1",
                "date": "2026-03-20",
                "total_orders": "12",
                "shop_orders": "7",
                "food_panda_orders": "5",
            },
        )

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        daily_stock = DailyStock.objects.get(branch__name="Barki Road", date="2026-03-20")
        self.assertEqual(daily_stock.revision_count, 1)
        self.assertEqual(daily_stock.last_updated_by, self.user)

    def test_negative_stock_inputs_are_clamped_to_zero(self):
        self.client.force_login(self.user)
        context = resolve_sheet(branch_id=1, raw_date="2026-03-22")
        first_entry = context["entries"][0]

        response = self.client.post(
            reverse("stock_control:stock_sheet"),
            {
                "branch": "1",
                "date": "2026-03-22",
                "total_orders": "-10",
                "shop_orders": "-5",
                "food_panda_orders": "-2",
                f"opening_{first_entry.id}": "-3",
                f"received_{first_entry.id}": "-4",
                f"sale_{first_entry.id}": "-5",
                f"exchange_{first_entry.id}": "-6",
                f"remaining_{first_entry.id}": "-7",
            },
        )

        self.assertEqual(response.status_code, 302)
        daily_stock = DailyStock.objects.get(branch__name="Barki Road", date="2026-03-22")
        first_entry.refresh_from_db()
        self.assertEqual(daily_stock.total_orders, 0)
        self.assertEqual(daily_stock.shop_orders, 0)
        self.assertEqual(daily_stock.food_panda_orders, 0)
        self.assertEqual(first_entry.opening, 0)
        self.assertEqual(first_entry.received, 0)
        self.assertEqual(first_entry.sale, 0)
        self.assertEqual(first_entry.exchange, 0)
        self.assertEqual(first_entry.remaining_value, 0)
        self.assertEqual(first_entry.stock, 0)
        self.assertEqual(first_entry.in_hand, 0)

    def test_stock_sheet_accepts_decimal_values(self):
        self.client.force_login(self.user)
        context = resolve_sheet(branch_id=1, raw_date="2026-03-25")
        first_entry = context["entries"][0]

        response = self.client.post(
            reverse("stock_control:stock_sheet"),
            {
                "branch": "1",
                "date": "2026-03-25",
                "total_orders": "10",
                "shop_orders": "5",
                "food_panda_orders": "5",
                f"opening_{first_entry.id}": "1.50",
                f"received_{first_entry.id}": "2.25",
                f"sale_{first_entry.id}": "1.00",
                f"exchange_{first_entry.id}": "0.50",
                f"remaining_{first_entry.id}": "2.75",
            },
        )

        self.assertEqual(response.status_code, 302)
        first_entry.refresh_from_db()
        self.assertEqual(first_entry.opening, Decimal("1.50"))
        self.assertEqual(first_entry.received, Decimal("2.25"))
        self.assertEqual(first_entry.stock, Decimal("3.75"))
        self.assertEqual(first_entry.sale, Decimal("1.00"))
        self.assertEqual(first_entry.exchange, Decimal("0.50"))
        self.assertEqual(first_entry.remaining_value, Decimal("2.75"))
        self.assertEqual(first_entry.in_hand, Decimal("2.75"))

    def test_stock_user_login_redirects_to_assigned_branch(self):
        user = User.objects.create_user(username="stocker", password="testpass123")
        stock_group, _ = Group.objects.get_or_create(name=STOCK_ROLE)
        user.groups.add(stock_group)
        assigned_branch = Branch.objects.create(name="Township")
        UserWorkspace.objects.create(user=user, branch=assigned_branch)

        response = self.client.post(reverse("login"), {"username": "stocker", "password": "testpass123"})

        self.assertRedirects(response, f"{reverse('stock_control:stock_sheet')}?branch={assigned_branch.pk}")

    def test_stock_user_cannot_switch_to_another_branch_sheet(self):
        user = User.objects.create_user(username="stocker2", password="testpass123")
        stock_group, _ = Group.objects.get_or_create(name=STOCK_ROLE)
        user.groups.add(stock_group)
        assigned_branch = Branch.objects.create(name="Township")
        other_branch = Branch.objects.create(name="Bahria")
        UserWorkspace.objects.create(user=user, branch=assigned_branch)
        self.client.force_login(user)

        response = self.client.get(reverse("stock_control:stock_sheet"), {"branch": other_branch.pk, "date": "2026-03-22"})

        self.assertEqual(response.context["branch"].pk, assigned_branch.pk)
        self.assertTrue(all(branch.pk == assigned_branch.pk for branch in response.context["branches"]))

# Create your tests here.
