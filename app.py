import os
import uuid
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, send_file, jsonify, abort, send_from_directory
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


@app.route("/api/browse")
@login_required
def api_browse():
    rel_path = request.args.get("path", "")
    root = os.path.realpath(config.SAVE_ROOT_DIR)
    target = os.path.realpath(os.path.join(root, rel_path.lstrip("/\\")))

    if not (target == root or target.startswith(root + os.sep)):
        return jsonify({"error": "Недопустимый путь"}), 400
    if not os.path.isdir(target):
        return jsonify({"error": "Папка не найдена"}), 404

    entries = []
    with os.scandir(target) as it:
        for entry in it:
            if entry.is_dir():
                entries.append(entry.name)
    entries.sort(key=str.lower)

    rel_current = os.path.relpath(target, root)
    rel_current = "" if rel_current == "." else rel_current.replace(os.sep, "/")

    parent = None
    if rel_current != "":
        parent = os.path.dirname(rel_current)

    return jsonify({
        "root_label": config.SAVE_ROOT_DIR,
        "current": rel_current,
        "parent": parent,
        "dirs": entries,
    })


@app.route("/api/browse/create", methods=["POST"])
@login_required
def api_browse_create():
    data = request.get_json(force=True) or {}
    rel_path = data.get("path", "")
    name = secure_filename(data.get("name", "")).strip()
    if not name:
        return jsonify({"error": "Укажите имя папки"}), 400

    root = os.path.realpath(config.SAVE_ROOT_DIR)
    parent = os.path.realpath(os.path.join(root, rel_path.lstrip("/\\")))
    if not (parent == root or parent.startswith(root + os.sep)):
        return jsonify({"error": "Недопустимый путь"}), 400

    new_dir = os.path.join(parent, name)
    os.makedirs(new_dir, exist_ok=True)
    return jsonify({"ok": True})


@app.route("/api/save", methods=["POST"])
@login_required
def api_save():
    data = request.get_json(force=True) or {}
    folder_rel = data.get("folder", "")
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

    root = os.path.realpath(config.SAVE_ROOT_DIR)
    folder = os.path.realpath(os.path.join(root, folder_rel.lstrip("/\\")))
    if not (folder == root or folder.startswith(root + os.sep)):
        return jsonify({"error": "Недопустимый путь сохранения"}), 400
    os.makedirs(folder, exist_ok=True)

    full_path = os.path.join(folder, filename)
    ocr.editable_text_to_docx(text, full_path)

    title = os.path.splitext(filename)[0]
    saved_date = processed_date
    scan_id = db.add_scan(
        title=title,
        incoming_number=incoming_number,
        saved_date=saved_date,
        file_path=full_path,
        created_by=current_user.username,
    )

    return jsonify({"ok": True, "scan_id": scan_id, "path": full_path})


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
    path = row["file_path"]
    if not os.path.isfile(path):
        abort(404)
    directory, name = os.path.split(path)
    return send_from_directory(directory, name, as_attachment=False)


if __name__ == "__main__":
    config.ensure_dirs()
    db.init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
