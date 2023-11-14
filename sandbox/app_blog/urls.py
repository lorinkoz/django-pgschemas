from django.urls import path

from sandbox.views import generic

urlpatterns = [
    path("", generic, name="blog-home"),
    path("entries/", generic, name="entries"),
]
