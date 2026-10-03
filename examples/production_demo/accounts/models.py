from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        OPERATOR = "operator", "Operator"
        MANAGER = "manager", "Manager"

    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.OPERATOR)

    def __str__(self) -> str:
        return self.email
