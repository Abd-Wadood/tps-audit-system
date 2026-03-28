from django.db import migrations


def seed_owner_user(apps, schema_editor):
    User = apps.get_model("auth", "User")
    owner, created = User.objects.get_or_create(
        username="TPSadmin",
        defaults={
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        },
    )
    owner.is_staff = True
    owner.is_superuser = True
    owner.is_active = True
    if created and not owner.password:
        # Avoid shipping a known credential in fresh deployments.
        owner.password = "!"
    owner.save()


class Migration(migrations.Migration):
    dependencies = [
        ("stocks", "0006_seed_user_roles"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(seed_owner_user, migrations.RunPython.noop),
    ]
