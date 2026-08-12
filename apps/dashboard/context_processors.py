from django.conf import settings
from .gates import POPUP_CONFIG
from .access import get_user_plan


def auth_context(request):
    """Inject plan info and popup timing into every template context."""
    return {
        'user_plan': get_user_plan(request),
        'popup_config': POPUP_CONFIG,
        'google_oauth_enabled': bool(getattr(settings, 'GOOGLE_CLIENT_ID', '')),
    }
