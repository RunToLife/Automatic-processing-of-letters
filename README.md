<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/banner.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/banner-light.svg">
  <img alt="Гендальф — письма из сканов в Word. Хаос писем слева проходит под сканирующим Оком и ложится ровными стопками .docx справа." src="assets/banner.svg" width="100%">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/typing.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/typing-light.svg">
  <img alt="Скан письма → Word-документ. Автоматически. OCR Tesseract: русский + английский. Таблицы остаются таблицами. Реестр «СКАНЫ» с фильтрами и поиском." src="assets/typing.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/stack.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/stack-light.svg">
  <img alt="Python 3.11/3.12 · Django 5.1 · PyMuPDF · Tesseract OCR · OCRmyPDF · python-docx · Pillow · NumPy · SQLite · Waitress · WhiteNoise" src="assets/stack.svg">
</picture>

</div>

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/divider.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/divider-light.svg">
  <img alt="" src="assets/divider.svg" width="100%">
</picture>
</p>

# Гендальф — автоматическая обработка писем из сканов в Word

> **Интерактивная сцена:** [`docs/index.html`](docs/index.html) — письма летят к курсору и сортируются (после включения GitHub Pages: *Settings → Pages → Branch → `/docs`*).

## О проекте

Веб-приложение на **Django** для локальной сети. Пользователь загружает скан письма (PDF), система
преобразует его в Word-документ (текстовые PDF разбираются напрямую, сканы распознаются OCR Tesseract,
русский + английский). Скан и документ показываются рядом, документ можно править и сохранить как `.docx`
на свой компьютер. Все сохранения попадают в общий реестр «СКАНЫ» с фильтрами и поиском.

### Как работает преобразование

* **Всё лежит там же, где в оригинале.** Из PDF берётся не просто текст, а геометрия страницы: положение каждого слова, шрифт, размер,
  жирный/курсив. По ней восстанавливается вёрстка: центрированная шапка, «реквизиты слева / адресат справа», красная строка и выравнивание
  по ширине, подпись «должность — ФИО» на одной строке, интервалы между блоками, подчёркивание под шапкой, логотипы и печати (картинки
  поверх текста остаются на своих местах). Поля и размер страницы Word берутся из оригинала, поэтому отступы совпадают.
* **Таблицы остаются таблицами** — в Word создаются настоящие таблицы с теми же колонками, строками и объединёнными ячейками (colspan/rowspan):
  * с полной сеткой линий;
  * с частью линий (рамка, только горизонтальные линии, линия под шапкой) — границы повторяют оригинал по каждой стороне ячейки;
  * без линий вообще (колонки выровнены пробелами) — таблица без границ; заливка шапки и «зебра» сохраняются.
* Страницы с текстовым слоем разбирает PyMuPDF (слова, шрифты, линии и заливки из векторной графики).
* Страницы-сканы — связка **OCRmyPDF + Tesseract**:
  1. OCRmyPDF определяет ориентацию каждой страницы-скана (OSD) и разворачивает перевёрнутые и лежащие на боку листы; текстовые
     страницы документа он не трогает (`letters/ocrprep.py`);
  2. выравнивание наклона (до ±4°) → поиск линий таблиц (numpy) и их стирание → Tesseract (`rus+eng`, LSTM, 300 dpi) —
     слова с точными рамками, а затем отдельный проход по ячейкам таблиц. Эти данные нужны для вёрстки, поэтому текстовый слой OCRmyPDF
     не используется: он подготавливает страницу, а распознаёт Tesseract напрямую.
  Если OCRmyPDF или Ghostscript не установлены либо шаг не удался, преобразование продолжается без него (в окне появится предупреждение).
  Кегль определяется по ширине строки (строки в Word получаются той же ширины, что в скане, и переносятся так же), жирность — по толщине штриха;
  мелкие ячейки таблиц (номера, количество) распознаются отдельно, поэтому «1, 2, 3» не превращаются в мусор.
