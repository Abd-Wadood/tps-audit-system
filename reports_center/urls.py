from django.urls import path

from .views import reports_dashboard_view

app_name = "reports_center"

urlpatterns = [
    path("", reports_dashboard_view, name="dashboard"),
]
