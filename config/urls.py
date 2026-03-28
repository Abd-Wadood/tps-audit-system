from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path

from user_access.views import WorkspaceLoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/login/", WorkspaceLoginView.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("", include("user_access.urls")),
    path("stock/", include("stock_control.urls")),
    path("accounting/", include("accounting_app.urls")),
    path("reports/", include("reports_center.urls")),
]
