from django.urls import path

from .views import reports_dashboard_view, sales_graph_view

app_name = "reports_center"

urlpatterns = [
    path("graphs/", sales_graph_view, name="sales_graphs"),
    path("", reports_dashboard_view, name="dashboard"),
]
