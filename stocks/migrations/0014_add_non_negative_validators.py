from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stocks", "0013_daily_stock_and_summary_audit_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dailystock",
            name="food_panda_orders",
            field=models.IntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="dailystock",
            name="shop_orders",
            field=models.IntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="dailystock",
            name="total_orders",
            field=models.IntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="cancelled",
            field=models.IntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="exchange",
            field=models.IntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="in_hand",
            field=models.IntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="opening",
            field=models.IntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="ready",
            field=models.IntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="received",
            field=models.IntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="remaining_value",
            field=models.IntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="sale",
            field=models.IntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="stock",
            field=models.IntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stocksheet",
            name="system_sale",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[MinValueValidator(0)]),
        ),
    ]
