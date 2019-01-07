from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    pass


class User(AbstractBaseUser):

    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=50)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ("display_name",)

    objects = UserManager()
