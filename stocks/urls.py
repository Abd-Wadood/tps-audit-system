from django.urls import include, path

urlpatterns = [
    path("stock/", include("stock_control.urls")),
    path("accounting/", include("accounting_app.urls")),
    path("reports/", include("reports_center.urls")),
]

