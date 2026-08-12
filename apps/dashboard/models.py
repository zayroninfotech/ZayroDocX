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
