"""
ZayroDocX — central feature-gate configuration.

Edit this file to change which tools each plan can access, usage limits,
and popup timing. Changes propagate everywhere automatically.
"""

# ── Tool access sets ─────────────────────────────────────────────────────────

# No account required
GUEST_TOOLS = {
    'merge-pdf', 'split-pdf', 'remove-pages', 'extract-pages',
    'compress-pdf', 'rotate-pdf', 'add-page-numbers', 'watermark-pdf',
    'sign-pdf', 'crop-pdf', 'protect-pdf', 'unlock-pdf',
    'word-to-pdf', 'pptx-to-pdf', 'excel-to-pdf', 'html-to-pdf',
    'jpg-to-pdf', 'scan-to-pdf', 'pdf-to-jpg', 'pdf-to-word',
    'pdf-to-pptx', 'pdf-to-excel',
    'compress-image', 'resize-image', 'crop-image', 'rotate-image',
    'convert-to-jpg', 'convert-from-jpg', 'watermark-image', 'meme-generator',
}

# Free account: OCR + AI tools + everything guests get
FREE_TOOLS = GUEST_TOOLS | {
    'ocr-pdf', 'invoice-extractor', 'ai-summarizer', 'translate-pdf', 'redact-pdf',
    'image-to-text', 'upscale-image', 'remove-background', 'blur-face', 'photo-blue',
    'connectspace', 'ai-resume-analyzer', 'product-recommender', 'pdf-chat',
}

# Plus/Pro: premium tools on top of free
PLUS_TOOLS = FREE_TOOLS | {
    'zayrodesk', 'zayro-eye',
}

PRO_TOOLS = PLUS_TOOLS  # expand here as premium features are added

# ── Daily usage limits ───────────────────────────────────────────────────────
# Format: {tool_slug: {'daily': N}}  — missing slug = unlimited for that plan.

PLAN_LIMITS = {
    'guest': {},
    'free': {
        'ocr-pdf':             {'daily': 10},
        'ai-summarizer':       {'daily': 5},
        'translate-pdf':       {'daily': 5},
        'invoice-extractor':   {'daily': 10},
        'remove-background':   {'daily': 10},
        'upscale-image':       {'daily': 10},
        'pdf-chat':            {'daily': 5},
        'ai-resume-analyzer':  {'daily': 5},
        'product-recommender': {'daily': 10},
        'blur-face':           {'daily': 20},
        'image-to-text':       {'daily': 20},
    },
    'plus': {
        'ocr-pdf':             {'daily': 100},
        'ai-summarizer':       {'daily': 50},
        'translate-pdf':       {'daily': 50},
        'invoice-extractor':   {'daily': 100},
        'remove-background':   {'daily': 100},
        'upscale-image':       {'daily': 100},
        'pdf-chat':            {'daily': 50},
        'ai-resume-analyzer':  {'daily': 50},
        'product-recommender': {'daily': 100},
        'blur-face':           {'daily': 200},
        'image-to-text':       {'daily': 200},
    },
    'pro': {},  # no limits
}

# Plan → allowed tool set (used by check_access)
PLAN_TOOLS = {
    'guest': GUEST_TOOLS,
    'free':  FREE_TOOLS,
    'plus':  PLUS_TOOLS,
    'pro':   PRO_TOOLS,
}

# ── Signup popup timing (milliseconds) ──────────────────────────────────────
# Change here — propagates to every page via the auth_context processor.

POPUP_CONFIG = {
    'initial_delay_ms':      10_000,  # first show: 10 s after page load
    'redisplay_delay_ms':    10_000,  # re-show: 10 s after each dismiss
    'max_shows_per_session':   9999,  # effectively unlimited until login
}
