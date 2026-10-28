from django.db import models

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrator"
        AP_CLERK = "AP_CLERK", "Accounts Payable Clerk"
        APPROVER = "APPROVER", "Approver"
        FINANCE_MANAGER = "FINANCE_MANAGER", "Finance Manager"
        AUDITOR = "AUDITOR", "Auditor"

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.AP_CLERK,
    )

    department = models.CharField(
        max_length=100,
        blank=True,
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
