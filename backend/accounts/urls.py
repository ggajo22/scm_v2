from django.urls import path
from rest_framework.routers import DefaultRouter

from accounts.views import AdminUserViewSet, LoginView, LogoutView, TokenRefreshView

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
]

router = DefaultRouter()
router.register(r"admin/users", AdminUserViewSet, basename="admin-users")
urlpatterns += router.urls

# Custom action: reset-password
urlpatterns += [
    path(
        "admin/users/<int:pk>/reset-password/",
        AdminUserViewSet.as_view({"post": "reset_password"}),
        name="admin-users-reset-password",
    ),
]
