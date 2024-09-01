from django.http import HttpResponse
from django.urls import path

from sandbox.views import generic

urlpatterns = [
    path("", generic, name="blog-home"),
    path("entries/", generic, name="entries"),
    path("ping/", lambda request: HttpResponse(), name="ping"),
]
