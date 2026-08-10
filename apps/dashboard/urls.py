from django.urls import path
from apps.dashboard import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('about/', views.about, name='about'),
    path('zayro-admin/', views.admin_panel, name='admin_panel'),
    path('zayro-admin/toggle/<slug:slug>/', views.toggle_tool_privilege, name='toggle_tool'),
]
