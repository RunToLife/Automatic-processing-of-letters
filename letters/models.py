from django.conf import settings
from django.db import models
from django.utils import timezone


class ScanRecord(models.Model):
    """Запись о сохранённом WORD-файле (таблица «СКАНЫ»)."""

    title = models.CharField('Название письма', max_length=255)
    incoming_number = models.CharField('№ входящего письма', max_length=100, blank=True)
    processed_date = models.DateField('Дата обработки письма', null=True, blank=True)
    saved_at = models.DateTimeField('Дата сохранения', default=timezone.now)
    path = models.CharField('Путь к письму', max_length=1000)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, verbose_name='Кто сохранил')

    class Meta:
        ordering = ['-saved_at', '-id']
        verbose_name = 'Скан письма'
        verbose_name_plural = 'Сканы писем'

    def __str__(self):
        return f'{self.title} ({self.incoming_number})'

    @property
    def saved_display(self):
        return timezone.localtime(self.saved_at).strftime('%d.%m.%Y %H:%M')

    @property
    def processed_display(self):
        return self.processed_date.strftime('%d.%m.%Y') if self.processed_date else ''

    @property
    def file_url(self):
        """file:// ссылка (UNC-пути и диски Windows, пути Linux/Mac)."""
        p = self.path.strip().replace('\\', '/')
        if p.startswith('//'):
            return 'file:' + p
        if p.startswith('/'):
            return 'file://' + p
        return 'file:///' + p
