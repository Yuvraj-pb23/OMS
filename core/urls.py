from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('inbox/', views.inbox, name='inbox'),
    path('Document Repository/', views.Document_Repository, name='Document Repository'),
    path('Analytics & Reporting/', views.Analytics_Reporting, name='Analytics & Reporting'),

    
]