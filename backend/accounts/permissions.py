from rest_framework.permissions import BasePermission

from accounts.models import AdminUser


class IsSuperAdmin(BasePermission):
    # @MX:ANCHOR: [AUTO] IsSuperAdmin is the gatekeeper for all SuperAdmin-only endpoints
    # @MX:REASON: REQ-AUTH-015 CRITICAL — role must be read from DB (request.user), NOT JWT payload
    """
    Grants access only to authenticated, active SUPER_ADMIN users.

    CRITICAL (REQ-AUTH-015): Role is read from request.user (DB),
    never from JWT payload claims.
    """

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if not request.user.is_active:
            return False
        # Read role from DB via request.user — NOT from JWT payload
        return request.user.role == AdminUser.Role.SUPER_ADMIN


class IsAdminOrSuperAdmin(BasePermission):
    """
    Grants access to authenticated, active users with ADMIN or SUPER_ADMIN role.

    CRITICAL (REQ-AUTH-015): Role is read from request.user (DB),
    never from JWT payload claims.
    """

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if not request.user.is_active:
            return False
        # Read role from DB via request.user — NOT from JWT payload
        return request.user.role in (
            AdminUser.Role.SUPER_ADMIN,
            AdminUser.Role.ADMIN,
        )
