from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from stocks.models import Branch, DailyStock, Item, StockEntry


class WorkspaceLoginSessionTests(TestCase):
    def test_login_sets_session_to_expire_after_24_hours(self):
        User.objects.create_user(username="session-user", password="testpass123")

        response = self.client.post(
            reverse("login"),
            {"username": "session-user", "password": "testpass123"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get_expiry_age(), 60 * 60 * 24)


class OwnerStockItemManagementTests(TestCase):
    def test_owner_can_add_stock_item_from_user_management(self):
        owner = User.objects.create_user(
            username="owner",
            password="testpass123",
            is_superuser=True,
            is_staff=True,
        )
        self.client.force_login(owner)

        response = self.client.post(
            reverse("user_access:user_management"),
            {"action": "create_item", "name": "Mozzarella Cheese"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Item.objects.filter(name="Mozzarella Cheese").exists())

    def test_owner_can_remove_unused_stock_item_from_user_management(self):
        owner = User.objects.create_user(
            username="owner-remove",
            password="testpass123",
            is_superuser=True,
            is_staff=True,
        )
        item = Item.objects.create(name="Temporary Item")
        self.client.force_login(owner)

        response = self.client.post(
            reverse("user_access:user_management"),
            {"action": "delete_item", "item_id": item.id},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Item.objects.filter(pk=item.pk).exists())

    def test_owner_can_remove_stock_item_that_is_already_used(self):
        owner = User.objects.create_user(
            username="owner-protect",
            password="testpass123",
            is_superuser=True,
            is_staff=True,
        )
        branch = Branch.objects.create(name="Protected Branch")
        item = Item.objects.create(name="Used Item")
        daily_stock = DailyStock.objects.create(branch=branch, date="2026-04-13")
        StockEntry.objects.create(daily_stock=daily_stock, item=item)
        self.client.force_login(owner)

        response = self.client.post(
            reverse("user_access:user_management"),
            {"action": "delete_item", "item_id": item.id},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Item.objects.filter(pk=item.pk).exists())
        self.assertFalse(StockEntry.objects.filter(daily_stock=daily_stock).exists())

    def test_owner_can_search_stock_items_by_name(self):
        owner = User.objects.create_user(
            username="owner-search",
            password="testpass123",
            is_superuser=True,
            is_staff=True,
        )
        Item.objects.create(name="Mozzarella Cheese")
        Item.objects.create(name="Paneer Cubes")
        self.client.force_login(owner)

        response = self.client.get(
            reverse("user_access:user_management"),
            {"item_query": "mozza"},
        )

        self.assertContains(response, "Mozzarella Cheese")
        self.assertNotContains(response, "Paneer Cubes")
