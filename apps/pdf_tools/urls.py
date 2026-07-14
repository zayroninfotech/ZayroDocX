from django.urls import path
from django.shortcuts import render

# Tool page views
def tool_page(template):
    def view(request):
        return render(request, f'pdf_tools/{template}')
    return view

# API views
from apps.pdf_tools.views.merge import merge_pdf
from apps.pdf_tools.views.split import split_pdf
from apps.pdf_tools.views.pages import remove_pages, extract_pages, get_pdf_info
from apps.pdf_tools.views.compress import compress_pdf
from apps.pdf_tools.views.edit_pdf import rotate_pdf, add_page_numbers
from apps.pdf_tools.views.watermark import add_watermark
from apps.pdf_tools.views.sign_pdf import sign_pdf
from apps.pdf_tools.views.ocr_pdf import ocr_pdf, ocr_pdf_stream, ocr_pdf_progress, extract_page, extract_page_ai, extract_statement_summary, extract_invoice, scan_to_pdf, invoice_to_excel, extract_invoice_ai, smart_split_suggest, detect_blank_pages
from apps.pdf_tools.views.convert_to_pdf import jpg_to_pdf, word_to_pdf, pptx_to_pdf, excel_to_pdf, html_to_pdf
from apps.pdf_tools.views.convert_from_pdf import pdf_to_jpg, pdf_to_word, pdf_to_pptx, pdf_to_excel
from apps.pdf_tools.views.pdf_viewer import pdf_preview, extract_pdf_data, download_page_image

urlpatterns = [
    # Tool pages
    path('merge-pdf/', tool_page('merge.html'), name='merge_pdf_page'),
    path('split-pdf/', tool_page('split.html'), name='split_pdf_page'),
    path('remove-pages/', tool_page('remove_pages.html'), name='remove_pages_page'),
    path('extract-pages/', tool_page('extract_pages.html'), name='extract_pages_page'),
    path('compress-pdf/', tool_page('compress.html'), name='compress_pdf_page'),
    path('rotate-pdf/', tool_page('rotate.html'), name='rotate_pdf_page'),
    path('add-page-numbers/', tool_page('page_numbers.html'), name='page_numbers_page'),
    path('watermark-pdf/', tool_page('watermark.html'), name='watermark_pdf_page'),
    path('sign-pdf/', tool_page('sign.html'), name='sign_pdf_page'),
    path('ocr-pdf/', tool_page('ocr.html'), name='ocr_pdf_page'),
    path('scan-to-pdf/', tool_page('scan.html'), name='scan_pdf_page'),
    path('jpg-to-pdf/', tool_page('jpg_to_pdf.html'), name='jpg_to_pdf_page'),
    path('word-to-pdf/', tool_page('word_to_pdf.html'), name='word_to_pdf_page'),
    path('pptx-to-pdf/', tool_page('pptx_to_pdf.html'), name='pptx_to_pdf_page'),
    path('excel-to-pdf/', tool_page('excel_to_pdf.html'), name='excel_to_pdf_page'),
    path('html-to-pdf/', tool_page('html_to_pdf.html'), name='html_to_pdf_page'),
    path('pdf-to-jpg/', tool_page('pdf_to_jpg.html'), name='pdf_to_jpg_page'),
    path('pdf-to-word/', tool_page('pdf_to_word.html'), name='pdf_to_word_page'),
    path('pdf-to-pptx/', tool_page('pdf_to_pptx.html'), name='pdf_to_pptx_page'),
    path('pdf-to-excel/', tool_page('pdf_to_excel.html'), name='pdf_to_excel_page'),
    path('invoice-extractor/', tool_page('invoice.html'), name='invoice_page'),
    path('pdf-viewer/', tool_page('pdf_viewer.html'), name='pdf_viewer_page'),

    # API endpoints
    path('api/merge-pdf/', merge_pdf, name='api_merge_pdf'),
    path('api/split-pdf/', split_pdf, name='api_split_pdf'),
    path('api/remove-pages/', remove_pages, name='api_remove_pages'),
    path('api/extract-pages/', extract_pages, name='api_extract_pages'),
    path('api/get-pdf-info/', get_pdf_info, name='api_pdf_info'),
    path('api/compress-pdf/', compress_pdf, name='api_compress_pdf'),
    path('api/rotate-pdf/', rotate_pdf, name='api_rotate_pdf'),
    path('api/add-page-numbers/', add_page_numbers, name='api_page_numbers'),
    path('api/watermark-pdf/', add_watermark, name='api_watermark'),
    path('api/sign-pdf/', sign_pdf, name='api_sign_pdf'),
    path('api/ocr-pdf/', ocr_pdf, name='api_ocr_pdf'),
    path('api/ocr-pdf-stream/', ocr_pdf_stream, name='api_ocr_pdf_stream'),
    path('api/ocr-progress/<str:job_id>/', ocr_pdf_progress, name='api_ocr_progress'),
    path('api/extract-page/', extract_page, name='api_extract_page'),
    path('api/extract-page-ai/', extract_page_ai, name='api_extract_page_ai'),
    path('api/extract-statement-summary/', extract_statement_summary, name='api_extract_statement_summary'),
    path('api/extract-invoice/', extract_invoice, name='api_invoice'),
    path('api/invoice-to-excel/', invoice_to_excel, name='api_invoice_excel'),
    path('api/extract-invoice-ai/', extract_invoice_ai, name='api_invoice_ai'),
    path('api/smart-split-suggest/', smart_split_suggest, name='api_smart_split'),
    path('api/detect-blank-pages/', detect_blank_pages, name='api_detect_blank'),
    path('api/scan-to-pdf/', scan_to_pdf, name='api_scan_pdf'),
    path('api/jpg-to-pdf/', jpg_to_pdf, name='api_jpg_to_pdf'),
    path('api/word-to-pdf/', word_to_pdf, name='api_word_to_pdf'),
    path('api/pptx-to-pdf/', pptx_to_pdf, name='api_pptx_to_pdf'),
    path('api/excel-to-pdf/', excel_to_pdf, name='api_excel_to_pdf'),
    path('api/html-to-pdf/', html_to_pdf, name='api_html_to_pdf'),
    path('api/pdf-to-jpg/', pdf_to_jpg, name='api_pdf_to_jpg'),
    path('api/pdf-to-word/', pdf_to_word, name='api_pdf_to_word'),
    path('api/pdf-to-pptx/', pdf_to_pptx, name='api_pdf_to_pptx'),
    path('api/pdf-to-excel/', pdf_to_excel, name='api_pdf_to_excel'),
    path('api/pdf-preview/', pdf_preview, name='api_pdf_preview'),
    path('api/extract-pdf-data/', extract_pdf_data, name='api_extract_pdf_data'),
    path('api/download-page-image/', download_page_image, name='api_download_page_image'),
]