* Результат правится в окне (оно показывает страницу с теми же полями и отступами); при сохранении собирается `.docx`
  (Times New Roman/Arial по оригиналу, размеры и поля страницы как в оригинале, разрывы страниц сохраняются).

Качество OCR зависит от скана: чистые сканы 300 dpi распознаются почти безошибочно; печати
и рукописный текст нужно вычитывать в окне редактирования. На сканах картинки (логотипы, печати) не переносятся — только текст и таблицы.

### Что лежит в репозитории

| Путь | Назначение |
|---|---|
| `gendalf/`, `letters/`, `templates/` | код приложения |
| `db.sqlite3` | готовая база SQLite: таблицы и пользователь `admin/admin` (создаётся миграцией `letters/migrations/0002_create_admin.py`) |
| `vendor/wheels/` | **все Python-библиотеки** (Windows x64 и Linux x64, Python 3.11/3.12) — установка без интернета |
| `tessdata/` | модели Tesseract: `rus`, `eng` и `osd` (определение ориентации страницы для OCRmyPDF) — доустанавливать не нужно |
| `requirements.txt` | список библиотек |
| `check.bat`, `manage.py check_ocr` | проверка Tesseract, Ghostscript и OCRmyPDF на этой машине |
| `setup.bat` / `setup.sh` | установка; `run.bat` / `run.sh` — запуск |

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/divider.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/divider-light.svg">
  <img alt="" src="assets/divider.svg" width="100%">
</picture>
</p>

## Возможности

* Авторизация (логины/пароли — в SQLite, `db.sqlite3`). Администратор: **`admin` / `admin`** (смените пароль после запуска).
  Новых пользователей добавляет администратор: меню «Пользователи» (`/admin/`).
* **Загрузка PDF-писем**: слева PDF-скан, справа редактируемый Word-документ (жирный/курсив/подчёркивание,
  выравнивание, списки, заголовки). Кнопка **«Сохранить WORD файл»** → окно: название файла, № входящего письма,
  дата обработки, папка → файл записывается **на компьютере пользователя**, запись попадает в «СКАНЫ».
* **СКАНЫ**: таблица (№ п/п, название, № входящего, дата сохранения, дата обработки, путь-ссылка),
  фильтр по каждому столбцу и поиск слова по всем столбцам сразу.

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/divider.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/divider-light.svg">
  <img alt="" src="assets/divider.svg" width="100%">
</picture>
</p>

## Быстрый старт

### Что нужно скачать и поставить (один раз, на компьютере-сервере)

Программы ставятся обычными установщиками. Всё остальное (Django, PyMuPDF, OCRmyPDF, python-docx, waitress и т. д.)
лежит в папке проекта `vendor/wheels` и ставится без интернета.

