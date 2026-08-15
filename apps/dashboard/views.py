from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.dashboard.mongo_auth import (
    create_user, user_exists, authenticate,
    mongo_login, mongo_logout,
    get_all_users,
)
from apps.dashboard.mongo_models import (
    get_tool_privs_map, get_all_tool_privs, toggle_tool_priv,
)
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


def guest_tools(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'guest_tools.html')


def dashboard(request):
    try:
        stats = get_stats()
        recent_jobs = get_recent_jobs(10)
    except Exception:
        stats = {'total_jobs': 0, 'by_tool': []}
        recent_jobs = []
    try:
        tool_privs = get_tool_privs_map()
    except Exception:
        tool_privs = {}
    return render(request, 'dashboard.html', {
        'stats': stats,
        'recent_jobs': recent_jobs,
        'tool_privs': tool_privs,
    })


def logout_view(request):
    mongo_logout(request)
    return redirect('/')


@require_POST
def ajax_register(request):
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
    if user_exists(username):
        return JsonResponse({'ok': False, 'error': 'Username already taken.'}, status=400)
    user = create_user(username=username, email=email, password=password)
    mongo_login(request, user)
    return JsonResponse({'ok': True})


@require_POST
def ajax_login(request):
    if request.user.is_authenticated:
        return JsonResponse({'ok': True})
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    user = authenticate(username=username, password=password)
    if user is None:
        return JsonResponse({'ok': False, 'error': 'Incorrect username or password.'}, status=401)
    mongo_login(request, user)
    return JsonResponse({'ok': True})


def _superadmin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return redirect('/')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@_superadmin_required
def admin_panel(request):
    tools = get_all_tool_privs()
    users = get_all_users()
    categories = {}
    for t in tools:
        categories.setdefault(t['category'], []).append(t)
    return render(request, 'admin_panel.html', {
        'tools_by_category': categories,
        'users': users,
        'total_users': len(users),
    })


@_superadmin_required
@require_POST
def toggle_tool_privilege(request, slug):
    new_val = toggle_tool_priv(slug)
    if new_val is None:
        return JsonResponse({'ok': False}, status=404)
    return JsonResponse({'ok': True, 'requires_login': new_val})
