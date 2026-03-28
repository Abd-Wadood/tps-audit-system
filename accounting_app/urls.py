from django.urls import path

from .views import stock_review_view, summary_create_view, summary_detail_view, summary_list_view, summary_pdf_view

app_name = "accounting_app"

urlpatterns = [
    path("", summary_list_view, name="summary_list"),
    path("new/", summary_create_view, name="summary_create"),
    path("stock-review/", stock_review_view, name="stock_review"),
    path("<int:pk>/", summary_detail_view, name="summary_detail"),
    path("<int:pk>/pdf/", summary_pdf_view, name="summary_pdf"),
]
