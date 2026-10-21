"""Group-based access control helpers.

Two groups exist in this project (created by ``manage.py setup_groups``):

* **Clinicians**  — patients, appointments and clinical notes.
* **Operations**  — doctors, departments and appointment oversight.

Views declare which groups may open them via ``GroupRequiredMixin``;
templates ask the same question with the ``in_group`` filter
(``{% if request.user|in_group:"Clinicians" %}``). Superusers always pass.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect


def user_in_groups(user, names: list[str] | tuple[str, ...]) -> bool:
    """True when ``user`` belongs to one of ``names`` (superusers: always)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=list(names)).exists()


class GroupRequiredMixin(AccessMixin):
    """Allow only users who belong to one of ``allowed_groups``.

    * Anonymous visitors are sent to the login page (``LOGIN_URL``).
    * Authenticated users outside the allowed groups get a friendly flash
      message and are sent back to the dashboard instead of a raw 403.
    * Superusers bypass the check.
    """

    allowed_groups: tuple[str, ...] = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not user_in_groups(request.user, self.allowed_groups):
            messages.error(
                request,
                "Your group does not have access to this section "
                f"(allowed: {', '.join(self.allowed_groups)}). "
                "Ask an administrator to move your account to that group.",
            )
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)
