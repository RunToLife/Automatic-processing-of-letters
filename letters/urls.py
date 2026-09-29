from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("upload/", views.upload_page, name="upload_page"),
    path("api/recognize", views.api_recognize, name="api_recognize"),
    path("api/save", views.api_save, name="api_save"),
    path("preview/<str:token>.pdf", views.serve_pdf_preview, name="serve_pdf_preview"),
    path("scans/", views.scans_page, name="scans_page"),
    path("download/<int:scan_id>", views.download_scan, name="download_scan"),
]
