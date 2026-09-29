import json
import os
import uuid
from datetime import datetime

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.core.exceptions import SuspiciousFileOperation
from django.utils.text import get_valid_filename
from django.views.decorators.http import require_GET, require_http_methods

from . import ocr
from .models import Scan


def _secure_filename(name: str) -> str:
    """Убирает небезопасные символы из имени файла/папки. Возвращает
    пустую строку, если после очистки не осталось ничего допустимого."""
    name = (name or "").strip()
    if not name:
        return ""
    try:
        return get_valid_filename(name)
    except SuspiciousFileOperation:
        return ""


# ---------------------------------------------------------------- авторизация

def login_view(request):
    if request.user.is_authenticated:
        return redirect("upload_page")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get("next") or reverse("upload_page")
            return redirect(next_url)
        from django.contrib import messages
        messages.error(request, "Неверный логин или пароль")
    return render(request, "login.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def index(request):
    return redirect("upload_page")


# ------------------------------------------------------------ загрузка писем

@login_required
def upload_page(request):
    return render(request, "upload.html")


@login_required
@require_http_methods(["POST"])
def api_recognize(request):
    file = request.FILES.get("pdf_file")
    if file is None or file.name == "":
        return JsonResponse({"error": "Файл не выбран"}, status=400)
    if not file.name.lower().endswith(".pdf"):
        return JsonResponse({"error": "Ожидается файл в формате PDF"}, status=400)
    if file.size > settings.MAX_PDF_SIZE:
        return JsonResponse({"error": "Файл слишком большой"}, status=400)

    token = uuid.uuid4().hex
    safe_name = _secure_filename(file.name) or "document.pdf"
    stored_name = f"{token}_{safe_name}"
    stored_path = os.path.join(settings.UPLOAD_DIR, stored_name)

    with open(stored_path, "wb") as dest:
        for chunk in file.chunks():
            dest.write(chunk)

    try:
        pages = ocr.recognize_pdf(stored_path)
    except Exception as exc:  # библиотека tesseract может быть не установлена
        return JsonResponse({
            "error": (
                "Не удалось распознать PDF. Убедитесь, что на сервере "
                "установлен Tesseract OCR (см. README). Подробность: "
                f"{exc}"
            )
        }, status=500)

    text = ocr.pages_to_editable_text(pages)

    return JsonResponse({
        "token": token,
        "pdf_url": reverse("serve_pdf_preview", args=[token]),
        "original_filename": file.name,
        "text": text,
        "suggested_filename": os.path.splitext(safe_name)[0],
    })


@login_required
@require_GET
def serve_pdf_preview(request, token):
    token = _secure_filename(token)
    for name in os.listdir(settings.UPLOAD_DIR):
        if name.startswith(token + "_"):
            return FileResponse(
                open(os.path.join(settings.UPLOAD_DIR, name), "rb"),
                content_type="application/pdf",
            )
    raise Http404


@login_required
@require_http_methods(["POST"])
def api_save(request):
    data = json.loads(request.body or "{}")

    filename = _secure_filename(data.get("filename", "")).strip()
    incoming_number = data.get("incoming_number", "").strip()
    processed_date = data.get("processed_date", "").strip()
    text = data.get("text", "")

    if not filename:
        return JsonResponse({"error": "Укажите название файла"}, status=400)
    if not incoming_number:
        return JsonResponse({"error": "Укажите № входящего письма"}, status=400)
    if not processed_date:
        processed_date = datetime.now().strftime("%Y-%m-%d")

    if not filename.lower().endswith(".docx"):
        filename += ".docx"

    # Служебная копия хранится на сервере под собственным именем, чтобы
    # ссылка в реестре "Сканы" работала независимо от того, куда и под
    # каким именем пользователь сохранит файл на своём компьютере.
    archive_filename = f"{uuid.uuid4().hex}.docx"
    archive_path = os.path.join(settings.ARCHIVE_DIR, archive_filename)
    ocr.editable_text_to_docx(text, archive_path)

    title = os.path.splitext(filename)[0]
    scan = Scan.objects.create(
        title=title,
        incoming_number=incoming_number,
        saved_date=processed_date,
        file_path=filename,
        archive_filename=archive_filename,
        created_by=request.user,
    )

    return JsonResponse({
        "ok": True,
        "scan_id": scan.id,
        "filename": filename,
        "download_url": reverse("download_scan", args=[scan.id]),
    })


# --------------------------------------------------------------------- сканы

@login_required
def scans_page(request):
    scans = Scan.objects.all()
    return render(request, "scans.html", {"scans": scans})


@login_required
def download_scan(request, scan_id):
    try:
        scan = Scan.objects.get(id=scan_id)
    except Scan.DoesNotExist:
        raise Http404

    archive_path = os.path.join(settings.ARCHIVE_DIR, scan.archive_filename)
    if not os.path.isfile(archive_path):
        raise Http404

    response = FileResponse(
        open(archive_path, "rb"),
        as_attachment=True,
        filename=scan.file_path,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    return response
