from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.urls import path

urlpatterns = [
    path("", lambda request: HttpResponse(), name="tenant-home"),
    path("profile/", lambda request: HttpResponse(), name="profile"),
    path("profile/advanced/", login_required(lambda request: HttpResponse()), name="advanced-profile"),
    path("login/", lambda request: HttpResponse(), name="login"),
]
