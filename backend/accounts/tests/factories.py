import factory
from factory.django import DjangoModelFactory

from accounts.models import AdminUser


class AdminUserFactory(DjangoModelFactory):
    class Meta:
        model = AdminUser

    username = factory.Sequence(lambda n: f"admin_{n}")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    role = AdminUser.Role.ADMIN
    is_active = True


class SuperAdminFactory(AdminUserFactory):
    role = AdminUser.Role.SUPER_ADMIN


class InactiveAdminFactory(AdminUserFactory):
    is_active = False
