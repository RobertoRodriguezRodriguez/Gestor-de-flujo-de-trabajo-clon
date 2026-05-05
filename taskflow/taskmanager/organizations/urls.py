from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('organizations/', views.org_list, name='org_list'),
    path('organizations/new/', views.org_create, name='org_create'),
    path('organizations/<uuid:pk>/', views.org_detail, name='org_detail'),
    path('organizations/<uuid:pk>/edit/', views.org_edit, name='org_edit'),
    path('organizations/<uuid:pk>/invite/', views.org_invite, name='org_invite'),
    path('organizations/<uuid:pk>/members/<uuid:member_pk>/role/', views.org_member_update, name='org_member_update'),
    path('organizations/<uuid:pk>/members/<uuid:member_pk>/remove/', views.org_member_remove, name='org_member_remove'),
    path('organizations/<uuid:pk>/hours/', views.org_hours_overview, name='org_hours_overview'),
    path('organizations/<uuid:pk>/hours/export/', views.org_hours_export, name='org_hours_export'),
    path('organizations/<uuid:pk>/hours/monthly/', views.org_hours_monthly, name='org_hours_monthly'),
    path('search/', views.global_search, name='global_search'),
]
