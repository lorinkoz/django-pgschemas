from django.urls import path

from dpgs_sandbox.views import generic

urlpatterns = [
    path("", generic, name="blog-home"),
    path("entries/", generic, name="entries"),
]
