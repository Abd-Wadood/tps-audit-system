from django.urls import path

from .views import stock_register_view

app_name = "stock_register"

urlpatterns = [
    path("", stock_register_view, name="register"),
]

