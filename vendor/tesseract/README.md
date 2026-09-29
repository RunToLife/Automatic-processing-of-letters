# vendor/tesseract — портативный Tesseract OCR для сборки

Эта папка **не заполнена автоматически** — сама сборка Tesseract под Windows
не скачивалась (в окружении, где готовился этот проект, нет доступа к
Windows-бинарям). Заполнить её нужно вручную один раз, на своей Windows-машине,
перед запуском `build.bat`.

## Что должно лежать в этой папке в итоге

```
vendor/tesseract/
  tesseract.exe          - сам исполняемый файл
  *.dll                   - все DLL, от которых зависит tesseract.exe
  tessdata/
    rus.traineddata       - русский язык
    eng.traineddata       - английский язык
    osd.traineddata       - определение ориентации/скрипта (нужен tesseract'у
                            внутренне почти всегда, даже если явно не используется)
  LICENSE.txt             - текст лицензии Tesseract (Apache 2.0), см. ниже
```

`tessdata/` уже создана как пустая папка (с `.gitkeep`) — просто скопируйте
в неё файлы `.traineddata` для нужных вам языков.

## Как получить эти файлы

Самый простой и надёжный способ — взять их из уже установленного на Windows
пакета **Tesseract for Windows** (сборки UB-Mannheim):

1. Скачайте и установите Tesseract с
   https://github.com/UB-Mannheim/tesseract/wiki (например,
   `tesseract-ocr-w64-setup-5.x.x.exe`). При установке отметьте нужные
   языковые пакеты (как минимум русский и английский) — либо просто
   поставьте с языками по умолчанию и докиньте `.traineddata` вручную (шаг 3).
2. После установки Tesseract обычно лежит в
   `C:\Program Files\Tesseract-OCR\`. Скопируйте оттуда в `vendor/tesseract/`
   этого репозитория:
   - `tesseract.exe`
   - **все** `.dll` файлы из этой же папки (libtesseract, leptonica,
     зависимости вроде `libpng`, `libjpeg`, `zlib` и т.п. — проще скопировать
     все `.dll`, чем угадывать, какие именно нужны)
3. Скопируйте нужные языки из `C:\Program Files\Tesseract-OCR\tessdata\` в
   `vendor/tesseract/tessdata/`:
   - `rus.traineddata`
   - `eng.traineddata`
   - `osd.traineddata`
   Если нужны дополнительные языки — см. раздел «Добавление языков OCR» в
   `DOCS_DIST.md`.
4. Возьмите текст лицензии Tesseract (Apache License 2.0) и положите его как
   `vendor/tesseract/LICENSE.txt` — например, скопируйте
   `C:\Program Files\Tesseract-OCR\LICENSE` или возьмите актуальный текст с
   https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE.
   Правило Apache 2.0 требует поставлять текст лицензии вместе с бинарником —
   `build.bat` копирует этот файл в `dist/Гендальф/` автоматически.

## Проверка перед сборкой

`build.bat` сам проверяет, что `vendor/tesseract/tesseract.exe` существует, и
останавливается с понятным сообщением, если файла нет. Но полезно проверить
и вручную, что скопированный `tesseract.exe` вообще запускается на этой же
машине:

```powershell
vendor\tesseract\tesseract.exe --version
vendor\tesseract\tesseract.exe --list-langs --tessdata-dir vendor\tesseract\tessdata
```

Вторая команда должна вывести `rus` и `eng` в списке языков.

## Почему нельзя просто взять tesseract.exe с любого компьютера

Нужна версия, скомпилированная под ту же архитектуру (x64), и лежащая рядом
со ВСЕМИ своими DLL-зависимостями — Tesseract линкуется динамически, и без
нужных DLL он просто не запустится ни на вашей машине, ни тем более на
"чистой" машине пользователя, где этих DLL нет вообще нигде в системе.
Установщик UB-Mannheim статически же собирает и упаковывает всё, что нужно, в
одну папку — это и есть самый простой источник файлов для этой папки.
