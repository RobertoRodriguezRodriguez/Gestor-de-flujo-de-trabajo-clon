from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from projects.models import Project, ProjectMember
from tasks.models import Task, Comment
from projects.permissions import (
    can_create_task, can_edit_task, can_delete_task, can_manage_members,
    can_edit_project,
)
from .serializers import (
    UserSerializer, ProjectSerializer, TaskSerializer, CommentSerializer,
)

_RATELIMITED_RESPONSE = Response(
    {'error': 'Demasiadas peticiones. Inténtalo más tarde.'},
    status=status.HTTP_429_TOO_MANY_REQUESTS,
)


@method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=False), name='post')
class RateLimitedTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        if getattr(request, 'limited', False):
            return _RATELIMITED_RESPONSE
        return super().post(request, *args, **kwargs)


@method_decorator(ratelimit(key='ip', rate='20/m', method='POST', block=False), name='post')
class RateLimitedTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        if getattr(request, 'limited', False):
            return _RATELIMITED_RESPONSE
        return super().post(request, *args, **kwargs)

User = get_user_model()


class TokenRevokeView(APIView):
    """Blacklist a refresh token (logout)."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'refresh token requerido'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({'error': 'Token inválido o ya revocado'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user


class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Project.objects.filter(
            members__user=self.request.user, deleted_at__isnull=True
        ).select_related('owner').distinct()

    def perform_create(self, serializer):
        from organizations.models import Organization, OrganizationUser
        org_id = self.request.data.get('organization')
        org = Organization.objects.get(pk=org_id)
        if not OrganizationUser.objects.filter(organization=org, user=self.request.user).exists():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('No eres miembro de esa organización.')
        project = serializer.save(owner=self.request.user, organization=org)
        ProjectMember.objects.create(project=project, user=self.request.user, role='owner')


class ProjectRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Project.objects.filter(
            members__user=self.request.user, deleted_at__isnull=True
        )

    def update(self, request, *args, **kwargs):
        project = self.get_object()
        membership = project.members.filter(user=request.user).first()
        if not can_edit_project(membership):
            return Response({'error': 'Sin permisos'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)


class _ProjectTaskMixin:
    """Resolve project + membership from URL kwarg project_pk."""
    permission_classes = (permissions.IsAuthenticated,)

    def _get_project_and_membership(self):
        project = Project.objects.filter(
            pk=self.kwargs['project_pk'], deleted_at__isnull=True,
            members__user=self.request.user,
        ).first()
        if not project:
            from rest_framework.exceptions import NotFound
            raise NotFound()
        membership = project.members.filter(user=self.request.user).first()
        return project, membership


class TaskListCreateView(_ProjectTaskMixin, generics.ListCreateAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        project, _ = self._get_project_and_membership()
        qs = project.tasks.select_related('assignee').prefetch_related('tags')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied
        project, membership = self._get_project_and_membership()
        if not can_create_task(membership):
            raise PermissionDenied('Sin permisos para crear tareas.')
        serializer.save(project=project)


class TaskRetrieveUpdateDestroyView(_ProjectTaskMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        project, _ = self._get_project_and_membership()
        return project.tasks.all()

    def update(self, request, *args, **kwargs):
        from rest_framework.exceptions import PermissionDenied
        _, membership = self._get_project_and_membership()
        if not can_edit_task(membership):
            raise PermissionDenied('Sin permisos para editar tareas.')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        from rest_framework.exceptions import PermissionDenied
        _, membership = self._get_project_and_membership()
        if not can_delete_task(membership):
            raise PermissionDenied('Sin permisos para eliminar tareas.')
        return super().destroy(request, *args, **kwargs)


class CommentListCreateView(_ProjectTaskMixin, generics.ListCreateAPIView):
    serializer_class = CommentSerializer

    def _get_task(self):
        project, _ = self._get_project_and_membership()
        from django.shortcuts import get_object_or_404
        from tasks.models import Task
        return get_object_or_404(Task, pk=self.kwargs['task_pk'], project=project)

    def get_queryset(self):
        return self._get_task().comments.filter(deleted_at__isnull=True).select_related('user')

    def perform_create(self, serializer):
        serializer.save(task=self._get_task(), user=self.request.user)


class CommentDestroyView(_ProjectTaskMixin, generics.DestroyAPIView):
    serializer_class = CommentSerializer

    def get_queryset(self):
        project, _ = self._get_project_and_membership()
        return Comment.objects.filter(task__project=project)

    def destroy(self, request, *args, **kwargs):
        from rest_framework.exceptions import PermissionDenied
        from django.utils import timezone
        comment = self.get_object()
        if comment.user != request.user:
            raise PermissionDenied('Solo puedes eliminar tus propios comentarios.')
        comment.deleted_at = timezone.now()
        comment.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
