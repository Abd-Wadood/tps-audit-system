from django.urls import reverse

from stocks.models import Branch


def get_user_branch(user):
    workspace = getattr(user, "workspace", None)
    if not workspace:
        return None
    return workspace.branch


def get_user_branch_id(user):
    branch = get_user_branch(user)
    return branch.pk if branch else None


def get_accessible_branches(user):
    branches = Branch.objects.order_by("name")
    if getattr(user, "is_superuser", False):
        return branches

    branch_id = get_user_branch_id(user)
    if branch_id:
        return branches.filter(pk=branch_id)
    return branches


def get_branch_aware_url(view_name, user):
    branch_id = get_user_branch_id(user)
    url = reverse(view_name)
    if branch_id:
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}branch={branch_id}"
    return url
