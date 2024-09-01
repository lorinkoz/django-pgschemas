from django.contrib import admin
from django.urls import path

from sandbox.views import generic

urlpatterns = [
    path("", generic, name="main-home"),
    path("register/", generic, name="register"),
    path("admin/", admin.site.urls),
]
