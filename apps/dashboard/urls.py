from django.urls import path
from apps.dashboard import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('about/', views.about, name='about'),
    path('support/', views.support, name='support'),
    path('tools/guest/', views.guest_tools, name='guest_tools'),
    path('zayro-admin/', views.admin_panel, name='admin_panel'),
    path('zayro-admin/toggle/<slug:slug>/', views.toggle_tool_privilege, name='toggle_tool'),
    # Popup inline auth (no page redirect, JSON only)
    path('ajax/register/', views.ajax_register,   name='ajax_register'),
    path('ajax/login/',    views.ajax_login,      name='ajax_login'),
    path('ajax/support/',     views.submit_support,   name='submit_support'),
    path('ajax/suggestion/',  views.submit_suggestion, name='submit_suggestion'),
    path('zayro-admin/suggestions/<int:pk>/update/', views.update_suggestion, name='update_suggestion'),
]
