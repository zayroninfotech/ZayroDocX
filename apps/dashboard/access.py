"""
Access-control helpers — use these in views and URL wrappers.
"""
from .gates import PLAN_TOOLS, PLAN_LIMITS


def get_user_plan(request):
    if not request.user.is_authenticated:
        return 'guest'
    return getattr(request.user, 'plan', 'free')


def _today_count(user_id, slug):
    from .mongo_models import get_today_usage
    return get_today_usage(user_id, slug)


def check_access(request, slug):
    from .mongo_models import get_tool_priv
    priv = get_tool_priv(slug)

    if not request.user.is_authenticated:
        # Admin toggle is the single source of truth for guest access.
        # Red (requires_login=True)  → popup required.
        # Green (requires_login=False) → allow guest through, no popup.
        if priv and priv.get('requires_login'):
            return 'login_required', 'Sign in to use this tool.'
        if priv and not priv.get('requires_login'):
            return 'ok', ''
        # Tool not in DB — fall back to plan-based gate.
        plan = get_user_plan(request)
        allowed = PLAN_TOOLS.get(plan, set())
        if slug not in allowed:
            return 'login_required', 'Create a free account to use this tool.'
        return 'ok', ''

    # Authenticated users: check plan tier.
    plan = get_user_plan(request)
    allowed = PLAN_TOOLS.get(plan, set())
    if slug not in allowed:
        return 'upgrade_required', 'Upgrade your plan to access this tool.'
    # Superusers and staff always get unlimited access — no daily cap.
    if getattr(request.user, 'is_superuser', False) or getattr(request.user, 'is_staff', False):
        return 'ok', ''
    limits = PLAN_LIMITS.get(plan, {}).get(slug, {})
    daily = limits.get('daily')
    if daily is not None and _today_count(request.user.id, slug) >= daily:
        return 'limit_reached', f'Daily limit of {daily} uses reached. Upgrade for more.'
    return 'ok', ''


def record_usage(request, slug):
    if not request.user.is_authenticated:
        return
    from .mongo_models import record_tool_usage
    record_tool_usage(request.user.id, slug)
