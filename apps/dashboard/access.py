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
    plan = get_user_plan(request)
    allowed = PLAN_TOOLS.get(plan, set())
    if slug not in allowed:
        if plan == 'guest':
            return 'login_required', 'Create a free account to use this tool.'
        return 'upgrade_required', 'Upgrade your plan to access this tool.'
    if request.user.is_authenticated:
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
