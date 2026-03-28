from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from user_access.constants import ACCOUNTING_ROLE
from stocks.models import Branch, DailyStock, StockSheet


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
        sheet = StockSheet.objects.get(reference_number="ACC-NEGATIVE")
        self.assertEqual(str(sheet.system_sale), "0.00")
        self.assertEqual(sheet.local_purchases["values"]["cheese"], "0")
        self.assertEqual(sheet.market_purchases["values"]["chicken"], "0")
        self.assertEqual(sheet.counter_summary["values"]["counter_sale"], "0")
        self.assertEqual(sheet.total_summary["values"]["loan"], "0")
        self.assertEqual(sheet.totals["total_purchase"], "0")
        self.assertEqual(sheet.totals["balance"], "0")
