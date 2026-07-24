from django.urls import path

from .views import (
    accounting_range_pdf_view,
    monthly_stock_usage_pdf_view,
    owner_balance_view,
    owner_user_management_view,
    sheikh_bill_pdf_view,
    signup_view,
    workspace_home,
)

app_name = "user_access"

urlpatterns = [
    path("", workspace_home, name="workspace_home"),
    path("signup/", signup_view, name="signup"),
    path("users/", owner_user_management_view, name="user_management"),
    path("balance/", owner_balance_view, name="balance_overview"),
    path("balance/accounting-range-pdf/", accounting_range_pdf_view, name="accounting_range_pdf"),
    path("balance/monthly-stock-usage-pdf/", monthly_stock_usage_pdf_view, name="monthly_stock_usage_pdf"),
    path("balance/sheikh-bill-pdf/", sheikh_bill_pdf_view, name="sheikh_bill_pdf"),
]
