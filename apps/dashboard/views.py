from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import os

from apps.dashboard.mongo_auth import (
    create_user, user_exists, authenticate,
    mongo_login, mongo_logout,
    get_all_users,
)
from apps.dashboard.mongo_models import (
    get_tool_privs_map, get_all_tool_privs, toggle_tool_priv,
    create_ticket, get_all_tickets, create_suggestion, get_all_suggestions, update_suggestion_status,
    get_visitor_sessions, get_visitor_stats,
    delete_visitor_session, delete_all_visitor_sessions,
)
from apps.pdf_tools.mongo_db import get_recent_jobs, get_stats


def about(request):
    return render(request, 'about.html')


def _locked_slugs_json():
    import json
    try:
        slugs = [d['slug'] for d in get_all_tool_privs() if d.get('requires_login')]
    except Exception:
        slugs = []
    return json.dumps(slugs)


def landing(request):
    return render(request, 'landing.html', {'locked_slugs_json': _locked_slugs_json()})


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('/')


def guest_tools(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'guest_tools.html', {'locked_slugs_json': _locked_slugs_json()})


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

    raw_tickets     = get_all_tickets()
    raw_suggestions = get_all_suggestions()

    _CATEGORY_LABELS = {
        'general': 'General', 'feature': 'Feature', 'bug': 'Bug',
        'ui': 'UI/UX', 'performance': 'Performance', 'other': 'Other',
    }
    _STATUS_LABELS = {
        'new': 'New', 'reviewing': 'Reviewing', 'planned': 'Planned',
        'completed': 'Completed', 'declined': 'Declined',
    }

    tickets = []
    for t in raw_tickets:
        t['pk'] = str(t['_id'])
        tickets.append(t)

    suggestions = []
    for s in raw_suggestions:
        s['pk']               = str(s['_id'])
        s['category_display'] = _CATEGORY_LABELS.get(s.get('category', ''), s.get('category', ''))
        s['status_display']   = _STATUS_LABELS.get(s.get('status', ''), s.get('status', ''))
        s['submitter']        = s.get('user_email') or 'Guest'
        suggestions.append(s)

    open_ticket_count   = sum(1 for t in tickets if t.get('status') == 'open')
    new_suggestion_count = sum(1 for s in suggestions if s.get('status') == 'new')

    return render(request, 'admin_panel.html', {
        'tools_by_category':    categories,
        'users':                users,
        'total_users':          len(users),
        'visitor_stats':        get_visitor_stats(),
        'recent_sessions':      get_visitor_sessions(limit=50),
        'tickets':              tickets,
        'suggestions':          suggestions,
        'open_ticket_count':    open_ticket_count,
        'new_suggestion_count': new_suggestion_count,
    })


@_superadmin_required
@require_POST
def toggle_tool_privilege(request, slug):
    new_val = toggle_tool_priv(slug)
    if new_val is None:
        return JsonResponse({'ok': False}, status=404)
    return JsonResponse({'ok': True, 'requires_login': new_val})


@_superadmin_required
@require_POST
def delete_session(request, session_key):
    delete_visitor_session(session_key)
    return JsonResponse({'ok': True})


@_superadmin_required
@require_POST
def delete_all_sessions(request):
    delete_all_visitor_sessions()
    return JsonResponse({'ok': True})


