"""Template filters for group-based access control in templates."""

from __future__ import annotations

from django import template

from core.mixins import user_in_groups

register = template.Library()


@register.filter
def in_group(user, group_names: str) -> bool:
    """``{% if request.user|in_group:"Clinicians,Operations" %}``

    Comma-separated group names; superusers count as members of every
    group; anonymous users belong to none.
    """
    names = [n.strip() for n in (group_names or "").split(",") if n.strip()]
    return user_in_groups(user, names)
