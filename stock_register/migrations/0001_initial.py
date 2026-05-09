from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


ROLE_NAMES = ["stock_registrar"]


def seed_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for role_name in ROLE_NAMES:
        Group.objects.get_or_create(name=role_name)


def remove_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=ROLE_NAMES).delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("stocks", "0015_stockentry_decimal_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="StockRegister",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("revision_count", models.PositiveIntegerField(default=0)),
                ("branch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stock_registers", to="stocks.branch")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_stock_registers", to=settings.AUTH_USER_MODEL)),
                ("last_updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_stock_registers", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-date", "branch__name"],
            },
        ),
        migrations.CreateModel(
            name="StockRegisterEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rate", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("received_stock", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("issued_stock", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("remaining_balance", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("stock_in_hand", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stock_register_entries", to="stocks.item")),
                ("register", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="entries", to="stock_register.stockregister")),
            ],
            options={
                "ordering": ["item_id"],
            },
        ),
        migrations.AddConstraint(
            model_name="stockregister",
            constraint=models.UniqueConstraint(fields=("date", "branch"), name="unique_stock_register_per_branch"),
        ),
        migrations.AddConstraint(
            model_name="stockregisterentry",
            constraint=models.UniqueConstraint(fields=("register", "item"), name="unique_stock_register_entry_per_item"),
        ),
        migrations.RunPython(seed_roles, remove_roles),
    ]

