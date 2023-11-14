from django.http import HttpResponse
from django.urls import path

from sandbox.views import generic

urlpatterns = [
    path("", generic, name="main-home"),
    path("register/", generic, name="register"),
    path("ping/", lambda request: HttpResponse(), name="ping"),
]
