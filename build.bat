@echo off
rem =============================================================
rem  Сборка "Гендальф" в Windows-приложение (PyInstaller --onedir)
rem
rem  Запускать на Windows из корня репозитория, где установлен Python 3.
rem  Подробности и диагностика - в DOCS_DIST.md, раздел "Для разработчика".
rem
rem  Отладочная сборка (exe с консолью, вместо обычной без консоли):
rem      set GENDALF_BUILD_CONSOLE=1
rem      build.bat
rem =============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

set "APP_NAME=Гендальф"
set "DIST_DIR=dist\%APP_NAME%"
set "INTERNAL_DIR=%DIST_DIR%\_internal"

echo ============================================
echo   Сборка "%APP_NAME%"
echo ============================================

if not exist "vendor\tesseract\tesseract.exe" (
    echo.
    echo [ОШИБКА] Не найден vendor\tesseract\tesseract.exe
    echo          Заполните папку vendor\tesseract перед сборкой -
    echo          инструкция в vendor\tesseract\README.md
    exit /b 1
)

if "%GENDALF_BUILD_CONSOLE%"=="1" (
    echo Режим: ОТЛАДОЧНАЯ сборка ^(exe с консолью, GENDALF_BUILD_CONSOLE=1^)
) else (
    echo Режим: обычная сборка ^(exe без консоли^)
    echo        Для отладочной сборки: set GENDALF_BUILD_CONSOLE=1 ^&^& build.bat
)

echo.
echo [1/7] Создание чистого виртуального окружения .venv_build ...
if exist ".venv_build" (
    rmdir /s /q ".venv_build"
)
python -m venv .venv_build
if errorlevel 1 (
    echo [ОШИБКА] Не удалось создать виртуальное окружение.
    echo          Убедитесь, что Python 3 установлен и доступен в PATH.
    exit /b 1
)
call ".venv_build\Scripts\activate.bat"

echo.
echo [2/7] Установка зависимостей приложения из requirements.txt ...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить зависимости из requirements.txt
    exit /b 1
)

echo.
echo [3/7] Установка PyInstaller ...
pip install pyinstaller pyinstaller-hooks-contrib
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить PyInstaller
    exit /b 1
)

echo.
echo [4/7] Сбор статики Django ^(collectstatic^) ...
if exist "staticfiles" (
    rmdir /s /q "staticfiles"
)
python manage.py collectstatic --noinput
if errorlevel 1 (
    echo [ОШИБКА] collectstatic завершился с ошибкой
    exit /b 1
)

echo.
echo [5/7] Очистка предыдущей сборки ^(build\, dist\^) ...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo [6/7] Запуск PyInstaller ^(app.spec^) ...
pyinstaller app.spec --noconfirm
if errorlevel 1 (
    echo [ОШИБКА] PyInstaller завершился с ошибкой
    exit /b 1
)

echo.
echo [7/7] Проверка результата сборки ...

if not exist "%DIST_DIR%\%APP_NAME%.exe" (
    echo [ОШИБКА] Не найден %DIST_DIR%\%APP_NAME%.exe - сборка не удалась.
    exit /b 1
)
echo   OK: %DIST_DIR%\%APP_NAME%.exe создан.

if not exist "%INTERNAL_DIR%\vendor\tesseract\tesseract.exe" (
    echo [ОШИБКА] В собранном приложении нет tesseract.exe
    echo          ^(ожидался %INTERNAL_DIR%\vendor\tesseract\tesseract.exe^).
    exit /b 1
)
echo   OK: tesseract.exe присутствует в сборке.

if exist "DOCS_DIST.md" (
    copy /y "DOCS_DIST.md" "%DIST_DIR%\README.md" >nul
    echo   OK: документация скопирована в %DIST_DIR%\README.md
) else (
    echo   [ПРЕДУПРЕЖДЕНИЕ] DOCS_DIST.md не найден - README для пользователя не скопирован.
)

echo.
echo ============================================
echo   Готово! Результат: %DIST_DIR%\
echo ============================================
echo   Перед раздачей пользователям папку можно упаковать в zip
echo   ^(см. DOCS_DIST.md, раздел "Распространение"^).

endlocal
