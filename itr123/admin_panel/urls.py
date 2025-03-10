from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('ca/<str:ca_phone>/', views.manage_ca, name='manage_ca'),
    path('ca/<str:ca_phone>/update/', views.update_ca_mapping, name='update_ca_mapping'),
]