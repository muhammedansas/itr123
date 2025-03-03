from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signin/', views.signin, name='signin'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout, name='logout'),
    path('ca/signup/', views.ca_signup, name='ca_signup'),
    path('ca/signin/', views.ca_signin, name='ca_signin'),
    path('ca/logout/', views.ca_logout, name='ca_logout'),
    path('ca/dashboard/', views.ca_dashboard, name='ca_dashboard'),
]