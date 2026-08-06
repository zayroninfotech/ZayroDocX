from django.urls import path
from django.shortcuts import render, redirect
from django.http import JsonResponse

# ── Dynamic privilege check from DB ──────────────────────────────────────────
def tool_page(template, slug):
    def view(request):
        try:
            from apps.dashboard.models import ToolPrivilege
            priv = ToolPrivilege.objects.filter(slug=slug).first()
            if priv and priv.requires_login and not request.user.is_authenticated:
                return redirect(f'/login/?next={request.path}')
        except Exception:
            pass
        return render(request, f'pdf_tools/{template}')
    view.__name__ = slug.replace('-', '_') + '_page_view'
    return view


def protected_api(view_func):
    def wrapper(request, *args, **kwargs):
        try:
            from apps.dashboard.models import ToolPrivilege
            slug = getattr(view_func, '_tool_slug', None)
            if slug:
                priv = ToolPrivilege.objects.filter(slug=slug).first()
                if priv and priv.requires_login and not request.user.is_authenticated:
                    return JsonResponse({'error': 'Login required to use this tool.'}, status=401)
        except Exception:
            pass
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
from apps.pdf_tools.views.ocr_pdf import ocr_pdf, ocr_pdf_stream, ocr_pdf_progress, extract_page, extract_page_ai, extract_statement_summary, extract_invoice, scan_to_pdf, invoice_to_excel, extract_invoice_ai, smart_split_suggest, detect_blank_pages, crop_extract, extract_all_pages_excel
from apps.pdf_tools.views.convert_to_pdf import word_to_pdf, pptx_to_pdf, excel_to_pdf, html_to_pdf, jpg_to_pdf, render_word_pages, render_pptx_pages, render_excel_pages
from apps.pdf_tools.views.convert_from_pdf import pdf_to_jpg, pdf_to_word, pdf_to_pptx, pdf_to_excel
from apps.pdf_tools.views.ai_summarizer import summarize_pdf, render_pdf_pages
from apps.pdf_tools.views.translate_pdf import translate_pdf
from apps.pdf_tools.views.security import protect_pdf, unlock_pdf, redact_pdf
from apps.pdf_tools.views.crop_pdf import crop_pdf
from apps.pdf_tools.views.thumbnail import pdf_thumbnails
from apps.pdf_tools.views.image_tools import (
    compress_image, resize_image, crop_image, rotate_image,
    convert_to_jpg, convert_from_jpg, watermark_image, meme_generator,
    upscale_image, remove_background, blur_face, img_ocr,
)
from apps.pdf_tools.views.live_share import (
    create_room, join_room, upload_file, poll_room, download_file,
)

# Tag API views with their slug for dynamic privilege check
def _tag(fn, slug):
    fn._tool_slug = slug
    return fn