| Что | Откуда | Что нажимать |
|---|---|---|
| **Python 3.11 или 3.12**, 64-бит (3.13 пока не подходит: для него нет готовых библиотек в `vendor/wheels`) | [python.org/downloads/windows](https://www.python.org/downloads/windows/) → *Windows installer (64-bit)* | В первом окне установщика поставьте галочку **Add python.exe to PATH** |
| **Tesseract OCR** — распознаёт текст на сканах | [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki) → *tesseract-ocr-w64-setup-…exe* | Путь по умолчанию `C:\Program Files\Tesseract-OCR` не менять. Языки выбирать не нужно: русская, английская и OSD-модели лежат в `tessdata/` проекта |
| **Ghostscript** — нужен OCRmyPDF, чтобы разворачивать перевёрнутые и лежащие на боку сканы | [ghostscript.com/releases/gsdnld.html](https://ghostscript.com/releases/gsdnld.html) → *Ghostscript … for Windows (64 bit)* | Путь по умолчанию (`C:\Program Files\gs`) не менять |

Linux (Ubuntu/Debian): `sudo apt install python3-venv tesseract-ocr ghostscript` (необязательно ещё `unpaper` — чистка сканов,
см. настройку `GENDALF_OCRMYPDF_CLEAN`).

Ghostscript и OCRmyPDF необязательны: без них всё работает как раньше, но перевёрнутые листы не исправляются.
Tesseract и Python обязательны. Пользователям на своих компьютерах нужен только современный браузер (Chrome/Edge/Firefox).

### Запуск

**Windows**
1. Скопируйте папку проекта на сервер (например, в `C:\Gendalf`). Путь лучше без кириллицы и пробелов.
2. Дважды щёлкните **`setup.bat`**. Он создаст окружение `.venv`, поставит библиотеки из `vendor\wheels`, применит миграции БД,
   соберёт статику и в конце выведет проверку связки, например:
   ```
   [OK   ] Tesseract — tesseract v5.x
   [OK   ] tessdata/rus.traineddata
   [OK   ] OCRmyPDF (пакет Python)
   [OK   ] Ghostscript — C:\Program Files\gs\gs10.xx\bin\gswin64c.exe
   [OK   ] Пробный прогон OCRmyPDF (поворот страницы)
   ```
   Строка `[нет  ]` — необязательная часть не готова (система будет работать без неё), `[ОШИБКА]` — без этого работать не будет
   (чаще всего не установлен Tesseract).
3. Дважды щёлкните **`run.bat`** — сервер запустится на порту 8000. Окно закрывать нельзя: пока оно открыто, сервис работает.
4. Откройте в браузере `http://localhost:8000`. Первый вход: логин `admin`, пароль `admin` — сразу смените его
   (`/admin/` → Пользователи → admin).

Проверить установку в любой момент можно двойным щелчком по **`check.bat`** (или `.venv\Scripts\python.exe manage.py check_ocr`).

**Linux / macOS**
```bash
./setup.sh      # окружение + библиотеки + БД + проверка
./run.sh        # запуск
```

**Вручную (любая ОС)**
```bash
python -m venv .venv
.venv/bin/pip install --no-index --find-links vendor/wheels -r requirements.txt   # Windows: .venv\Scripts\pip
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check_ocr
.venv/bin/python waitress_run.py
```

**Открытие из сети.** Узнайте IP сервера (`ipconfig` / `ip a`), например `192.168.1.10`. Пользователи открывают
`http://192.168.1.10:8000`. Если страница не открывается — разрешите входящий TCP-порт 8000 в брандмауэре сервера
(Windows: «Брандмауэр → Правила для входящих подключений → Создать правило → Порт 8000»).
Порт и адрес меняются переменными `GENDALF_PORT`, `GENDALF_HOST`.

**Автозапуск на Windows** (чтобы сервис поднимался после перезагрузки сервера): «Планировщик заданий → Создать задачу →
Триггер: при входе в систему (или при запуске) → Действие: запуск программы `C:\Gendalf\run.bat`, «Рабочая папка» `C:\Gendalf`».

### Настройки (переменные окружения, все необязательны)

| Переменная | По умолчанию |
|---|---|
| `GENDALF_PORT` / `GENDALF_HOST` | `8000` / `0.0.0.0` |
| `GENDALF_SECRET_KEY` | задайте свой длинный случайный ключ на рабочем сервере |
| `GENDALF_TZ` | `Europe/Moscow` |
| `GENDALF_OCR_LANGS` | `rus+eng` |
| `GENDALF_OCR_DPI` | `300` (выше — точнее, но медленнее) |
| `TESSERACT_CMD` | полный путь к `tesseract.exe`, если его нет в PATH |
| `GENDALF_OCRMYPDF` | `auto` — использовать OCRmyPDF, если он есть и сработал (по умолчанию); `on` — обязательно, иначе ошибка; `off` — выключить |
| `GENDALF_OCRMYPDF_DESKEW` | `1` — выравнивать наклон силами OCRmyPDF (по умолчанию `0`: свой алгоритм не портит ровные сканы) |
| `GENDALF_OCRMYPDF_CLEAN` | `1` — чистка скана через unpaper (по умолчанию `0`) |
| `GENDALF_OCRMYPDF_TIMEOUT` | секунд на подготовку документа, по умолчанию `900` |
| `GENDALF_CSRF_ORIGINS` | адреса через запятую (нужно только за прокси/по HTTPS) |

### Безопасность

Сервис рассчитан на закрытую локальную сеть (HTTP без шифрования). Смените пароль `admin`, задайте
`GENDALF_SECRET_KEY`, не публикуйте порт в интернет.

### Перенос на другой компьютер

Всё состояние сервиса — это папка проекта, а в ней один файл данных: **`db.sqlite3`** (пользователи и реестр «СКАНЫ»).
Сами Word-файлы на сервере не хранятся: они сохраняются на компьютерах пользователей, в реестре лишь ссылки на них.

1. На старом сервере **остановите** сервис (закройте окно `run.bat`), чтобы база не писалась в момент копирования.
2. Скопируйте папку проекта на новую машину целиком (флешка, сетевая папка, архив) **кроме папок `.venv` и `staticfiles`** —
   окружение привязано к путям и версии Python старого компьютера и не переносится, оно создаётся заново.
   Важно взять `db.sqlite3` из рабочей папки: именно в нём ваши пользователи и записи реестра.
3. На новой машине поставьте Python, Tesseract и Ghostscript (таблица выше) — версии могут быть новее.
4. Запустите `setup.bat` (на Linux — `./setup.sh`), убедитесь, что проверка прошла, затем `run.bat`.
   `setup.bat` не затирает существующую базу, он лишь применяет недостающие миграции.
5. Если задавали переменные окружения (`GENDALF_SECRET_KEY`, `GENDALF_PORT`, `TESSERACT_CMD` и др.), задайте их и на новой машине.
   При смене `GENDALF_SECRET_KEY` пользователям придётся войти заново — данные не пострадают.
6. Пользователям сообщите новый адрес (`http://<IP нового сервера>:8000`) или назначьте новому серверу прежний IP / имя.
7. Откройте порт 8000 в брандмауэре нового сервера.

Чтобы **создать резервную копию**, достаточно копировать `db.sqlite3` (при остановленном сервисе) — и держать под рукой установщики из таблицы выше.

### Если что-то не работает

Первым делом запустите `check.bat` (или `manage.py check_ocr`) — он покажет, чего не хватает.

| Симптом | Причина и решение |
|---|---|
| `Python not found` в `setup.bat` | Python не установлен или при установке не стояла галочка *Add to PATH*: переустановите, отметив её |
| `Offline install failed` в `setup.bat` | Нет колёс под вашу версию Python (нужен 3.11 или 3.12, 64-бит). Скрипт попробует поставить из интернета |
| «Не найден Tesseract OCR» в окне сервиса | Tesseract не установлен или стоит не в `C:\Program Files\Tesseract-OCR`: задайте `TESSERACT_CMD` (в `run.bat` есть готовая закомментированная строка) |
| `[нет  ] Ghostscript` | Установите Ghostscript. До тех пор сервис работает, но перевёрнутые сканы не исправляет |
| В окне предупреждение «OCRmyPDF не применён (…)» | Скан обработан без OCRmyPDF; текст ошибки в скобках. Чаще всего не найден Ghostscript или слишком большой документ (`GENDALF_OCRMYPDF_TIMEOUT`) |
| Перевёрнутую страницу не развернуло | Ориентацию определяют по тексту: на листе из одной-двух строк OCRmyPDF её не определит — разверните страницу в PDF вручную |
| Страница не открывается с других компьютеров | Не открыт порт 8000 в брандмауэре сервера |

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/divider.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/divider-light.svg">
  <img alt="" src="assets/divider.svg" width="100%">
</picture>
</p>

## Использование

После запуска откройте адрес сервера в браузере, войдите (`admin` / `admin`, пароль сразу смените), загрузите PDF-письмо — слева появится скан, справа редактируемый Word-документ; кнопка **«Сохранить WORD файл»** добавляет запись в реестр **«СКАНЫ»** (подробности — в разделе «Возможности»).

### Как сохраняется файл на машину пользователя

Сервер собирает `.docx`, а **запись файла выполняет браузер пользователя**:

* Chrome/Edge на `localhost` или по HTTPS — кнопка «Выбрать папку…» открывает системный диалог, файл пишется прямо в папку.
* Обычный доступ по `http://IP-сервера:8000` — браузеры не дают выбрать папку на небезопасных адресах; тогда файл
  скачивается браузером (в «Загрузки» или с запросом места — включите в настройках браузера
  «Всегда спрашивать, куда сохранять файлы»). Чтобы получить системный диалог и по http, в Chrome/Edge откройте
  `chrome://flags/#unsafely-treat-insecure-origin-as-secure`, добавьте `http://IP-сервера:8000` и включите параметр.

**Путь в таблице «СКАНЫ».** Браузер не сообщает полный путь выбранной папки, поэтому в окне сохранения есть поле
«Папка» (запоминается) — впишите путь (`C:\Письма` или `\\сервер\общая\Письма`). В реестр попадёт
`путь\название.docx` в виде ссылки. Браузеры не открывают `file://` со страниц по http, поэтому клик по ссылке
ещё и копирует путь в буфер обмена — его можно вставить в «Проводник».

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/divider.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/divider-light.svg">
  <img alt="" src="assets/divider.svg" width="100%">
</picture>
</p>

## Roadmap

Идеи для развития выведены из ограничений, описанных выше. Это направления, а не обязательства.

- [ ] Таблицы без линий сетки (только выравнивание пробелами) — сейчас распознаются как обычный текст.
- [ ] Рукописный текст и печати — сейчас такие места нужно вычитывать в окне редактирования.
- [ ] HTTPS «из коробки» — сейчас сервис рассчитан на закрытую сеть по HTTP, а выбор папки в браузере работает только на `localhost`/HTTPS.
- [ ] Автотесты конвертера и представлений (`letters/tests.py` пока пуст).

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/divider.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/divider-light.svg">
  <img alt="" src="assets/divider.svg" width="100%">
</picture>
</p>

## Contributing

1. Сделайте форк и создайте ветку под свою задачу.
2. Запустите проект локально в режиме разработки (команда ниже) и проверьте изменение руками на PDF-письме и скане.
3. Откройте pull request с описанием: что изменено и как проверить.

**Запуск для разработки**

```bash
GENDALF_DEBUG=1 .venv/bin/python manage.py runserver
.venv/bin/python manage.py test letters      # тесты преобразования (таблицы, вёрстка, скан — нужен Tesseract)
```

Код преобразования: `letters/converter.py` (чтение PDF и OCR), `letters/layout.py` (восстановление вёрстки), `letters/docxbuild.py` (HTML → DOCX).

Визуальные ассеты (`assets/*.svg`) собираются генератором — не правьте SVG руками, а меняйте цвета и тексты в `tools/visuals/*.py` и запускайте `python3 tools/build_visuals.py` (подробности — в [`tools/README.md`](tools/README.md)).

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/divider.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/divider-light.svg">
  <img alt="" src="assets/divider.svg" width="100%">
</picture>
</p>

## License

Файл лицензии в репозиторий пока не добавлен, поэтому права на код сохраняются за его автором(ами). Для использования или распространения свяжитесь с владельцем репозитория ([RunToLife](https://github.com/RunToLife)).

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/footer.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/footer-light.svg">
  <img alt="Золотая печать с руной и цепочка сигнальных маяков" src="assets/footer.svg" width="100%">
</picture>

</div>
