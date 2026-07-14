import logging
import time

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
