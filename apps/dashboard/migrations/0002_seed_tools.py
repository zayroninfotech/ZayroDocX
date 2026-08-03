from django.db import migrations

TOOLS = [
    # slug, name, category, requires_login, icon
    # FREE tools
    ('merge-pdf',        'Merge PDF',          'Organize PDF',  False, 'fa-object-group'),
    ('split-pdf',        'Split PDF',          'Organize PDF',  False, 'fa-scissors'),
    ('rotate-pdf',       'Rotate PDF',         'Edit PDF',      False, 'fa-rotate-right'),
    ('add-page-numbers', 'Add Page Numbers',   'Edit PDF',      False, 'fa-list-ol'),
    ('jpg-to-pdf',       'JPG to PDF',         'Convert PDF',   False, 'fa-images'),
    ('pdf-to-jpg',       'PDF to JPG',         'Convert PDF',   False, 'fa-file-image'),
    ('word-to-pdf',      'Word to PDF',        'Convert PDF',   False, 'fa-file-word'),
    ('pptx-to-pdf',      'PowerPoint to PDF',  'Convert PDF',   False, 'fa-file-powerpoint'),
    ('excel-to-pdf',     'Excel to PDF',       'Convert PDF',   False, 'fa-file-excel'),
    ('html-to-pdf',      'HTML to PDF',        'Convert PDF',   False, 'fa-brands fa-html5'),
    ('compress-image',   'Compress Image',     'Image Tools',   False, 'fa-compress'),
    ('resize-image',     'Resize Image',       'Image Tools',   False, 'fa-up-right-and-down-left-from-center'),
    ('rotate-image',     'Rotate Image',       'Image Tools',   False, 'fa-rotate-right'),
    ('convert-to-jpg',   'Convert to JPG',     'Image Tools',   False, 'fa-file-image'),
    ('convert-from-jpg', 'Convert from JPG',   'Image Tools',   False, 'fa-images'),
    # LOGIN REQUIRED tools
    ('compress-pdf',     'Compress PDF',       'Optimize & AI', True,  'fa-compress'),
    ('remove-pages',     'Remove Pages',       'Organize PDF',  True,  'fa-trash-can'),
    ('extract-pages',    'Extract Pages',      'Organize PDF',  True,  'fa-file-export'),
    ('watermark-pdf',    'Watermark PDF',      'Edit PDF',      True,  'fa-droplet'),
    ('sign-pdf',         'Sign PDF',           'Edit PDF',      True,  'fa-signature'),
    ('ocr-pdf',          'OCR PDF',            'Optimize & AI', True,  'fa-eye'),
    ('scan-to-pdf',      'Scan to PDF',        'Organize PDF',  True,  'fa-camera'),
    ('crop-pdf',         'Crop PDF',           'Edit PDF',      True,  'fa-crop-simple'),
    ('invoice-extractor','Invoice Extractor',  'Optimize & AI', True,  'fa-file-invoice-dollar'),
    ('ai-summarizer',    'AI Summarizer',      'Optimize & AI', True,  'fa-wand-magic-sparkles'),
    ('translate-pdf',    'Translate PDF',      'Optimize & AI', True,  'fa-language'),
    ('pdf-to-word',      'PDF to Word',        'Convert PDF',   True,  'fa-file-word'),
    ('pdf-to-pptx',      'PDF to PowerPoint',  'Convert PDF',   True,  'fa-file-powerpoint'),
    ('pdf-to-excel',     'PDF to Excel',       'Convert PDF',   True,  'fa-file-excel'),
    ('protect-pdf',      'Protect PDF',        'PDF Security',  True,  'fa-lock'),
    ('unlock-pdf',       'Unlock PDF',         'PDF Security',  True,  'fa-lock-open'),
    ('redact-pdf',       'Redact PDF',         'PDF Security',  True,  'fa-eraser'),
    ('crop-image',       'Crop Image',         'Image Tools',   True,  'fa-crop-simple'),
    ('watermark-image',  'Watermark Image',    'Image Tools',   True,  'fa-stamp'),
    ('meme-generator',   'Meme Generator',     'Image Tools',   True,  'fa-face-laugh-squint'),
    ('upscale-image',    'Upscale Image',      'Image Tools',   True,  'fa-magnifying-glass-plus'),
    ('remove-background','Remove Background',  'Image Tools',   True,  'fa-wand-magic-sparkles'),
    ('blur-face',        'Blur Face',          'Image Tools',   True,  'fa-user-secret'),
    ('image-to-text',    'Image to Text',      'Image Tools',   True,  'fa-font'),
]


def seed_tools(apps, schema_editor):
    ToolPrivilege = apps.get_model('dashboard', 'ToolPrivilege')
    for slug, name, category, requires_login, icon in TOOLS:
        ToolPrivilege.objects.get_or_create(
            slug=slug,
            defaults=dict(name=name, category=category, requires_login=requires_login, icon=icon)
        )


class Migration(migrations.Migration):
    dependencies = [('dashboard', '0001_initial')]
    operations = [migrations.RunPython(seed_tools, migrations.RunPython.noop)]
