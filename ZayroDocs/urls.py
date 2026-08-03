from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
import mimetypes
import os
from django.http import FileResponse, Http404

def _serve_output(request, path):
    """Serve files from MEDIA_ROOT/outputs/ only — no directory traversal."""
    safe = os.path.normpath(path).lstrip('/\\')
    if '..' in safe.split(os.sep):
        raise Http404
    full = os.path.join(settings.MEDIA_ROOT, 'outputs', safe)
    if not os.path.isfile(full):
        raise Http404
    mime, _ = mimetypes.guess_type(full)
    return FileResponse(open(full, 'rb'), content_type=mime or 'application/octet-stream')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('', include('apps.dashboard.urls')),
    path('tools/', include('apps.pdf_tools.urls')),
    path('media/outputs/<path:path>', _serve_output),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
