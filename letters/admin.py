from django.contrib import admin

from .models import ScanRecord


@admin.register(ScanRecord)
class ScanRecordAdmin(admin.ModelAdmin):
    list_display = ('title', 'incoming_number', 'processed_date', 'saved_at', 'path', 'user')
    search_fields = ('title', 'incoming_number', 'path')
    list_filter = ('processed_date', 'user')
