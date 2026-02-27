from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Registration (Admin only)
    path('', views.register_letter, name='register_letter'),
    path('register/complaint/', views.register_complaint, name='register_complaint'),

    # Admin Dashboard
    path('dashboard/', views.index, name='index'),
    path('dashboard/main/', views.dashboard_main, name='dashboard_main'),

    # Department Dashboard
    path('department/', views.dept_dashboard, name='dept_dashboard'),

    # Forwarding & Reply
    path('forward/<int:pk>/', views.forward_record, name='forward_record'),
    path('reply/<int:pk>/', views.reply_record, name='reply_record'),

    # List Views
    path('letters/', views.letters_list, name='letters_list'),
    path('complaints/', views.complaints_list, name='complaints_list'),
    path('replies/', views.replies_received, name='replies_received'),
    path('record/<int:pk>/', views.record_detail, name='record_detail'),
    path('record/<int:pk>/delete/', views.delete_record, name='delete_record'),
    path('reply-detail/<int:pk>/', views.reply_detail, name='reply_detail'),
    path('reply/<int:pk>/toggle-read/', views.toggle_reply_read_status, name='toggle_reply_read_status'),

    # Inbox (Removed from UI temporarily, model remains)
    # path('inbox/', views.inbox, name='inbox'),

    # Other pages
    path('analytics/', views.Analytics_Reporting, name='Analytics & Reporting'),
    path('documents/', views.Document_Repository, name='Document Repository'),
]