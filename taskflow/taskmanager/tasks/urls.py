from django.urls import path
from . import views

urlpatterns = [
    path('my-tasks/', views.my_tasks, name='my_tasks'),
    path('projects/<uuid:project_pk>/tasks/new/', views.task_create, name='task_create'),
    path('projects/<uuid:project_pk>/tasks/<uuid:pk>/', views.task_detail, name='task_detail'),
    path('projects/<uuid:project_pk>/tasks/<uuid:pk>/edit/', views.task_edit, name='task_edit'),
    path('projects/<uuid:project_pk>/tasks/<uuid:pk>/delete/', views.task_delete, name='task_delete'),
    path('projects/<uuid:project_pk>/tasks/list-data/', views.task_list_data, name='task_list_data'),
    path('projects/<uuid:project_pk>/tasks/<uuid:pk>/status/', views.task_update_status, name='task_update_status'),
    path('projects/<uuid:project_pk>/tasks/<uuid:pk>/title/', views.task_update_title, name='task_update_title'),
    path('projects/<uuid:project_pk>/tasks/<uuid:task_pk>/comments/', views.comment_create, name='comment_create'),
    path('projects/<uuid:project_pk>/tasks/<uuid:task_pk>/comments/<uuid:pk>/delete/', views.comment_delete, name='comment_delete'),
    path('projects/<uuid:project_pk>/tasks/<uuid:task_pk>/attachments/', views.attachment_upload, name='attachment_upload'),
    path('projects/<uuid:project_pk>/tasks/<uuid:task_pk>/timelogs/', views.timelog_create, name='timelog_create'),
    path('projects/<uuid:project_pk>/tasks/<uuid:pk>/validate-hours/', views.task_validate_hours, name='task_validate_hours'),
    path('projects/<uuid:project_pk>/tags/new/', views.tag_create, name='tag_create'),
    path('projects/<uuid:project_pk>/tasks/reorder/', views.task_reorder, name='task_reorder'),
]
