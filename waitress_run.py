"""Запуск сервера «Гендальф» (waitress) для локальной сети."""
import os
import sys

from waitress import serve

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gendalf.settings')
from django.core.wsgi import get_wsgi_application  # noqa: E402

if __name__ == '__main__':
    host = os.environ.get('GENDALF_HOST', '0.0.0.0')
    port = int(os.environ.get('GENDALF_PORT', '8000'))
    print(f'Гендальф запущен: http://{host}:{port}  (Ctrl+C — остановка)')
    sys.stdout.flush()
    serve(get_wsgi_application(), host=host, port=port, threads=8,
          channel_timeout=900, max_request_body_size=300 * 1024 * 1024)
