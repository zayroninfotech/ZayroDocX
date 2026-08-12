"""
Access-control helpers — use these in views and URL wrappers.
"""
import datetime
from .gates import PLAN_TOOLS, PLAN_LIMITS


def get_user_plan(request):
    """Return 'guest', 'free', 'plus', or 'pro' for the current request."""
    if not request.user.is_authenticated:
        return 'guest'
    try:
        return request.user.profile.plan
    except Exception:
        return 'free'


def _today_count(user, slug):
    from .models import ToolUsage
    today = datetime.date.today()
    obj = ToolUsage.objects.filter(user=user, tool_slug=slug, date=today).first()
    return obj.count if obj else 0


def check_access(request, slug):
    """
    Returns (status, message).
    status: 'ok' | 'login_required' | 'upgrade_required' | 'limit_reached'
    """
    plan = get_user_plan(request)
    allowed = PLAN_TOOLS.get(plan, set())

    if slug not in allowed:
        if plan == 'guest':
            return 'login_required', 'Create a free account to use this tool.'
        return 'upgrade_required', 'Upgrade your plan to access this tool.'

    if request.user.is_authenticated:
        limits = PLAN_LIMITS.get(plan, {}).get(slug, {})
        daily = limits.get('daily')
        if daily is not None and _today_count(request.user, slug) >= daily:
            return 'limit_reached', f'Daily limit of {daily} uses reached. Upgrade for more.'

    return 'ok', ''


def record_usage(request, slug):
    """Increment today's usage counter for this user + tool (no-op for guests)."""
    if not request.user.is_authenticated:
        return
    from .models import ToolUsage
    today = datetime.date.today()
    obj, created = ToolUsage.objects.get_or_create(
        user=request.user, tool_slug=slug, date=today,
        defaults={'count': 0},
    )
    if not created:
        ToolUsage.objects.filter(pk=obj.pk).update(count=obj.count + 1)
    else:
        ToolUsage.objects.filter(pk=obj.pk).update(count=1)
