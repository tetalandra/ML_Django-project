"""Word-limit validators powered by our own ``texttools`` package.

These run in three places at once:

* inside the CRUD screens (Django ModelForms)
* inside the Django admin (model validators run on ``full_clean``)
* in the browser: the forms copy the limits onto ``data-word-limit`` /
  ``data-word-min`` attributes, so the user sees a live "12 / 50 words"
  counter while typing

The class is used instead of a closure so Django can write it into
migration files (``deconstruct()`` tells the migration writer how to
rebuild the object).
"""

from __future__ import annotations

from django.core.exceptions import ValidationError

import texttools


class WordLimitValidator:
    """Reject text outside a word-count range, counted by ``texttools``."""

    def __init__(self, minimum: int | None = None, maximum: int | None = None):
        self.minimum = minimum
        self.maximum = maximum
        # Read by records.forms.StyledModelForm to expose the live counter.
        if minimum is not None:
            self.min_limit = minimum
        if maximum is not None:
            self.limit = maximum

    def __call__(self, value: str) -> None:
        count = texttools.count_words(value)
        if self.maximum is not None and count > self.maximum:
            raise ValidationError(
                f"Please keep this under {self.maximum} words — texttools counted {count}."
            )
        if self.minimum is not None and count < self.minimum:
            raise ValidationError(
                f"This field needs at least {self.minimum} words — texttools counted {count}."
            )

    def deconstruct(self):
        """Let Django's migration writer serialize this validator."""
        kwargs = {}
        if self.minimum is not None:
            kwargs["minimum"] = self.minimum
        if self.maximum is not None:
            kwargs["maximum"] = self.maximum
        return ("records.validators.WordLimitValidator", [], kwargs)

    def __repr__(self) -> str:
        parts = []
        if self.minimum is not None:
            parts.append(f"minimum={self.minimum}")
        if self.maximum is not None:
            parts.append(f"maximum={self.maximum}")
        return f"WordLimitValidator({', '.join(parts)})"


def max_words(limit: int) -> WordLimitValidator:
    """Allow at most *limit* words (counted by texttools)."""
    return WordLimitValidator(maximum=limit)


def min_words(limit: int) -> WordLimitValidator:
    """Require at least *limit* words (counted by texttools)."""
    return WordLimitValidator(minimum=limit)
