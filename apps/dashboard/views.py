from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, authenticate
from apps.pdf_tools.mongo_db import get_recent_jobs, get_stats


def about(request):
    return render(request, 'about.html')


def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('/')


def dashboard(request):
    try:
        stats = get_stats()
        recent_jobs = get_recent_jobs(10)
    except Exception:
        stats = {'total_jobs': 0, 'by_tool': []}
        recent_jobs = []

    # Build a slug→requires_login map for template use
    try:
        from apps.dashboard.models import ToolPrivilege
        tool_privs = {t.slug.replace('-', '_'): t.requires_login for t in ToolPrivilege.objects.all()}
    except Exception:
        tool_privs = {}

    context = {
        'stats': stats,
        'recent_jobs': recent_jobs,
        'tool_privs': tool_privs,
    }
    return render(request, 'dashboard.html', context)


@require_POST
def ajax_register(request):
    """Popup inline registration — returns JSON, no page redirect."""
    if request.user.is_authenticated:
        return JsonResponse({'ok': True})
    username  = request.POST.get('username', '').strip()
    email     = request.POST.get('email', '').strip()
    password  = request.POST.get('password', '')
    password2 = request.POST.get('password2', '')
    if not username or not password:
        return JsonResponse({'ok': False, 'error': 'Username and password are required.'}, status=400)
    if len(password) < 8:
        return JsonResponse({'ok': False, 'error': 'Password must be at least 8 characters.'}, status=400)
    if password != password2:
        return JsonResponse({'ok': False, 'error': 'Passwords do not match.'}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({'ok': False, 'error': 'Username already taken.'}, status=400)
    user = User.objects.create_user(username=username, email=email, password=password)
    login(request, user)
    return JsonResponse({'ok': True})


@require_POST
def ajax_login(request):
    """Popup inline login — returns JSON, no page redirect."""
    if request.user.is_authenticated:
        return JsonResponse({'ok': True})
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({'ok': False, 'error': 'Incorrect username or password.'}, status=401)
    login(request, user)
    return JsonResponse({'ok': True})


def superadmin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return redirect('/')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@superadmin_required
def admin_panel(request):
    from apps.dashboard.models import ToolPrivilege
    tools = ToolPrivilege.objects.all()
    users = User.objects.all().order_by('-date_joined')
    categories = {}
    for t in tools:
        categories.setdefault(t.category, []).append(t)

    context = {
        'tools_by_category': categories,
        'users': users,
        'total_users': users.count(),
    }
    return render(request, 'admin_panel.html', context)


@superadmin_required
@require_POST
def toggle_tool_privilege(request, slug):
    from apps.dashboard.models import ToolPrivilege
    try:
        tool = ToolPrivilege.objects.get(slug=slug)
        tool.requires_login = not tool.requires_login
        tool.save()
        return JsonResponse({'ok': True, 'requires_login': tool.requires_login})
    except ToolPrivilege.DoesNotExist:
        return JsonResponse({'ok': False}, status=404)
