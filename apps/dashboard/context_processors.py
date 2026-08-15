from .gates import POPUP_CONFIG


def auth_context(request):
    return {
        'user_plan': getattr(request.user, 'plan', 'guest'),
        'popup_config': POPUP_CONFIG,
    }
