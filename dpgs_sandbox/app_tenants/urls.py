from django.urls import path
from django.views.generic import TemplateView


urlpatterns = [
    path("", TemplateView.as_view(), name="home"),
    path("profile/", TemplateView.as_view(), name="profile"),
    path("profile/advanced/", TemplateView.as_view(), name="advanced-profile"),
]
