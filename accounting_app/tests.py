from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from stock_control.sheet_logic import resolve_sheet
from user_access.constants import ACCOUNTING_ROLE
from user_access.models import UserWorkspace
from stocks.models import Branch, DailyStock, StockEntry, StockSheet


class AccountingSummaryFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner",
            password="testpass123",
            is_superuser=True,
            is_staff=True,
        )
        self.client.force_login(self.user)
        self.branch = Branch.objects.create(name="Township")

    def seed_sales_entries(self, target_date, sales_by_item, branch=None):
        context = resolve_sheet(branch_id=(branch or self.branch).pk, raw_date=target_date.isoformat())
        entries_by_name = {entry.item.name: entry for entry in context["entries"]}
        for item_name, sale_value in sales_by_item.items():
            entry = entries_by_name[item_name]
            entry.sale = Decimal(str(sale_value))
            entry.save(update_fields=["sale"])
        return context["daily_stock"]

    def test_summary_form_loads_existing_branch_and_date(self):
        StockSheet.objects.create(
            title="Existing Summary",
            reference_number="ACC-EXISTING",
            sheet_date=date(2026, 3, 27),
            branch=self.branch,
            system_sale=250,
            local_purchases={"values": {"cheese": "10"}, "custom_rows": []},
            market_purchases={"values": {"chicken": "20"}, "custom_rows": []},
            counter_summary={"values": {"counter_sale": "30", "direct_sale": "0", "credit": "0"}, "custom_rows": []},
            total_summary={"values": {"loan": "0", "extra_fee": "0", "total_wage": "0", "food_panda": "0", "discount": "0", "counter_purchase": "0"}, "custom_rows": []},
            totals={"total_sale": "280", "total_purchase": "30", "balance": "250"},
            created_by=self.user,
        )

        response = self.client.get(reverse("accounting_app:summary_create"), {"branch": self.branch.pk, "sheet_date": "2026-03-27"})

        self.assertContains(response, "Loaded existing summary")
        self.assertContains(response, 'value="Existing Summary"')
        self.assertContains(response, 'value="ACC-EXISTING"')

    def test_summary_save_updates_existing_record_for_same_branch_and_date(self):
        existing = StockSheet.objects.create(
            title="Existing Summary",
            reference_number="ACC-EXISTING",
            sheet_date=date(2026, 3, 27),
            branch=self.branch,
            system_sale=250,
            local_purchases={"values": {}, "custom_rows": []},
            market_purchases={"values": {}, "custom_rows": []},
            counter_summary={"values": {}, "custom_rows": []},
            total_summary={"values": {}, "custom_rows": []},
            totals={"total_sale": "250", "total_purchase": "0", "balance": "250"},
            created_by=self.user,
        )

        response = self.client.post(
            reverse("accounting_app:summary_create"),
            {
                "title": "Updated Summary",
                "reference_number": "ACC-EXISTING",
                "sheet_date": "2026-03-27",
                "branch": str(self.branch.pk),
                "system_sale": "300",
                "local_custom_rows": "[]",
                "market_custom_rows": "[]",
                "total_custom_rows": "[]",
                "local_cheese": "10",
                "market_chicken": "20",
                "counter_counter_sale": "30",
                "counter_direct_sale": "0",
                "counter_credit": "0",
                "total_loan": "0",
                "total_extra_fee": "0",
                "total_total_wage": "0",
                "total_food_panda": "0",
                "total_discount": "0",
                "total_counter_purchase": "0",
            },
        )

        self.assertRedirects(response, reverse("accounting_app:summary_detail", args=[existing.pk]))
        self.assertEqual(StockSheet.objects.filter(branch=self.branch, sheet_date=date(2026, 3, 27)).count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.title, "Updated Summary")
        self.assertEqual(str(existing.system_sale), "300.00")
        self.assertEqual(existing.revision_count, 1)
        self.assertEqual(existing.last_updated_by, self.user)

    def test_summary_create_ignores_manual_reference_number_and_generates_date_based_id(self):
        response = self.client.post(
            reverse("accounting_app:summary_create"),
            {
                "title": "Generated Summary",
                "reference_number": "MANUAL-CONFLICT",
                "sheet_date": "2026-03-27",
                "branch": str(self.branch.pk),
                "system_sale": "300",
                "local_custom_rows": "[]",
                "market_custom_rows": "[]",
                "total_custom_rows": "[]",
                "local_cheese": "10",
                "market_chicken": "20",
                "counter_counter_sale": "30",
                "counter_direct_sale": "0",
                "counter_credit": "0",
                "total_loan": "0",
                "total_extra_fee": "0",
                "total_total_wage": "0",
                "total_food_panda": "0",
                "total_discount": "0",
                "total_counter_purchase": "0",
            },
        )

        self.assertEqual(response.status_code, 302)
        sheet = StockSheet.objects.get(branch=self.branch, sheet_date=date(2026, 3, 27))
        self.assertEqual(sheet.reference_number, f"ACC-20260327-B{self.branch.pk}")
        self.assertNotEqual(sheet.reference_number, "MANUAL-CONFLICT")

    def test_summary_form_shows_reference_number_as_readonly(self):
        response = self.client.get(
            reverse("accounting_app:summary_create"),
            {"branch": self.branch.pk, "sheet_date": "2026-03-27"},
        )

        self.assertContains(response, f'value="ACC-20260327-B{self.branch.pk}" readonly')

    def test_reports_dashboard_filters_by_branch_and_date(self):
        other_branch = Branch.objects.create(name="Bahria")
        DailyStock.objects.create(branch=self.branch, date=date(2026, 3, 27))
        DailyStock.objects.create(branch=other_branch, date=date(2026, 3, 28))
        StockSheet.objects.create(
            title="Township Summary",
            reference_number="ACC-TOWN",
            sheet_date=date(2026, 3, 27),
            branch=self.branch,
            system_sale=100,
            local_purchases={"values": {}, "custom_rows": []},
            market_purchases={"values": {}, "custom_rows": []},
            counter_summary={"values": {}, "custom_rows": []},
            total_summary={"values": {}, "custom_rows": []},
            totals={"total_sale": "100", "total_purchase": "0", "balance": "100"},
            created_by=self.user,
        )
        StockSheet.objects.create(
            title="Bahria Summary",
            reference_number="ACC-BAH",
            sheet_date=date(2026, 3, 28),
            branch=other_branch,
            system_sale=200,
            local_purchases={"values": {}, "custom_rows": []},
            market_purchases={"values": {}, "custom_rows": []},
            counter_summary={"values": {}, "custom_rows": []},
            total_summary={"values": {}, "custom_rows": []},
            totals={"total_sale": "200", "total_purchase": "0", "balance": "200"},
            created_by=self.user,
        )

        response = self.client.get(reverse("reports_center:dashboard"), {"branch": self.branch.pk, "date": "2026-03-27"})

        self.assertContains(response, "Township Summary")
        self.assertContains(response, "Township")
        self.assertNotContains(response, "Bahria Summary")

    def test_reports_dashboard_defaults_to_last_10_days_without_date_filter(self):
        DailyStock.objects.create(branch=self.branch, date=date(2026, 4, 12))
        DailyStock.objects.create(branch=self.branch, date=date(2026, 4, 2))
        StockSheet.objects.create(
            title="Recent Summary",
            reference_number="ACC-RECENT",
            sheet_date=date(2026, 4, 11),
            branch=self.branch,
            system_sale=100,
            local_purchases={"values": {}, "custom_rows": []},
            market_purchases={"values": {}, "custom_rows": []},
            counter_summary={"values": {}, "custom_rows": []},
            total_summary={"values": {}, "custom_rows": []},
            totals={"total_sale": "100", "total_purchase": "0", "balance": "100"},
            created_by=self.user,
        )
        StockSheet.objects.create(
            title="Old Summary",
            reference_number="ACC-OLD",
            sheet_date=date(2026, 4, 1),
            branch=self.branch,
            system_sale=100,
            local_purchases={"values": {}, "custom_rows": []},
            market_purchases={"values": {}, "custom_rows": []},
            counter_summary={"values": {}, "custom_rows": []},
            total_summary={"values": {}, "custom_rows": []},
            totals={"total_sale": "100", "total_purchase": "0", "balance": "100"},
            created_by=self.user,
        )

        response = self.client.get(reverse("reports_center:dashboard"))

        self.assertContains(response, "Recent Summary")
        self.assertContains(response, "2026-04-12")
        self.assertNotContains(response, "ACC-OLD")
        self.assertNotContains(response, "2026-04-02")

    def test_reports_dashboard_builds_grouped_sales_graph_for_date_range(self):
        self.seed_sales_entries(
            date(2026, 3, 27),
            {
                "Small Dough": 2,
                "Medium Dough": 3,
                "Large Dough": 5,
                "Tortia Wrap": 4,
                "Paratha / Bread": 6,
                "Chicken Thigh Fillet": 7,
                "Chicken Piece": 2,
                "Chicken Wings": 1,
                "Veggie Burger": 50,
            },
        )
        self.seed_sales_entries(
            date(2026, 3, 28),
            {
                "Small Dough": 1,
                "Medium Dough": 1,
                "Large Dough": 2,
                "Chicken Wings": 9,
            },
        )

        response = self.client.get(
            reverse("reports_center:dashboard"),
            {
                "branch": self.branch.pk,
                "date_from": "2026-03-27",
                "date_to": "2026-03-28",
            },
        )

        self.assertEqual(response.status_code, 200)
        sales_graph = response.context["sales_graph"]
        self.assertTrue(sales_graph["has_data"])
        self.assertEqual(len(sales_graph["days"]), 2)
        totals_by_label = {category["label"]: category["total"] for category in sales_graph["categories"]}
        self.assertEqual(totals_by_label["Pizza Dough"], 14.0)
        self.assertEqual(totals_by_label["Chicken Fillet Burger"], 7.0)
        self.assertEqual(totals_by_label["Chicken Wings"], 10.0)
        self.assertNotIn("Veggie Burger", response.content.decode())
        self.assertContains(response, "Daily item sales graph")
        self.assertContains(response, "2026-03-27")

    def test_reports_dashboard_graph_view_hides_report_tables_and_stats(self):
        self.seed_sales_entries(
            date(2026, 3, 27),
            {
                "Small Dough": 2,
                "Chicken Wings": 3,
            },
        )

        response = self.client.get(
            reverse("reports_center:sales_graphs"),
            {
                "branch": self.branch.pk,
                "date": "2026-03-27",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Daily item sales graph")
        self.assertNotContains(response, "Daily Stock Reports")
        self.assertNotContains(response, "Daily stock sheets")
        self.assertNotContains(response, "Account summaries")

    def test_accounting_user_can_open_summary_detail(self):
        accounting_group, _ = Group.objects.get_or_create(name=ACCOUNTING_ROLE)
        accounting_user = User.objects.create_user(username="acc", password="testpass123")
        accounting_user.groups.add(accounting_group)
        sheet = StockSheet.objects.create(
            title="Township Summary",
            reference_number="ACC-TOWN",
            sheet_date=date(2026, 3, 27),
            branch=self.branch,
            system_sale=100,
            local_purchases={"values": {}, "custom_rows": []},
            market_purchases={"values": {}, "custom_rows": []},
            counter_summary={"values": {}, "custom_rows": []},
            total_summary={"values": {}, "custom_rows": []},
            totals={"total_sale": "100", "total_purchase": "0", "balance": "100"},
            created_by=self.user,
        )

        self.client.force_login(accounting_user)
        response = self.client.get(reverse("accounting_app:summary_detail", args=[sheet.pk]))

        self.assertEqual(response.status_code, 200)

    def test_owner_can_view_total_balance_for_date_range(self):
        other_branch = Branch.objects.create(name="Bahria")
        StockSheet.objects.create(
            title="Township Summary",
            reference_number="ACC-TOWN",
            sheet_date=date(2026, 3, 10),
            branch=self.branch,
            system_sale=100,
            local_purchases={"values": {}, "custom_rows": []},
            market_purchases={"values": {"chicken": "40", "sheikh_bill": "15"}, "custom_rows": []},
            counter_summary={"values": {}, "custom_rows": []},
            total_summary={"values": {"food_panda": "12"}, "custom_rows": []},
            totals={"total_sale": "100", "total_purchase": "0", "balance": "100"},
            created_by=self.user,
        )
        StockSheet.objects.create(
            title="Bahria Summary",
            reference_number="ACC-BAH",
            sheet_date=date(2026, 3, 12),
            branch=other_branch,
            system_sale=50,
            local_purchases={"values": {}, "custom_rows": []},
            market_purchases={"values": {"chicken": "25", "sheikh_bill": "10"}, "custom_rows": []},
            counter_summary={"values": {}, "custom_rows": []},
            total_summary={"values": {"food_panda": "8"}, "custom_rows": []},
            totals={"total_sale": "50", "total_purchase": "0", "balance": "25"},
            created_by=self.user,
        )
        StockSheet.objects.create(
            title="Outside Range",
            reference_number="ACC-OUT",
            sheet_date=date(2026, 3, 20),
            branch=other_branch,
            system_sale=50,
            local_purchases={"values": {}, "custom_rows": []},
            market_purchases={"values": {"chicken": "500", "sheikh_bill": "500"}, "custom_rows": []},
            counter_summary={"values": {}, "custom_rows": []},
            total_summary={"values": {"food_panda": "500"}, "custom_rows": []},
            totals={"total_sale": "50", "total_purchase": "0", "balance": "500"},
            created_by=self.user,
        )

        response = self.client.get(
            reverse("user_access:balance_overview"),
            {
                "balance_branch": str(self.branch.pk),
                "balance_from": "2026-03-09",
                "balance_to": "2026-03-15",
                "chicken_branch": str(self.branch.pk),
                "chicken_from": "2026-03-09",
                "chicken_to": "2026-03-15",
                "food_panda_branch": str(self.branch.pk),
                "food_panda_from": "2026-03-09",
                "food_panda_to": "2026-03-15",
                "sheikh_bill_branch": str(self.branch.pk),
                "sheikh_bill_from": "2026-03-09",
                "sheikh_bill_to": "2026-03-15",
            },
        )

        self.assertContains(response, "100")
        self.assertContains(response, "40")
        self.assertContains(response, "12")
        self.assertContains(response, "15")
        self.assertContains(response, "ACC-TOWN")
        self.assertNotContains(response, "ACC-BAH")
        self.assertNotContains(response, "ACC-OUT")

    def test_owner_can_delete_non_superuser_from_user_management(self):
        deletable_user = User.objects.create_user(username="delete_me", password="testpass123")

        response = self.client.post(
            reverse("user_access:user_management"),
            {"action": "delete_user", "user_id": deletable_user.pk},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(pk=deletable_user.pk).exists())

    def test_owner_user_management_rejects_weak_password(self):
        response = self.client.post(
            reverse("user_access:user_management"),
            {
                "action": "create_user",
                "first_name": "Weak",
                "last_name": "Password",
                "username": "weak-user",
                "email": "weak@example.com",
                "role": ACCOUNTING_ROLE,
                "password": "123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="weak-user").exists())
        self.assertContains(response, "This password is too short")

    def test_owner_can_create_user_with_branch_assignment(self):
        response = self.client.post(
            reverse("user_access:user_management"),
            {
                "action": "create_user",
                "first_name": "Branch",
                "last_name": "User",
                "username": "branch-user",
                "email": "branch@example.com",
                "role": ACCOUNTING_ROLE,
                "branch": str(self.branch.pk),
                "password": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        created_user = User.objects.get(username="branch-user")
        self.assertEqual(created_user.workspace.branch, self.branch)

    def test_owner_can_create_user_with_all_branches_access(self):
        response = self.client.post(
            reverse("user_access:user_management"),
            {
                "action": "create_user",
                "first_name": "All",
                "last_name": "Branches",
                "username": "all-branches-user",
                "email": "all@example.com",
                "role": ACCOUNTING_ROLE,
                "branch": "",
                "password": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        created_user = User.objects.get(username="all-branches-user")
        self.assertIsNone(created_user.workspace.branch)

    def test_accounting_review_adds_ready_to_remaining(self):
        accounting_group, _ = Group.objects.get_or_create(name=ACCOUNTING_ROLE)
        accounting_user = User.objects.create_user(username="reviewer", password="testpass123")
        accounting_user.groups.add(accounting_group)
        UserWorkspace.objects.create(user=accounting_user, branch=self.branch)
        context = resolve_sheet(branch_id=self.branch.pk, raw_date="2026-04-04")
        entry = context["entries"][0]
        entry.opening = Decimal("10.00")
        entry.received = Decimal("0.00")
        entry.stock = Decimal("10.00")
        entry.sale = Decimal("2.00")
        entry.cancelled = Decimal("0.00")
        entry.ready = Decimal("0.00")
        entry.in_hand = Decimal("8.00")
        entry.remaining_value = Decimal("3.00")
        entry.save()

        self.client.force_login(accounting_user)
        response = self.client.post(
            reverse("accounting_app:stock_review"),
            {
                "branch": str(self.branch.pk),
                "date": "2026-04-04",
                "total_orders": "0",
                "shop_orders": "0",
                "food_panda_orders": "0",
                f"cancelled_{entry.id}": "0.00",
                f"ready_{entry.id}": "1.25",
                f"remaining_{entry.id}": "4.25",
            },
        )

        self.assertEqual(response.status_code, 302)
        entry.refresh_from_db()
        self.assertEqual(entry.ready, Decimal("1.25"))
        self.assertEqual(entry.remaining_value, Decimal("4.25"))

        get_response = self.client.get(
            reverse("accounting_app:stock_review"),
            {"branch": self.branch.pk, "date": "2026-04-04"},
        )
        reviewed_entry = get_response.context["entries"][0]
        self.assertEqual(reviewed_entry.review_base_remaining, Decimal("3.00"))

    def test_negative_accounting_inputs_are_clamped_to_zero(self):
        response = self.client.post(
            reverse("accounting_app:summary_create"),
            {
                "title": "Updated Summary",
                "reference_number": "ACC-NEGATIVE",
                "sheet_date": "2026-03-27",
                "branch": str(self.branch.pk),
                "system_sale": "-300",
                "local_custom_rows": "[]",
                "market_custom_rows": "[]",
                "total_custom_rows": "[]",
                "local_cheese": "-10",
                "market_chicken": "-20",
                "counter_counter_sale": "-30",
                "counter_direct_sale": "-2",
                "counter_credit": "-1",
                "total_loan": "-4",
                "total_extra_fee": "-5",
                "total_total_wage": "-6",
                "total_food_panda": "-7",
                "total_discount": "-8",
                "total_counter_purchase": "-9",
            },
        )

        self.assertEqual(response.status_code, 302)
        sheet = StockSheet.objects.get(branch=self.branch, sheet_date=date(2026, 3, 27))
        self.assertEqual(sheet.reference_number, f"ACC-20260327-B{self.branch.pk}")
        self.assertEqual(str(sheet.system_sale), "0.00")
        self.assertEqual(sheet.local_purchases["values"]["cheese"], "0")
        self.assertEqual(sheet.market_purchases["values"]["chicken"], "0")
        self.assertEqual(sheet.counter_summary["values"]["counter_sale"], "0")
        self.assertEqual(sheet.total_summary["values"]["loan"], "0")
        self.assertEqual(sheet.totals["total_purchase"], "0")
        self.assertEqual(sheet.totals["balance"], "0")
