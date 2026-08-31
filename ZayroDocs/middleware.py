import logging
import time
import threading

audit_log = logging.getLogger('ZayroDocs.audit')


class SecurityHeadersMiddleware:
    """
    Layer 7 — Adds security response headers not covered by Django's built-in
    SecurityMiddleware: Content-Security-Policy, Referrer-Policy,
    Permissions-Policy, Cross-Origin-Opener-Policy.
    """

    # CSP allows Google Fonts + Font Awesome CDN (used in base.html).
    # unsafe-inline is required because templates use {% block extra_js %} inline scripts.
    _CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com "
            "https://cdnjs.cloudflare.com; "
        "font-src 'self' "
            "https://fonts.gstatic.com "
            "https://cdnjs.cloudflare.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none';"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Content-Security-Policy'] = self._CSP
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = (
            'camera=(), microphone=(), geolocation=(), '
            'payment=(), usb=(), bluetooth=()'
        )
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        response['Cross-Origin-Resource-Policy'] = 'same-origin'
        return response


class AuditLogMiddleware:
    """
    Layer 7 / Layer 5 — Logs every request with IP, method, path,
    user-agent, response status, and processing time.
    Provides an audit trail for all file upload and tool usage events.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    _SKIP_PATHS = {'/favicon.ico', '/robots.txt'}

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)

        if request.path in self._SKIP_PATHS:
            return response

        duration_ms = round((time.monotonic() - start) * 1000)
        ip = self._get_client_ip(request)

        audit_log.info(
            '%s %s %s [%s] %dms ua="%s"',
            request.method,
            request.path,
            response.status_code,
            ip,
            duration_ms,
            request.META.get('HTTP_USER_AGENT', '-')[:200],
        )

        return response

    @staticmethod
    def _get_client_ip(request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            # Take only the first IP — leftmost is the real client
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


class VisitorSessionMiddleware:
    """
    Automatically records every visitor's session in the MongoDB
    `visitor_sessions` collection on each page request.

    Captures: session key, IP address, user agent, current path,
    username (if logged in), session start time, last-seen time,
    page view count, and list of unique pages visited.

    Skipped for: static files, media files, and AJAX/API endpoints.
    """

    _SKIP_PREFIXES = ('/static/', '/media/', '/ajax/', '/api/', '/favicon')
    _SKIP_EXTENSIONS = ('.css', '.js', '.png', '.jpg', '.ico', '.woff', '.woff2', '.svg')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            path = request.path

            # Skip static/media/AJAX
            if any(path.startswith(p) for p in self._SKIP_PREFIXES):
                return response
            if any(path.endswith(ext) for ext in self._SKIP_EXTENSIONS):
                return response
            # Skip non-HTML responses (file downloads, JSON)
            content_type = response.get('Content-Type', '')
            if 'text/html' not in content_type and response.status_code == 200:
                return response

            # Use existing session key only — never force session creation
            # (creating a session hits Redis which may be unavailable)
            session_key = request.session.session_key
            if not session_key:
                return response

            ip = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:300]
            username = request.user.username if getattr(request.user, 'is_authenticated', False) else None

            # Run DB write in background thread — zero impact on response time
            threading.Thread(
                target=self._record,
                args=(session_key, ip, user_agent, path, username),
                daemon=True,
            ).start()
        except Exception:
            pass  # Never crash the request over analytics

        return response

    @staticmethod
    def _record(session_key, ip, user_agent, path, username):
        try:
            from apps.dashboard.mongo_models import upsert_visitor_session
            upsert_visitor_session(session_key, ip, user_agent, path, username)
        except Exception:
            pass  # Never crash the request over analytics

    @staticmethod
    def _get_client_ip(request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
