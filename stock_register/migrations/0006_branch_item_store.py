from django.db import migrations, models
import django.db.models.deletion


def assign_existing_items_to_first_branch(apps, schema_editor):
    Branch = apps.get_model("stocks", "Branch")
    Item = apps.get_model("stock_register", "Item")
    branch = Branch.objects.order_by("name").first()
    if branch is None:
        branch = Branch.objects.create(name="Default Branch")
    Item.objects.filter(branch__isnull=True).update(branch=branch)


class Migration(migrations.Migration):
    dependencies = [
        ("stocks", "0015_stockentry_decimal_fields"),
        ("stock_register", "0005_stocktransaction_total_amount"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="name",
            field=models.CharField(max_length=255),
        ),
        migrations.AddField(
            model_name="item",
            name="branch",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="stock_register_items",
                to="stocks.branch",
            ),
        ),
        migrations.RunPython(assign_existing_items_to_first_branch, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="item",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="stock_register_items",
                to="stocks.branch",
            ),
        ),
        migrations.AlterModelOptions(
            name="item",
            options={"ordering": ["branch__name", "name"]},
        ),
        migrations.AddConstraint(
            model_name="item",
            constraint=models.UniqueConstraint(fields=("branch", "name"), name="unique_stock_register_item_per_branch"),
        ),
    ]
