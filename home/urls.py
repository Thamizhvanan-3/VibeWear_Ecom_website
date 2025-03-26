from django.urls import path
from . import views

urlpatterns=[
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('about/',views.about, name='about'),
    path('contact/>',views.contact, name='contact'),
    path('contact/submit/', views.contact_submit, name='contact_submit'),
]