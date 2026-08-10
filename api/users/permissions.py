# users/permissions.py
from rest_framework import permissions
from django.contrib.auth import get_user_model

# Get the custom user model with the 'Role' attribute
User = get_user_model()

class IsAdmin(permissions.BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.ADMIN


class IsSelfOrAdmin(permissions.BasePermission):
    """
    Allows access to an object only if the user is an admin or the object owner.
    """
    def has_object_permission(self, request, view, obj):
        # Admins have full access
        if request.user.role == User.Role.ADMIN:
            return True

        # Only the object's owner can modify or view it
        return obj == request.user

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allows safe methods (GET, HEAD, OPTIONS) for any authenticated user,
    but write methods (POST, PUT, DELETE) only for admins.
    """
    def has_permission(self, request, view):
        # Read-only permissions are allowed for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        # Write permissions are only allowed for admins
        return request.user.is_authenticated and request.user.role == User.Role.ADMIN