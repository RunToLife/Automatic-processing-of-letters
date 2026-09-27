import os
import uuid
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    jsonify, abort, send_from_directory
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required,
    current_user
)
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

import config
import db
import ocr

app = Flask(__name__)
app.config["SECRET_KEY"] = config.get_secret_key()
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Пожалуйста, войдите в систему."
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.role = row["role"]


@login_manager.user_loader
def load_user(user_id):
    row = db.get_user_by_id(int(user_id))
    if row is None:
        return None
    return User(row)


@app.before_request
def _ensure_ready():
    config.ensure_dirs()


# ---------------------------------------------------------------- авторизация

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("upload_page"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        row = db.get_user_by_username(username)
        if row is not None and check_password_hash(row["password_hash"], password):
            login_user(User(row))
            next_url = request.args.get("next") or url_for("upload_page")
            return redirect(next_url)
        flash("Неверный логин или пароль", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return redirect(url_for("upload_page"))


# ------------------------------------------------------------ загрузка писем

@app.route("/upload")
@login_required
def upload_page():
    return render_template("upload.html")


@app.route("/api/recognize", methods=["POST"])
@login_required
def api_recognize():
    file = request.files.get("pdf_file")
    if file is None or file.filename == "":
        return jsonify({"error": "Файл не выбран"}), 400
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Ожидается файл в формате PDF"}), 400

    token = uuid.uuid4().hex
    safe_name = secure_filename(file.filename) or "document.pdf"
    stored_name = f"{token}_{safe_name}"
    stored_path = os.path.join(config.UPLOAD_DIR, stored_name)
    file.save(stored_path)

    try:
        pages = ocr.recognize_pdf(stored_path)
    except Exception as exc:  # библиотека tesseract может быть не установлена
        return jsonify({
            "error": (
                "Не удалось распознать PDF. Убедитесь, что на сервере "
                "установлен Tesseract OCR (см. README). Подробность: "
                f"{exc}"
            )
        }), 500

    text = ocr.pages_to_editable_text(pages)

    return jsonify({
        "token": token,
        "pdf_url": url_for("serve_pdf_preview", token=token),
        "original_filename": file.filename,
        "text": text,
        "suggested_filename": os.path.splitext(safe_name)[0],
    })


@app.route("/preview/<token>.pdf")
@login_required
def serve_pdf_preview(token):
    token = secure_filename(token)
    for name in os.listdir(config.UPLOAD_DIR):
        if name.startswith(token + "_"):
            return send_from_directory(config.UPLOAD_DIR, name, mimetype="application/pdf")
    abort(404)


@app.route("/api/save", methods=["POST"])
@login_required
def api_save():
    data = request.get_json(force=True) or {}
    filename = secure_filename(data.get("filename", "")).strip()
    incoming_number = data.get("incoming_number", "").strip()
    processed_date = data.get("processed_date", "").strip()
    text = data.get("text", "")

    if not filename:
        return jsonify({"error": "Укажите название файла"}), 400
    if not incoming_number:
        return jsonify({"error": "Укажите № входящего письма"}), 400
    if not processed_date:
        processed_date = datetime.now().strftime("%Y-%m-%d")

    if not filename.lower().endswith(".docx"):
        filename += ".docx"

    # Служебная копия хранится на сервере под собственным именем, чтобы
    # ссылка в реестре "Сканы" работала независимо от того, куда и под
    # каким именем пользователь сохранит файл на своём компьютере.
    archive_filename = f"{uuid.uuid4().hex}.docx"
    archive_path = os.path.join(config.ARCHIVE_DIR, archive_filename)
    ocr.editable_text_to_docx(text, archive_path)

    title = os.path.splitext(filename)[0]
    scan_id = db.add_scan(
        title=title,
        incoming_number=incoming_number,
        saved_date=processed_date,
        file_path=filename,
        archive_filename=archive_filename,
        created_by=current_user.username,
    )

    return jsonify({
        "ok": True,
        "scan_id": scan_id,
        "filename": filename,
        "download_url": url_for("download_scan", scan_id=scan_id),
    })


# --------------------------------------------------------------------- сканы

@app.route("/scans")
@login_required
def scans_page():
    rows = db.list_scans()
    return render_template("scans.html", scans=rows)


@app.route("/download/<int:scan_id>")
@login_required
def download_scan(scan_id):
    row = db.get_scan(scan_id)
    if row is None:
        abort(404)
    archive_name = row["archive_filename"]
    if not os.path.isfile(os.path.join(config.ARCHIVE_DIR, archive_name)):
        abort(404)
    return send_from_directory(
        config.ARCHIVE_DIR, archive_name,
        as_attachment=True, download_name=row["file_path"],
    )


if __name__ == "__main__":
    config.ensure_dirs()
    db.init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
