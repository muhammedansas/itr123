from django.urls import path
from . import views

urlpatterns = [
    path('', views.tax_questions, name='tax_questions'),
]