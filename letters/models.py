from django.conf import settings
from django.db import models


class Scan(models.Model):
    title = models.CharField("Название письма", max_length=255)
    incoming_number = models.CharField("№ входящего письма", max_length=100)
    saved_date = models.CharField("Дата сохранения", max_length=20)
    file_path = models.CharField(
        "Имя файла у пользователя", max_length=255,
        help_text="Имя файла, под которым письмо сохранено на компьютере пользователя",
    )
    archive_filename = models.CharField(
        "Служебное имя архивной копии", max_length=64,
        help_text="Имя файла в ARCHIVE_DIR на сервере (для повторного скачивания)",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.title} (№{self.incoming_number})"
