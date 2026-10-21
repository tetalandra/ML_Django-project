"""Extra variables available in every template."""

SITE_BRANDING = {
    "SITE_NAME": "Riverside Hospital Manager",
    "SITE_TAGLINE": "Django + TextTools demo application",
}


def site_branding(request):
    return dict(SITE_BRANDING)
