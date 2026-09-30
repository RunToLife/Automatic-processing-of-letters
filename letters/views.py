import json
import re
import tempfile
from datetime import date
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .converter import ConversionError, convert_pdf, html_to_docx
from .models import ScanRecord

BAD_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
DOCX_MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


@login_required
def upload(request):
    return render(request, 'letters/upload.html', {'today': date.today().isoformat(),
                                                   'max_mb': settings.MAX_PDF_MB})


@login_required
@require_POST
def convert(request):
    f = request.FILES.get('pdf')
    if not f:
        return JsonResponse({'error': 'Файл не выбран.'}, status=400)
    if not f.name.lower().endswith('.pdf'):
        return JsonResponse({'error': 'Нужен файл в формате PDF.'}, status=400)
    if f.size > settings.MAX_PDF_MB * 1024 * 1024:
        return JsonResponse({'error': f'Файл больше {settings.MAX_PDF_MB} МБ.'}, status=400)
    with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp:
        for chunk in f.chunks():
            tmp.write(chunk)
        tmp.flush()
        try:
            res = convert_pdf(tmp.name)
        except ConversionError as e:
            return JsonResponse({'error': str(e)}, status=422)
    return JsonResponse({'html': res.html, 'pages': res.pages, 'ocr_pages': res.ocr_pages,
                         'warnings': res.warnings})


def _clean_name(name):
    name = BAD_NAME.sub('_', (name or '').strip()).strip('. ')
    if name.lower().endswith('.docx'):
        name = name[:-5]
    return name or 'Письмо'


@login_required
@require_POST
def build_docx(request):
    """Собирает WORD из отредактированного текста; браузер сам записывает файл на машину пользователя."""
    html = request.POST.get('html', '')
    name = _clean_name(request.POST.get('filename'))
    data = html_to_docx(html)
    resp = HttpResponse(data, content_type=DOCX_MIME)
    resp['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(name)}.docx"
    return resp


@login_required
@require_POST
def register(request):
    """Добавляет запись в таблицу СКАНЫ после успешного сохранения файла у пользователя."""
    try:
        p = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'Неверный запрос.'}, status=400)
    name = _clean_name(p.get('filename'))
    folder = (p.get('folder') or '').strip()
    sep = '\\' if ('\\' in folder or re.match(r'^[A-Za-z]:', folder)) else '/'
    full = f"{folder.rstrip('/' + chr(92))}{sep}{name}.docx" if folder else f'{name}.docx'
    try:
        processed = date.fromisoformat(p.get('processed_date') or '')
    except ValueError:
        processed = None
    rec = ScanRecord.objects.create(
        title=name, incoming_number=(p.get('incoming_number') or '').strip()[:100],
        processed_date=processed, path=full, user=request.user)
    return JsonResponse({'id': rec.id, 'path': full})


COLUMNS = [  # параметр фильтра, функция-значение
    ('f_title', lambda r: r.title),
    ('f_num', lambda r: r.incoming_number),
    ('f_saved', lambda r: r.saved_display),
    ('f_proc', lambda r: r.processed_display),
    ('f_path', lambda r: r.path),
]


@login_required
def scans(request):
    q = request.GET.get('q', '').strip().lower()
    filters = {k: request.GET.get(k, '').strip() for k, _ in COLUMNS}
    rows = []
    for r in ScanRecord.objects.all():
        vals = [fn(r).lower() for _, fn in COLUMNS]
        if q and not any(q in v for v in vals):
            continue
        if any(filters[k] and filters[k].lower() not in v for (k, _), v in zip(COLUMNS, vals)):
            continue
        rows.append(r)
    page = Paginator(rows, 100).get_page(request.GET.get('page'))
    keep = request.GET.copy()
    keep.pop('page', None)
    return render(request, 'letters/scans.html', {
        'page': page, 'q': request.GET.get('q', ''), 'f': filters, 'total': len(rows),
        'offset': page.start_index() - 1 if rows else 0, 'qs': keep.urlencode()})
