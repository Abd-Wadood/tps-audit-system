from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .constants import ACCOUNTING_ROLE, REPORT_ROLE, STOCK_ROLE


def has_any_role(user, roles):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=roles).exists()


def role_required(*roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not has_any_role(request.user, roles):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def role_flags(user):
    if not user.is_authenticated:
        return {
            "is_stock_user": False,
            "is_accounting_user": False,
            "is_report_user": False,
            "is_superuser": False,
        }

    return {
        "is_stock_user": user.groups.filter(name=STOCK_ROLE).exists(),
        "is_accounting_user": user.groups.filter(name=ACCOUNTING_ROLE).exists(),
        "is_report_user": user.groups.filter(name=REPORT_ROLE).exists(),
        "is_superuser": getattr(user, "is_superuser", False),
    }
