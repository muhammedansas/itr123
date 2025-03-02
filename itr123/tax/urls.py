from django.urls import path
from . import views
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('tax_questions/', views.tax_questions, name='tax_questions'),
    path('user_home/', views.user_home, name='user_home'),
    path('tax/view/<str:filing_id>/', views.view_tax_filing, name='view_tax_filing'),
    path('tax/delete/<str:filing_id>/', views.delete_tax_filing, name='delete_tax_filing'),
    path('tax/download/<str:user_phone>/<str:name>/<str:tax_year>/<str:filename>/',
         views.download_document, name='download_document'),
    path('tax/download-all/<str:filing_id>/',
         views.download_all_documents, name='download_all_documents'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)