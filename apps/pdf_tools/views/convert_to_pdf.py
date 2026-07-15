import fitz
import os
import subprocess
import tempfile
import logging
import traceback
import img2pdf
from PIL import Image
from io import BytesIO
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.utils import save_uploaded_file, get_output_path, media_url, cleanup_file, validate_image, validate_office
from apps.pdf_tools.mongo_db import save_job
from apps.pdf_tools.utils import ip_ratelimit

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def jpg_to_pdf(request):
    files = request.FILES.getlist('files')
    if not files:
        return JsonResponse({'error': 'No images uploaded.'}, status=400)

    saved = []
    try:
        img_paths = []
        for f in files:
            sp, _ = save_uploaded_file(f)
            saved.append(sp)
            validate_image(sp, f.name)
            # Ensure RGB
            img = Image.open(sp).convert('RGB')
            rgb_path, rgb_name = get_output_path('.jpg', 'rgb')
            img.save(rgb_path, 'JPEG', quality=95)
            img_paths.append(rgb_path)
            saved.append(rgb_path)

        out_path, out_name = get_output_path('.pdf', 'jpg_to_pdf')
        with open(out_path, 'wb') as fp:
            fp.write(img2pdf.convert(img_paths))

        save_job('jpg_to_pdf', [f.name for f in files], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'Conversion failed. Ensure all files are valid images.'}, status=500)
    finally:
        for sp in saved:
            cleanup_file(sp)


@csrf_exempt
@require_POST
def word_to_pdf(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No Word file uploaded.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.pdf', 'word_to_pdf')

    try:
        validate_office(saved_path, f.name, kinds=('doc', 'docx'))
        success = _libreoffice_convert(saved_path, out_path)
        if not success:
            raise RuntimeError(
                'LibreOffice not found or conversion failed. '
                'Run: sudo apt-get install -y libreoffice on the server.'
            )
        save_job('word_to_pdf', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('word_to_pdf error: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Conversion failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


@csrf_exempt
@require_POST
def pptx_to_pdf(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No PowerPoint file uploaded.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.pdf', 'pptx_to_pdf')

    try:
        validate_office(saved_path, f.name, kinds=('ppt', 'pptx'))
        success = _libreoffice_convert(saved_path, out_path)
        if not success:
            raise RuntimeError('LibreOffice not found or conversion failed.')
        save_job('pptx_to_pdf', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('pptx_to_pdf error: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Conversion failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


@csrf_exempt
@require_POST
def excel_to_pdf(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No Excel file uploaded.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.pdf', 'excel_to_pdf')

    try:
        validate_office(saved_path, f.name, kinds=('xls', 'xlsx'))
        success = _libreoffice_convert(saved_path, out_path)
        if not success:
            raise RuntimeError('LibreOffice not found or conversion failed.')
        save_job('excel_to_pdf', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('excel_to_pdf error: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Conversion failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


@ip_ratelimit(limit=15)
@csrf_exempt
@require_POST
def html_to_pdf(request):
    html_file = request.FILES.get('file')
    html_url = request.POST.get('url', '').strip()
    html_content = request.POST.get('content', '')

    out_path, out_name = get_output_path('.pdf', 'html_to_pdf')
    saved_path = None

    try:
        import pdfkit
        wk_config = pdfkit.configuration(wkhtmltopdf=settings.WKHTMLTOPDF_CMD)
        # local-file-access disabled to prevent reading server files via file:// URIs
        options = {'quiet': '', 'disable-local-file-access': ''}

        if html_file:
            saved_path, _ = save_uploaded_file(html_file)
            pdfkit.from_file(saved_path, out_path, configuration=wk_config, options=options)
        elif html_url:
            _validate_url(html_url)
            pdfkit.from_url(html_url, out_path, configuration=wk_config, options=options)
        elif html_content:
            pdfkit.from_string(html_content, out_path, configuration=wk_config, options=options)
        else:
            return JsonResponse({'error': 'Provide HTML file, URL, or content.'}, status=400)

        save_job('html_to_pdf', [html_file.name if html_file else html_url], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'Conversion failed. Check your input and try again.'}, status=500)
    finally:
        if saved_path:
            cleanup_file(saved_path)


def _validate_url(url):
    """Block non-HTTP schemes and private/loopback/cloud-metadata addresses (SSRF prevention)."""
    import ipaddress
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError('Only http:// and https:// URLs are allowed.')

    host = parsed.hostname or ''
    if not host:
        raise ValueError('Invalid URL: no hostname.')

    # Strip IPv6 brackets
    host_clean = host.strip('[]')

    # Always-blocked hostnames (covers DNS names for loopback/metadata)
    _BLOCKED_HOSTS = {
        'localhost',
        'metadata.google.internal',
        'metadata.google',
        '169.254.169.254',
        'instance-data',
    }
    if host_clean.lower() in _BLOCKED_HOSTS:
        raise ValueError('URL points to a blocked host.')

    # Resolve hostname â†’ IP and check all returned addresses
    try:
        resolved = socket.getaddrinfo(host_clean, None)
        ips = {r[4][0] for r in resolved}
    except socket.gaierror:
        raise ValueError('URL hostname could not be resolved.')

    for ip_str in ips:
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (addr.is_private or addr.is_loopback or addr.is_link_local
                or addr.is_reserved or addr.is_multicast
                or addr.is_unspecified):
            raise ValueError('URL resolves to a private or reserved address.')


def _libreoffice_convert(input_path, output_path):
    """Convert any Office document to PDF using LibreOffice."""
    import shutil
    lo_path = shutil.which('libreoffice') or shutil.which('soffice')
    if not lo_path:
        for p in [
            r'C:\Program Files\LibreOffice\program\soffice.exe',
            r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
            '/usr/bin/libreoffice', '/usr/bin/soffice',
            '/usr/local/bin/libreoffice', '/usr/local/bin/soffice',
            '/snap/bin/libreoffice',
        ]:
            if os.path.exists(p):
                lo_path = p
                break

    if not lo_path:
        logger.error('LibreOffice not found on PATH or known locations')
        return False

    out_dir = os.path.dirname(output_path)
    # Temp user profile prevents permission errors when running as www-data/nobody
    user_profile = os.path.join(tempfile.gettempdir(), 'lo_userprofile')
    os.makedirs(user_profile, exist_ok=True)

    cmd = [
        lo_path,
        '--headless',
        '--norestore',
        '--nofirststartwizard',
        f'-env:UserInstallation=file://{user_profile}',
        '--convert-to', 'pdf',
        '--outdir', out_dir,
        input_path,
    ]
    # Gunicorn runs with a stripped PATH; LibreOffice's shell wrapper needs
    # standard utilities (dirname, basename, sed, grep, uname) to be on PATH.
    env = os.environ.copy()
    env['PATH'] = '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:' + env.get('PATH', '')
    result = subprocess.run(cmd, capture_output=True, timeout=120, env=env)
    logger.info('LibreOffice stdout: %s', result.stdout.decode(errors='replace'))
    if result.returncode != 0:
        logger.error('LibreOffice stderr: %s', result.stderr.decode(errors='replace'))

    # LibreOffice saves as <input_stem>.pdf in out_dir
    stem = os.path.splitext(os.path.basename(input_path))[0]
    lo_out = os.path.join(out_dir, stem + '.pdf')
    if os.path.exists(lo_out) and lo_out != output_path:
        os.rename(lo_out, output_path)

    return os.path.exists(output_path)
