from django.contrib import admin

from .models import Scan


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "incoming_number", "saved_date", "created_by", "created_at")
    search_fields = ("title", "incoming_number", "file_path")
