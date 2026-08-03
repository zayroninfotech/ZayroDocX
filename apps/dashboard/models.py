from django.db import models


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
