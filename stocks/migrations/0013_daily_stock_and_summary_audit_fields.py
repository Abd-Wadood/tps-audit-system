import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stocks", "0012_stocksheet_unique_account_summary_per_branch_per_day"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="dailystock",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="dailystock",
            name="last_updated_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_daily_stocks", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="dailystock",
            name="revision_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="dailystock",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="stocksheet",
            name="last_updated_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_stock_sheets", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="stocksheet",
            name="revision_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
