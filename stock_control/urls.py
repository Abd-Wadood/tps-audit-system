from django.urls import path

from .views import stock_sheet_pdf_view, stock_sheet_view

app_name = "stock_control"

urlpatterns = [
    path("", stock_sheet_view, name="stock_sheet"),
    path("pdf/", stock_sheet_pdf_view, name="stock_sheet_pdf"),
]
