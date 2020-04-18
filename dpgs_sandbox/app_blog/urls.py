from django.urls import path
from django.views.generic import TemplateView


urlpatterns = [
    path("", TemplateView.as_view(), name="blog-home"),
    path("entries/", TemplateView.as_view(), name="entries"),
]
