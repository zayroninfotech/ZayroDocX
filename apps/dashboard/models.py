import datetime
from django.db import models
from django.contrib.auth.models import User


class ToolPrivilege(models.Model):
    slug = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=60)
    requires_login = models.BooleanField(default=False)
    icon = models.CharField(max_length=80, default='fa-file-pdf')

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('plus', 'Plus'),
        ('pro',  'Pro'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default='free')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} ({self.plan})'


class ToolUsage(models.Model):
    """Daily per-user usage counter for rate-limited tools."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tool_usages')
    tool_slug = models.CharField(max_length=80)
    date = models.DateField(default=datetime.date.today)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'tool_slug', 'date')

    def __str__(self):
        return f'{self.user.username}/{self.tool_slug}/{self.date}: {self.count}'


class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ('open',        'Open'),
        ('in_progress', 'In Progress'),
        ('resolved',    'Resolved'),
        ('closed',      'Closed'),
    ]
    VALID_ISSUE_TYPES = {
        'Getting Started', 'PDF Tools', 'OCR & AI',
        'Account & Billing', 'Troubleshooting', 'Other',
    }

    user        = models.ForeignKey(User, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='support_tickets')
    name        = models.CharField(max_length=200)
    email       = models.EmailField(max_length=254)
    issue_type  = models.CharField(max_length=100)
    related_tool = models.CharField(max_length=100, blank=True)
    description = models.TextField(max_length=5000)
    attachment  = models.FileField(upload_to='support/', blank=True, null=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'#{self.pk} {self.issue_type} — {self.email}'


class Suggestion(models.Model):
    STATUS_CHOICES = [
        ('new',       'New'),
        ('reviewing', 'Reviewing'),
        ('planned',   'Planned'),
        ('completed', 'Completed'),
        ('declined',  'Declined'),
    ]
    CATEGORY_CHOICES = [
        ('new_tool',     'New Tool'),
        ('improvement',  'Existing Tool Improvement'),
        ('ocr_ai',       'OCR / AI'),
        ('pdf_workflow',  'PDF Workflow'),
        ('image_tools',  'Image Tools'),
        ('account',      'Account / Billing'),
        ('other',        'Other'),
    ]
    VALID_CATEGORIES = {v for v, _ in CATEGORY_CHOICES}

    user        = models.ForeignKey(User, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='suggestions')
    user_email  = models.EmailField(max_length=254, blank=True)
    title       = models.CharField(max_length=200)
    description = models.TextField(max_length=2000)
    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    admin_notes = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'#{self.pk} {self.title}'
