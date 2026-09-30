from django.urls import path

from . import views

urlpatterns = [
    path('', views.upload, name='upload'),
    path('convert/', views.convert, name='convert'),
    path('docx/', views.build_docx, name='build_docx'),
    path('register/', views.register, name='register'),
    path('scans/', views.scans, name='scans'),
]
