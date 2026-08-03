from django.urls import path
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

# ── Free tool page (no login needed) ─────────────────────────────────────────
def tool_page(template):
    def view(request):
        return render(request, f'pdf_tools/{template}')
    return view

# ── Login-required tool page (redirects guests to login with message) ─────────
def protected_tool_page(template):
    @login_required(login_url='/login/')
    def view(request):
        return render(request, f'pdf_tools/{template}')
    return view

# ── Login-required API (returns 401 JSON for guests) ─────────────────────────
def protected_api(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Login required to use this tool.'}, status=401)
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper

# API views
from apps.pdf_tools.views.merge import merge_pdf
from apps.pdf_tools.views.split import split_pdf
from apps.pdf_tools.views.pages import remove_pages, extract_pages, get_pdf_info
from apps.pdf_tools.views.compress import compress_pdf
from apps.pdf_tools.views.edit_pdf import rotate_pdf, add_page_numbers
from apps.pdf_tools.views.watermark import add_watermark
from apps.pdf_tools.views.sign_pdf import sign_pdf
from apps.pdf_tools.views.ocr_pdf import ocr_pdf, ocr_pdf_stream, ocr_pdf_progress, extract_page, extract_page_ai, extract_statement_summary, extract_invoice, scan_to_pdf, invoice_to_excel, extract_invoice_ai, smart_split_suggest, detect_blank_pages
from apps.pdf_tools.views.convert_to_pdf import word_to_pdf, pptx_to_pdf, excel_to_pdf, html_to_pdf, jpg_to_pdf
from apps.pdf_tools.views.convert_from_pdf import pdf_to_jpg, pdf_to_word, pdf_to_pptx, pdf_to_excel
from apps.pdf_tools.views.ai_summarizer import summarize_pdf
from apps.pdf_tools.views.translate_pdf import translate_pdf
from apps.pdf_tools.views.security import protect_pdf, unlock_pdf, redact_pdf
from apps.pdf_tools.views.crop_pdf import crop_pdf
from apps.pdf_tools.views.thumbnail import pdf_thumbnails
from apps.pdf_tools.views.image_tools import (
    compress_image, resize_image, crop_image, rotate_image,
    convert_to_jpg, convert_from_jpg, watermark_image, meme_generator,
    upscale_image, remove_background, blur_face, img_ocr,
)


urlpatterns = [

    # ── FREE tool pages (no login needed) ────────────────────────────────────
    path('merge-pdf/',          tool_page('merge.html'),        name='merge_pdf_page'),
    path('split-pdf/',          tool_page('split.html'),        name='split_pdf_page'),
    path('rotate-pdf/',         tool_page('rotate.html'),       name='rotate_pdf_page'),
    path('add-page-numbers/',   tool_page('page_numbers.html'), name='page_numbers_page'),
    path('jpg-to-pdf/',         tool_page('jpg_to_pdf.html'),   name='jpg_to_pdf_page'),
    path('pdf-to-jpg/',         tool_page('pdf_to_jpg.html'),   name='pdf_to_jpg_page'),
    path('word-to-pdf/',        tool_page('word_to_pdf.html'),  name='word_to_pdf_page'),
    path('pptx-to-pdf/',        tool_page('pptx_to_pdf.html'),  name='pptx_to_pdf_page'),
    path('excel-to-pdf/',       tool_page('excel_to_pdf.html'), name='excel_to_pdf_page'),
    path('html-to-pdf/',        tool_page('html_to_pdf.html'),  name='html_to_pdf_page'),
    path('compress-image/',     tool_page('img_compress.html'), name='img_compress_page'),
    path('resize-image/',       tool_page('img_resize.html'),   name='img_resize_page'),
    path('rotate-image/',       tool_page('img_rotate.html'),   name='img_rotate_page'),
    path('convert-to-jpg/',     tool_page('img_to_jpg.html'),   name='img_to_jpg_page'),
    path('convert-from-jpg/',   tool_page('img_from_jpg.html'), name='img_from_jpg_page'),

    # ── LOGIN-REQUIRED tool pages ─────────────────────────────────────────────
    path('compress-pdf/',       protected_tool_page('compress.html'),       name='compress_pdf_page'),
    path('remove-pages/',       protected_tool_page('remove_pages.html'),   name='remove_pages_page'),
    path('extract-pages/',      protected_tool_page('extract_pages.html'),  name='extract_pages_page'),
    path('watermark-pdf/',      protected_tool_page('watermark.html'),      name='watermark_pdf_page'),
    path('sign-pdf/',           protected_tool_page('sign.html'),           name='sign_pdf_page'),
    path('ocr-pdf/',            protected_tool_page('ocr.html'),            name='ocr_pdf_page'),
    path('scan-to-pdf/',        protected_tool_page('scan.html'),           name='scan_pdf_page'),
    path('crop-pdf/',           protected_tool_page('crop.html'),           name='crop_pdf_page'),
    path('invoice-extractor/',  protected_tool_page('invoice.html'),        name='invoice_page'),
    path('ai-summarizer/',      protected_tool_page('ai_summarizer.html'),  name='ai_summarizer_page'),
    path('translate-pdf/',      protected_tool_page('translate_pdf.html'),  name='translate_pdf_page'),
    path('pdf-to-word/',        protected_tool_page('pdf_to_word.html'),    name='pdf_to_word_page'),
    path('pdf-to-pptx/',        protected_tool_page('pdf_to_pptx.html'),    name='pdf_to_pptx_page'),
    path('pdf-to-excel/',       protected_tool_page('pdf_to_excel.html'),   name='pdf_to_excel_page'),
    path('protect-pdf/',        protected_tool_page('protect.html'),        name='protect_pdf_page'),
    path('unlock-pdf/',         protected_tool_page('unlock.html'),         name='unlock_pdf_page'),
    path('redact-pdf/',         protected_tool_page('redact.html'),         name='redact_pdf_page'),
    path('crop-image/',         protected_tool_page('img_crop.html'),       name='img_crop_page'),
    path('watermark-image/',    protected_tool_page('img_watermark.html'),  name='img_watermark_page'),
    path('meme-generator/',     protected_tool_page('img_meme.html'),       name='img_meme_page'),
    path('upscale-image/',      protected_tool_page('img_upscale.html'),    name='img_upscale_page'),
    path('remove-background/',  protected_tool_page('img_remove_bg.html'),  name='img_remove_bg_page'),
    path('blur-face/',          protected_tool_page('img_blur_face.html'),  name='img_blur_face_page'),
    path('image-to-text/',      protected_tool_page('img_ocr.html'),        name='img_ocr_page'),

    # ── FREE API endpoints ────────────────────────────────────────────────────
    path('api/merge-pdf/',      merge_pdf,      name='api_merge_pdf'),
    path('api/split-pdf/',      split_pdf,      name='api_split_pdf'),
    path('api/rotate-pdf/',     rotate_pdf,     name='api_rotate_pdf'),
    path('api/add-page-numbers/', add_page_numbers, name='api_page_numbers'),
    path('api/jpg-to-pdf/',     jpg_to_pdf,     name='api_jpg_to_pdf'),
    path('api/pdf-to-jpg/',     pdf_to_jpg,     name='api_pdf_to_jpg'),
    path('api/word-to-pdf/',    word_to_pdf,    name='api_word_to_pdf'),
    path('api/pptx-to-pdf/',    pptx_to_pdf,    name='api_pptx_to_pdf'),
    path('api/excel-to-pdf/',   excel_to_pdf,   name='api_excel_to_pdf'),
    path('api/html-to-pdf/',    html_to_pdf,    name='api_html_to_pdf'),
    path('api/img/compress/',   compress_image, name='api_img_compress'),
    path('api/img/resize/',     resize_image,   name='api_img_resize'),
    path('api/img/rotate/',     rotate_image,   name='api_img_rotate'),
    path('api/img/to-jpg/',     convert_to_jpg, name='api_img_to_jpg'),
    path('api/img/from-jpg/',   convert_from_jpg, name='api_img_from_jpg'),
    path('api/get-pdf-info/',   get_pdf_info,   name='api_pdf_info'),
    path('api/pdf-thumbnails/', pdf_thumbnails, name='api_pdf_thumbnails'),

    # ── LOGIN-REQUIRED API endpoints ──────────────────────────────────────────
    path('api/compress-pdf/',               protected_api(compress_pdf),                name='api_compress_pdf'),
    path('api/remove-pages/',               protected_api(remove_pages),                name='api_remove_pages'),
    path('api/extract-pages/',              protected_api(extract_pages),               name='api_extract_pages'),
    path('api/watermark-pdf/',              protected_api(add_watermark),               name='api_watermark'),
    path('api/sign-pdf/',                   protected_api(sign_pdf),                    name='api_sign_pdf'),
    path('api/ocr-pdf/',                    protected_api(ocr_pdf),                     name='api_ocr_pdf'),
    path('api/ocr-pdf-stream/',             protected_api(ocr_pdf_stream),              name='api_ocr_pdf_stream'),
    path('api/ocr-progress/<str:job_id>/',  protected_api(ocr_pdf_progress),            name='api_ocr_progress'),
    path('api/extract-page/',               protected_api(extract_page),                name='api_extract_page'),
    path('api/extract-page-ai/',            protected_api(extract_page_ai),             name='api_extract_page_ai'),
    path('api/extract-statement-summary/',  protected_api(extract_statement_summary),   name='api_extract_statement_summary'),
    path('api/extract-invoice/',            protected_api(extract_invoice),             name='api_invoice'),
    path('api/invoice-to-excel/',           protected_api(invoice_to_excel),            name='api_invoice_excel'),
    path('api/extract-invoice-ai/',         protected_api(extract_invoice_ai),          name='api_invoice_ai'),
    path('api/smart-split-suggest/',        protected_api(smart_split_suggest),         name='api_smart_split'),
    path('api/detect-blank-pages/',         protected_api(detect_blank_pages),          name='api_detect_blank'),
    path('api/scan-to-pdf/',                protected_api(scan_to_pdf),                 name='api_scan_pdf'),
    path('api/pdf-to-word/',                protected_api(pdf_to_word),                 name='api_pdf_to_word'),
    path('api/pdf-to-pptx/',                protected_api(pdf_to_pptx),                 name='api_pdf_to_pptx'),
    path('api/pdf-to-excel/',               protected_api(pdf_to_excel),                name='api_pdf_to_excel'),
    path('api/summarize-pdf/',              protected_api(summarize_pdf),               name='api_summarize_pdf'),
    path('api/translate-pdf/',              protected_api(translate_pdf),               name='api_translate_pdf'),
    path('api/crop-pdf/',                   protected_api(crop_pdf),                    name='api_crop_pdf'),
    path('api/protect-pdf/',               protected_api(protect_pdf),                 name='api_protect_pdf'),
    path('api/unlock-pdf/',                 protected_api(unlock_pdf),                  name='api_unlock_pdf'),
    path('api/redact-pdf/',                 protected_api(redact_pdf),                  name='api_redact_pdf'),
    path('api/img/crop/',                   protected_api(crop_image),                  name='api_img_crop'),
    path('api/img/watermark/',              protected_api(watermark_image),             name='api_img_watermark'),
    path('api/img/meme/',                   protected_api(meme_generator),              name='api_img_meme'),
    path('api/img/upscale/',                protected_api(upscale_image),               name='api_img_upscale'),
    path('api/img/remove-bg/',              protected_api(remove_background),           name='api_img_remove_bg'),
    path('api/img/blur-face/',              protected_api(blur_face),                   name='api_img_blur_face'),
    path('api/img/ocr/',                    protected_api(img_ocr),                     name='api_img_ocr'),
]
