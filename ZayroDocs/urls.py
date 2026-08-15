from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
import mimetypes, os
from django.http import FileResponse, Http404
from apps.dashboard.views import logout_view


def _serve_output(request, path):
    safe = os.path.normpath(path).lstrip('/\')
    if '..' in safe.split(os.sep):
        raise Http404
    full = os.path.join(settings.MEDIA_ROOT, 'outputs', safe)
    if not os.path.isfile(full):
        raise Http404
    mime, _ = mimetypes.guess_type(full)
    return FileResponse(open(full, 'rb'), content_type=mime or 'application/octet-stream')


urlpatterns = [
    path('login/',    RedirectView.as_view(url='/', permanent=False), name='login'),
    path('register/', RedirectView.as_view(url='/', permanent=False), name='register'),
    path('logout/',   logout_view, name='logout'),
    path('', include('apps.dashboard.urls')),
    path('tools/', include('apps.pdf_tools.urls')),
    path('media/outputs/<path:path>', _serve_output),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
