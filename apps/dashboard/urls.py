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
    path('zayro-admin/suggestions/<str:pk>/update/', views.update_suggestion, name='update_suggestion'),
    path('zayro-admin/sessions/<str:session_key>/delete/', views.delete_session, name='delete_session'),
    path('zayro-admin/sessions/delete-all/', views.delete_all_sessions, name='delete_all_sessions'),
    path('zayro-admin/media/',              views.media_browser,        name='admin_media'),
    path('zayro-admin/media/delete/',       views.media_delete_file,    name='admin_media_delete'),
    path('zayro-admin/media/delete-all/',   views.media_delete_all,     name='admin_media_delete_all'),
]
