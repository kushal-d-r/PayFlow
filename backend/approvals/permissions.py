
from rest_framework.permissions import BasePermission


class IsApprovalAdmin(BasePermission):
    """
    Only ADMIN users or Django superusers can manage approval rules.
    """

    message = "Only administrators can manage approval rules."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.role == "ADMIN"
            )
        )
