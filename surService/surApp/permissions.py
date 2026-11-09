from rest_framework.permissions import BasePermission


class IsVotingAuthor(BasePermission):
    """Object-level protection in addition to the owner-filtered queryset."""

    def has_object_permission(self, request, view, obj):
        return obj.author_id == request.user.pk
