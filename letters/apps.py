from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_default_admin(sender, **kwargs):
    """Создаёт учётную запись администратора Admin/Admin при первом запуске,
    если она ещё не существует. Логины и пароли пользователей хранятся
    в SQLite стандартной моделью django.contrib.auth.User."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    if not User.objects.filter(username="Admin").exists():
        User.objects.create_superuser(username="Admin", password="Admin", email="")


class LettersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "letters"

    def ready(self):
        post_migrate.connect(create_default_admin, sender=self)
