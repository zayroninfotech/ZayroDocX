import os
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


def support(request):
    return render(request, 'support.html')


@require_POST
def submit_support(request):
    from apps.dashboard.models import SupportTicket

    name         = request.POST.get('name', '').strip()
    email        = request.POST.get('email', '').strip()
    issue_type   = request.POST.get('issue_type', '').strip()
    related_tool = request.POST.get('related_tool', '').strip()
    description  = request.POST.get('description', '').strip()

    errors = {}
    if not name:
        errors['name'] = 'Full name is required.'
    elif len(name) > 200:
        errors['name'] = 'Name must be 200 characters or fewer.'

    if not email:
        errors['email'] = 'Email address is required.'
    elif len(email) > 254 or '@' not in email:
        errors['email'] = 'Enter a valid email address.'

    if not issue_type:
        errors['issue_type'] = 'Please select an issue type.'
    elif issue_type not in SupportTicket.VALID_ISSUE_TYPES:
        errors['issue_type'] = 'Invalid issue type selected.'

    if not description:
        errors['description'] = 'Please describe the issue.'
    elif len(description) > 5000:
        errors['description'] = 'Description must be 5,000 characters or fewer.'

    # Validate optional file attachment
    attachment = request.FILES.get('attachment')
    if attachment:
        allowed_types = {'image/png', 'image/jpeg', 'application/pdf'}
        allowed_exts  = {'.png', '.jpg', '.jpeg', '.pdf'}
        ext = os.path.splitext(attachment.name)[1].lower()
        if attachment.content_type not in allowed_types or ext not in allowed_exts:
            errors['attachment'] = 'Only PNG, JPG, and PDF files are allowed.'
        elif attachment.size > 10 * 1024 * 1024:
            errors['attachment'] = 'Attachment must be under 10 MB.'

    if errors:
        return JsonResponse({'ok': False, 'errors': errors}, status=400)

    ticket = SupportTicket(
        name=name,
        email=email,
        issue_type=issue_type,
        related_tool=related_tool,
        description=description,
        status='open',
    )
    if request.user.is_authenticated:
        ticket.user = request.user
    if attachment and 'attachment' not in errors:
        ticket.attachment = attachment
    ticket.save()

    return JsonResponse({'ok': True, 'ticket_id': ticket.pk})


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


@require_POST
def submit_suggestion(request):
    from apps.dashboard.models import Suggestion

    title       = request.POST.get('sg_title', '').strip()
    description = request.POST.get('sg_description', '').strip()
    category    = request.POST.get('sg_category', 'other').strip()

    errors = {}
    if not title:
        errors['sg_title'] = 'A title is required.'
    elif len(title) > 200:
        errors['sg_title'] = 'Title must be 200 characters or fewer.'

    if not description:
        errors['sg_description'] = 'Please describe your idea.'
    elif len(description) > 2000:
        errors['sg_description'] = 'Description must be 2,000 characters or fewer.'

    if category not in Suggestion.VALID_CATEGORIES:
        category = 'other'

    if errors:
        return JsonResponse({'ok': False, 'errors': errors}, status=400)

    suggestion = Suggestion(title=title, description=description, category=category)
    if request.user.is_authenticated:
        suggestion.user = request.user
        suggestion.user_email = request.user.email
    suggestion.save()
    return JsonResponse({'ok': True, 'id': suggestion.pk})


@superadmin_required
@require_POST
def update_suggestion(request, pk):
    from apps.dashboard.models import Suggestion
    try:
        suggestion = Suggestion.objects.get(pk=pk)
    except Suggestion.DoesNotExist:
        return JsonResponse({'ok': False}, status=404)

    valid_statuses = {v for v, _ in Suggestion.STATUS_CHOICES}
    status = request.POST.get('status', '').strip()
    admin_notes = request.POST.get('admin_notes', suggestion.admin_notes).strip()

    if status and status in valid_statuses:
        suggestion.status = status
    suggestion.admin_notes = admin_notes[:2000]
    suggestion.save()
    return JsonResponse({'ok': True, 'status': suggestion.status,
                         'status_display': suggestion.get_status_display()})


@superadmin_required
def admin_panel(request):
    from apps.dashboard.models import ToolPrivilege, SupportTicket, Suggestion
    tools = ToolPrivilege.objects.all()
    users = User.objects.all().order_by('-date_joined')
    categories = {}
    for t in tools:
        categories.setdefault(t.category, []).append(t)

    tickets     = SupportTicket.objects.select_related('user').all()
    suggestions = Suggestion.objects.select_related('user').all()

    context = {
        'tools_by_category': categories,
        'users': users,
        'total_users': users.count(),
        'tickets': tickets,
        'open_ticket_count': tickets.filter(status='open').count(),
        'suggestions': suggestions,
        'new_suggestion_count': suggestions.filter(status='new').count(),
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
