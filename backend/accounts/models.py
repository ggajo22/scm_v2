from django.contrib.auth.models import AbstractUser
from django.db import models


class AdminUser(AbstractUser):
    # @MX:ANCHOR: [AUTO] AdminUser is the central auth model — all auth flows depend on this
    # @MX:REASON: AUTH_USER_MODEL references this; changing fields here impacts migrations and JWT
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "SuperAdmin"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ADMIN,
    )
    # Email is not used for login — stored for reference only
    email = models.EmailField(blank=True, null=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["role"]

    class Meta:
        verbose_name = "Admin User"
        verbose_name_plural = "Admin Users"

    def __str__(self) -> str:
        return self.username
