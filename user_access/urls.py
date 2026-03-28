from django.urls import path

from .views import owner_balance_view, owner_user_management_view, signup_view, workspace_home

app_name = "user_access"

urlpatterns = [
    path("", workspace_home, name="workspace_home"),
    path("signup/", signup_view, name="signup"),
    path("users/", owner_user_management_view, name="user_management"),
    path("balance/", owner_balance_view, name="balance_overview"),
]
