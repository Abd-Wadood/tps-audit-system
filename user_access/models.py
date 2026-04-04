from django.conf import settings
from django.db import models

from stocks.models import Branch


class UserWorkspace(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workspace")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_users")

    def __str__(self):
        return f"{self.user.username} workspace"