@_superadmin_required
def media_browser(request):
    from django.conf import settings
    media_root = str(settings.MEDIA_ROOT)

    def _fmt(size):
        for unit in ('B', 'KB', 'MB', 'GB'):
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'

    def _walk(path, rel=''):
        entries = {'folders': [], 'files': []}
        try:
            items = sorted(os.listdir(path))
        except PermissionError:
            return entries
        for name in items:
            full = os.path.join(path, name)
            rel_path = os.path.join(rel, name).replace('\\', '/')
            if os.path.isdir(full):
                sub = _walk(full, rel_path)
                total = sum(f['size_raw'] for f in sub['files']) + \
                        sum(f['total_raw'] for f in sub['folders'])
                entries['folders'].append({
                    'name': name,
                    'path': rel_path,
                    'total_raw': total,
                    'total': _fmt(total),
                    'file_count': len(sub['files']) + sum(f['file_count'] for f in sub['folders']),
                    'children': sub,
                })
            else:
                size = os.path.getsize(full)
                mtime = os.path.getmtime(full)
                import datetime
                entries['files'].append({
                    'name': name,
                    'path': rel_path,
                    'size_raw': size,
                    'size': _fmt(size),
                    'modified': datetime.datetime.fromtimestamp(mtime).strftime('%d %b %Y %H:%M'),
                    'ext': os.path.splitext(name)[1].lower().lstrip('.') or 'file',
                })
        return entries

    tree = _walk(media_root)
    total_raw = sum(f['size_raw'] for f in tree['files']) + \
                sum(f['total_raw'] for f in tree['folders'])
    total_files = len(tree['files']) + sum(f['file_count'] for f in tree['folders'])

    return JsonResponse({
        'ok': True,
        'tree': tree,
        'total_size': _fmt(total_raw),
        'total_files': total_files,
    })


@_superadmin_required
@require_POST
def media_delete_file(request):
    from django.conf import settings
    rel_path = request.POST.get('path', '')
    if not rel_path or '..' in rel_path:
        return JsonResponse({'ok': False, 'error': 'Invalid path'}, status=400)
    full_path = os.path.join(str(settings.MEDIA_ROOT), rel_path.lstrip('/'))
    if not os.path.isfile(full_path):
        return JsonResponse({'ok': False, 'error': 'File not found'}, status=404)
    os.remove(full_path)
    return JsonResponse({'ok': True})


@_superadmin_required
@require_POST
def media_delete_all(request):
    from django.conf import settings
    import shutil
    media_root = str(settings.MEDIA_ROOT)
    deleted = 0
    for root, dirs, files in os.walk(media_root):
        for fname in files:
            try:
                os.remove(os.path.join(root, fname))
                deleted += 1
            except Exception:
                pass
    return JsonResponse({'ok': True, 'deleted': deleted})


def support(request):
    return render(request, 'support.html')


@require_POST
def submit_support(request):
    user_id = request.user.id if request.user.is_authenticated else None
    name        = request.POST.get('name', '').strip()
    email       = request.POST.get('email', '').strip()
    issue_type  = request.POST.get('issue_type', '').strip()
    related_tool = request.POST.get('related_tool', '').strip()
    description = request.POST.get('description', '').strip()
    if not name or not email or not issue_type or not description:
        return JsonResponse({'ok': False, 'error': 'Please fill in all required fields.'}, status=400)
    create_ticket(user_id, name, email, issue_type, related_tool, description)
    return JsonResponse({'ok': True})


@require_POST
def submit_suggestion(request):
    user_id    = request.user.id if request.user.is_authenticated else None
    user_email = request.user.email if request.user.is_authenticated else request.POST.get('email', '')
    title       = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    category    = request.POST.get('category', 'other').strip()
    if not title or not description:
        return JsonResponse({'ok': False, 'error': 'Title and description are required.'}, status=400)
    create_suggestion(user_id, user_email, title, description, category)
    return JsonResponse({'ok': True})


@_superadmin_required
@require_POST
def update_suggestion(request, pk):
    status = request.POST.get('status', '').strip()
    admin_notes = request.POST.get('admin_notes', '').strip()
    if not status:
        return JsonResponse({'ok': False, 'error': 'Status is required.'}, status=400)
    _STATUS_LABELS = {
        'new': 'New', 'reviewing': 'Reviewing', 'planned': 'Planned',
        'completed': 'Completed', 'declined': 'Declined',
    }
    try:
        update_suggestion_status(pk, status, admin_notes)
        return JsonResponse({'ok': True, 'status': status, 'status_display': _STATUS_LABELS.get(status, status)})
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Update failed.'}, status=500)
