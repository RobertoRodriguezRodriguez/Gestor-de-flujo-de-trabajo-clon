from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView
from . import views

urlpatterns = [
    # Auth
    path('auth/token/', views.RateLimitedTokenObtainPairView.as_view(), name='api_token_obtain'),
    path('auth/token/refresh/', views.RateLimitedTokenRefreshView.as_view(), name='api_token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='api_token_verify'),
    path('auth/token/revoke/', views.TokenRevokeView.as_view(), name='api_token_revoke'),

    # User
    path('me/', views.MeView.as_view(), name='api_me'),

    # Projects
    path('projects/', views.ProjectListCreateView.as_view(), name='api_project_list'),
    path('projects/<uuid:pk>/', views.ProjectRetrieveUpdateView.as_view(), name='api_project_detail'),

    # Tasks
    path('projects/<uuid:project_pk>/tasks/', views.TaskListCreateView.as_view(), name='api_task_list'),
    path('projects/<uuid:project_pk>/tasks/<uuid:pk>/', views.TaskRetrieveUpdateDestroyView.as_view(), name='api_task_detail'),

    # Comments
    path('projects/<uuid:project_pk>/tasks/<uuid:task_pk>/comments/', views.CommentListCreateView.as_view(), name='api_comment_list'),
    path('projects/<uuid:project_pk>/tasks/<uuid:task_pk>/comments/<uuid:pk>/', views.CommentDestroyView.as_view(), name='api_comment_destroy'),
]
