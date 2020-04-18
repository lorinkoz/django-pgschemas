from django.urls import path
from django.views.generic import TemplateView


urlpatterns = [
    path("", TemplateView.as_view(), name="main-home"),
    path("register/", TemplateView.as_view(), name="register"),
]
