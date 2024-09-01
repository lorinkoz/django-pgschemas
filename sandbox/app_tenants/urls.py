from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.urls import path

from sandbox.views import generic

urlpatterns = [
    path("", generic, name="tenant-home"),
    path("profile/", generic, name="profile"),
    path("profile/advanced/", login_required(generic), name="advanced-profile"),
    path("login/", generic, name="login"),
    path("ping/", lambda request: HttpResponse(), name="ping"),
]
