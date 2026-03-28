from django.db import migrations


ROLE_NAMES = ["stock_updater", "accounting_user", "report_admin"]


def seed_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for role_name in ROLE_NAMES:
        Group.objects.get_or_create(name=role_name)


def remove_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=ROLE_NAMES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("stocks", "0005_dailystock_food_panda_orders_dailystock_shop_orders_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(seed_roles, remove_roles),
    ]
