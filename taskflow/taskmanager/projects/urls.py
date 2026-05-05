from django.urls import path
from . import views

urlpatterns = [
    path('projects/new/', views.project_create, name='project_create'),
    path('projects/<uuid:pk>/', views.project_detail, name='project_detail'),
    path('projects/<uuid:pk>/edit/', views.project_edit, name='project_edit'),
    path('projects/<uuid:pk>/delete/', views.project_delete, name='project_delete'),
    path('projects/<uuid:pk>/members/add/', views.project_add_member, name='project_add_member'),
    path('projects/<uuid:pk>/members/<uuid:member_pk>/role/', views.project_member_update, name='project_member_update'),
    path('projects/<uuid:pk>/members/<uuid:member_pk>/remove/', views.project_member_remove, name='project_member_remove'),
    path('projects/<uuid:pk>/hours/<uuid:user_pk>/', views.member_hour_history, name='member_hour_history'),
    path('projects/<uuid:pk>/sprints/new/', views.sprint_create, name='sprint_create'),
    path('projects/<uuid:pk>/sprints/<uuid:sprint_pk>/edit/', views.sprint_update, name='sprint_update'),
    path('projects/<uuid:pk>/roadmap/', views.project_roadmap, name='project_roadmap'),
    path('projects/new/ai/parse/', views.project_create_ai, name='project_create_ai'),
    path('projects/new/ai/confirm/', views.project_create_ai_confirm, name='project_create_ai_confirm'),
    path('projects/<uuid:pk>/summary/pdf/', views.project_executive_summary_pdf, name='project_summary_pdf'),
    path('projects/<uuid:pk>/board-chat/', views.project_board_chat, name='project_board_chat'),
    path('projects/<uuid:pk>/board-chat/apply/', views.project_board_chat_apply, name='project_board_chat_apply'),
]