urlpatterns = [
    # ── Tool pages (all dynamic — DB decides if login required) ──────────────
    path('merge-pdf/',          tool_page('merge.html',        'merge-pdf'),        name='merge_pdf_page'),
    path('split-pdf/',          tool_page('split.html',        'split-pdf'),        name='split_pdf_page'),
    path('remove-pages/',       tool_page('remove_pages.html', 'remove-pages'),     name='remove_pages_page'),
    path('extract-pages/',      tool_page('extract_pages.html','extract-pages'),    name='extract_pages_page'),
    path('compress-pdf/',       tool_page('compress.html',     'compress-pdf'),     name='compress_pdf_page'),
    path('rotate-pdf/',         tool_page('rotate.html',       'rotate-pdf'),       name='rotate_pdf_page'),
    path('add-page-numbers/',   tool_page('page_numbers.html', 'add-page-numbers'), name='page_numbers_page'),
    path('watermark-pdf/',      tool_page('watermark.html',    'watermark-pdf'),    name='watermark_pdf_page'),
    path('sign-pdf/',           tool_page('sign.html',         'sign-pdf'),         name='sign_pdf_page'),
    path('ocr-pdf/',            tool_page('ocr.html',          'ocr-pdf'),          name='ocr_pdf_page'),
    path('scan-to-pdf/',        tool_page('scan.html',         'scan-to-pdf'),      name='scan_pdf_page'),
    path('word-to-pdf/',        tool_page('word_to_pdf.html',  'word-to-pdf'),      name='word_to_pdf_page'),
    path('pptx-to-pdf/',        tool_page('pptx_to_pdf.html',  'pptx-to-pdf'),     name='pptx_to_pdf_page'),
    path('excel-to-pdf/',       tool_page('excel_to_pdf.html', 'excel-to-pdf'),     name='excel_to_pdf_page'),
    path('html-to-pdf/',        tool_page('html_to_pdf.html',  'html-to-pdf'),      name='html_to_pdf_page'),
    path('jpg-to-pdf/',         tool_page('jpg_to_pdf.html',   'jpg-to-pdf'),       name='jpg_to_pdf_page'),
    path('pdf-to-jpg/',         tool_page('pdf_to_jpg.html',   'pdf-to-jpg'),       name='pdf_to_jpg_page'),
    path('pdf-to-word/',        tool_page('pdf_to_word.html',  'pdf-to-word'),      name='pdf_to_word_page'),
    path('pdf-to-pptx/',        tool_page('pdf_to_pptx.html',  'pdf-to-pptx'),     name='pdf_to_pptx_page'),
    path('pdf-to-excel/',       tool_page('pdf_to_excel.html', 'pdf-to-excel'),     name='pdf_to_excel_page'),
    path('invoice-extractor/',  tool_page('invoice.html',       'invoice-extractor'),name='invoice_page'),
    path('ai-summarizer/',      tool_page('ai_summarizer.html', 'ai-summarizer'),   name='ai_summarizer_page'),
    path('translate-pdf/',      tool_page('translate_pdf.html', 'translate-pdf'),   name='translate_pdf_page'),
    path('crop-pdf/',           tool_page('crop.html',          'crop-pdf'),        name='crop_pdf_page'),
    path('protect-pdf/',        tool_page('protect.html',       'protect-pdf'),     name='protect_pdf_page'),
    path('unlock-pdf/',         tool_page('unlock.html',        'unlock-pdf'),      name='unlock_pdf_page'),
    path('redact-pdf/',         tool_page('redact.html',        'redact-pdf'),      name='redact_pdf_page'),
    path('compress-image/',     tool_page('img_compress.html',  'compress-image'),  name='img_compress_page'),
    path('resize-image/',       tool_page('img_resize.html',    'resize-image'),    name='img_resize_page'),
    path('crop-image/',         tool_page('img_crop.html',      'crop-image'),      name='img_crop_page'),
    path('rotate-image/',       tool_page('img_rotate.html',    'rotate-image'),    name='img_rotate_page'),
    path('convert-to-jpg/',     tool_page('img_to_jpg.html',    'convert-to-jpg'),  name='img_to_jpg_page'),
    path('convert-from-jpg/',   tool_page('img_from_jpg.html',  'convert-from-jpg'),name='img_from_jpg_page'),
    path('watermark-image/',    tool_page('img_watermark.html', 'watermark-image'), name='img_watermark_page'),
    path('meme-generator/',     tool_page('img_meme.html',      'meme-generator'),  name='img_meme_page'),
    path('upscale-image/',      tool_page('img_upscale.html',   'upscale-image'),   name='img_upscale_page'),
    path('remove-background/',  tool_page('img_remove_bg.html', 'remove-background'),name='img_remove_bg_page'),
    path('blur-face/',          tool_page('img_blur_face.html', 'blur-face'),       name='img_blur_face_page'),
    path('image-to-text/',      tool_page('img_ocr.html',       'image-to-text'),   name='img_ocr_page'),
    path('connectspace/',       tool_page('live_share.html',    'connectspace'),     name='connectspace_page'),

    # ── API endpoints ─────────────────────────────────────────────────────────
    path('api/merge-pdf/',      protected_api(_tag(merge_pdf,      'merge-pdf')),       name='api_merge_pdf'),
    path('api/split-pdf/',      protected_api(_tag(split_pdf,      'split-pdf')),       name='api_split_pdf'),
    path('api/remove-pages/',   protected_api(_tag(remove_pages,   'remove-pages')),    name='api_remove_pages'),
    path('api/extract-pages/',  protected_api(_tag(extract_pages,  'extract-pages')),   name='api_extract_pages'),
    path('api/get-pdf-info/',   get_pdf_info,                                           name='api_pdf_info'),
    path('api/compress-pdf/',   protected_api(_tag(compress_pdf,   'compress-pdf')),    name='api_compress_pdf'),
    path('api/rotate-pdf/',     protected_api(_tag(rotate_pdf,     'rotate-pdf')),      name='api_rotate_pdf'),
    path('api/add-page-numbers/', protected_api(_tag(add_page_numbers, 'add-page-numbers')), name='api_page_numbers'),
    path('api/watermark-pdf/',  protected_api(_tag(add_watermark,  'watermark-pdf')),   name='api_watermark'),
    path('api/sign-pdf/',       protected_api(_tag(sign_pdf,       'sign-pdf')),        name='api_sign_pdf'),
    path('api/ocr-pdf/',        protected_api(_tag(ocr_pdf,        'ocr-pdf')),         name='api_ocr_pdf'),
    path('api/ocr-pdf-stream/', protected_api(_tag(ocr_pdf_stream, 'ocr-pdf')),         name='api_ocr_pdf_stream'),
    path('api/ocr-progress/<str:job_id>/', protected_api(_tag(ocr_pdf_progress, 'ocr-pdf')), name='api_ocr_progress'),
    path('api/extract-page/',               protected_api(_tag(extract_page,              'ocr-pdf')),             name='api_extract_page'),
    path('api/extract-page-ai/',            protected_api(_tag(extract_page_ai,           'ocr-pdf')),             name='api_extract_page_ai'),
    path('api/extract-statement-summary/',  protected_api(_tag(extract_statement_summary, 'ocr-pdf')),             name='api_extract_statement_summary'),
    path('api/extract-invoice/',            protected_api(_tag(extract_invoice,           'invoice-extractor')),   name='api_invoice'),
    path('api/invoice-to-excel/',           protected_api(_tag(invoice_to_excel,          'invoice-extractor')),   name='api_invoice_excel'),
    path('api/extract-invoice-ai/',         protected_api(_tag(extract_invoice_ai,        'invoice-extractor')),   name='api_invoice_ai'),
    path('api/smart-split-suggest/',        protected_api(_tag(smart_split_suggest,       'split-pdf')),           name='api_smart_split'),
    path('api/detect-blank-pages/',         protected_api(_tag(detect_blank_pages,        'ocr-pdf')),             name='api_detect_blank'),
    path('api/ocr-crop-extract/',           protected_api(_tag(crop_extract,              'ocr-pdf')),             name='api_crop_extract_region'),
    path('api/ocr-all-pages-excel/',        protected_api(_tag(extract_all_pages_excel,   'ocr-pdf')),             name='api_all_pages_excel'),
    path('api/scan-to-pdf/',    protected_api(_tag(scan_to_pdf,    'scan-to-pdf')),     name='api_scan_pdf'),
    path('api/word-to-pdf/',    protected_api(_tag(word_to_pdf,    'word-to-pdf')),     name='api_word_to_pdf'),
    path('api/render-word-pages/', render_word_pages, name='api_render_word_pages'),
    path('api/render-pptx-pages/',  render_pptx_pages,  name='api_render_pptx_pages'),
    path('api/render-excel-pages/', render_excel_pages, name='api_render_excel_pages'),
    path('api/pptx-to-pdf/',    protected_api(_tag(pptx_to_pdf,   'pptx-to-pdf')),     name='api_pptx_to_pdf'),
    path('api/excel-to-pdf/',   protected_api(_tag(excel_to_pdf,  'excel-to-pdf')),    name='api_excel_to_pdf'),
    path('api/html-to-pdf/',    protected_api(_tag(html_to_pdf,   'html-to-pdf')),     name='api_html_to_pdf'),
    path('api/pdf-to-jpg/',     protected_api(_tag(pdf_to_jpg,    'pdf-to-jpg')),      name='api_pdf_to_jpg'),
    path('api/pdf-to-word/',    protected_api(_tag(pdf_to_word,   'pdf-to-word')),     name='api_pdf_to_word'),
    path('api/pdf-to-pptx/',    protected_api(_tag(pdf_to_pptx,   'pdf-to-pptx')),    name='api_pdf_to_pptx'),
    path('api/pdf-to-excel/',   protected_api(_tag(pdf_to_excel,  'pdf-to-excel')),   name='api_pdf_to_excel'),
    path('api/summarize-pdf/',  protected_api(_tag(summarize_pdf, 'ai-summarizer')),   name='api_summarize_pdf'),
    path('api/render-pdf-pages/', render_pdf_pages, name='api_render_pdf_pages'),
    path('api/translate-pdf/',  protected_api(_tag(translate_pdf, 'translate-pdf')),   name='api_translate_pdf'),
    path('api/crop-pdf/',       protected_api(_tag(crop_pdf,      'crop-pdf')),        name='api_crop_pdf'),
    path('api/protect-pdf/',    protected_api(_tag(protect_pdf,   'protect-pdf')),     name='api_protect_pdf'),
    path('api/unlock-pdf/',     protected_api(_tag(unlock_pdf,    'unlock-pdf')),      name='api_unlock_pdf'),
    path('api/redact-pdf/',     protected_api(_tag(redact_pdf,    'redact-pdf')),      name='api_redact_pdf'),
    path('api/pdf-thumbnails/', pdf_thumbnails,                                        name='api_pdf_thumbnails'),
    path('api/jpg-to-pdf/',     protected_api(_tag(jpg_to_pdf,   'jpg-to-pdf')),      name='api_jpg_to_pdf'),
    path('api/img/compress/',   protected_api(_tag(compress_image,'compress-image')),  name='api_img_compress'),
    path('api/img/resize/',     protected_api(_tag(resize_image,  'resize-image')),   name='api_img_resize'),
    path('api/img/crop/',       protected_api(_tag(crop_image,    'crop-image')),      name='api_img_crop'),
    path('api/img/rotate/',     protected_api(_tag(rotate_image,  'rotate-image')),    name='api_img_rotate'),
    path('api/img/to-jpg/',     protected_api(_tag(convert_to_jpg,'convert-to-jpg')), name='api_img_to_jpg'),
    path('api/img/from-jpg/',   protected_api(_tag(convert_from_jpg,'convert-from-jpg')), name='api_img_from_jpg'),
    path('api/img/watermark/',  protected_api(_tag(watermark_image,'watermark-image')),name='api_img_watermark'),
    path('api/img/meme/',       protected_api(_tag(meme_generator,'meme-generator')), name='api_img_meme'),
    path('api/img/upscale/',    protected_api(_tag(upscale_image, 'upscale-image')),  name='api_img_upscale'),
    path('api/img/remove-bg/',  protected_api(_tag(remove_background,'remove-background')), name='api_img_remove_bg'),
    path('api/img/blur-face/',  protected_api(_tag(blur_face,    'blur-face')),       name='api_img_blur_face'),
    path('api/img/ocr/',        protected_api(_tag(img_ocr,      'image-to-text')),   name='api_img_ocr'),
    path('api/live-share/create/',              create_room,    name='api_ls_create'),
    path('api/live-share/join/',                join_room,      name='api_ls_join'),
    path('api/live-share/upload/',              upload_file,    name='api_ls_upload'),
    path('api/live-share/poll/',                poll_room,      name='api_ls_poll'),
    path('api/live-share/download/<str:file_id>/', download_file, name='api_ls_download'),
]
