from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stocks", "0014_add_non_negative_validators"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stockentry",
            name="opening",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="received",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="stock",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="sale",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="cancelled",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="exchange",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="ready",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="in_hand",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="remaining_value",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[MinValueValidator(0)]),
        ),
    ]
