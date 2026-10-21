"""Insight helpers: small analytics that lean on our texttools package."""

from __future__ import annotations

import texttools
from django.db.models import CharField, Value
from django.db.models.functions import Concat

from records.models import Appointment, MedicalNote, Patient


def dashboard_insights() -> list[dict]:
    """Build a handful of interesting facts for the dashboard.

    Uses Django ORM aggregates *and* our own ``texttools`` package on top of
    the retrieved text (word frequencies of appointment reasons, note stats).
    """
    insights: list[dict] = []

    # 1. Busiest appointment reasons, via texttools word frequencies over all reasons.
    reasons = " ".join(Appointment.objects.exclude(reason="").values_list("reason", flat=True))
    if reasons:
        top = texttools.most_common_words(reasons, limit=3, ignore_stopwords=True)
        insights.append({
            "label": "Most common visit reasons",
            "value": ", ".join(top) if top else "—",
        })

    # 2. Clinical note corpus stats with texttools.
    notes = list(MedicalNote.objects.values_list("body", flat=True))
    if notes:
        corpus = " ".join(notes)
        longest = max(notes, key=len)
        avg = sum(texttools.count_words(n) for n in notes) // len(notes)
        insights.append({
            "label": "Clinical notes word total",
            "value": f"{texttools.count_words(corpus):,} words across all notes",
        })
        insights.append({
            "label": "Longest single note",
            "value": f"{texttools.count_characters(longest):,} characters",
        })
        insights.append({"label": "Average note length", "value": f"{avg} words"})

    # 3. Patients whose surname reads the same backwards (fun texttools demo).
    palindromic = [
        name
        for name in Patient.objects.values_list("last_name", flat=True)
        if texttools.is_palindrome(name)
    ]
    insights.append({
        "label": "Palindromic surnames on file",
        "value": ", ".join(sorted(set(palindromic))) if palindromic else "None yet",
    })

    return insights
