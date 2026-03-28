from .permissions import role_flags


def role_context(request):
    if not request.user.is_authenticated:
        return {
            "role_can_stock": False,
            "role_can_accounting": False,
            "role_can_reports": False,
        }

    flags = role_flags(request.user)
    return {
        "role_can_stock": flags["is_stock_user"] or flags["is_superuser"],
        "role_can_accounting": flags["is_accounting_user"] or flags["is_superuser"],
        "role_can_reports": flags["is_report_user"] or flags["is_superuser"],
    }

