"""Template filters that expose our texttools package to Django templates."""

from __future__ import annotations

import texttools
from django import template

register = template.Library()


@register.filter
def word_count(text: str) -> int:
    """``{{ note.body|word_count }}``"""
    return texttools.count_words(text or "")


@register.filter
def char_count(text: str) -> int:
    """``{{ note.body|char_count }}``"""
    return texttools.count_characters(text or "")


@register.filter
def smart_title(text: str) -> str:
    """``{{ note.body|smart_title }}``"""
    return texttools.capitalize_words(text or "")


@register.filter
def snippet(text: str, length: int = 100) -> str:
    """``{{ note.body|snippet:80 }}``"""
    return texttools.truncate(text or "", length=int(length))


@register.filter
def is_palindrome(text: str) -> bool:
    """``{{ patient.last_name|is_palindrome }}``"""
    return texttools.is_palindrome(text or "")


@register.simple_tag
def texttools_version() -> str:
    """``{% texttools_version %}``"""
    return texttools.__version__
