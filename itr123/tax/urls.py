from django.urls import path
from . import views
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('tax_questions/', views.tax_questions, name='tax_questions'),
    path('user_home/', views.user_home, name='user_home'),
    path('tax/view/<str:filing_id>/', views.view_tax_filing, name='view_tax_filing'),
    path('myfilings/', views.my_filings, name='myfilings'),
    path("save-message/", views.save_message, name="save_message"),
    path("download-all-docs/<str:filing_id>/", views.download_all_documents, name="download_all_docs"),
    path('upload-document/', views.upload_document, name='upload_document'),
    path('tax-details/<str:filing_id>/', views.view_tax_details, name='view_tax_details'),
    path('tax-details/<str:filing_id>/update/', views.update_tax_details, name='update_tax_details'),
        path('profile/', views.user_profile, name='user_profile'),
    path('profile/update/', views.update_user_profile, name='update_user_profile'),
    path('download_tax_details/<str:filing_id>/', views.download_tax_details, name='download_tax_details'),
]