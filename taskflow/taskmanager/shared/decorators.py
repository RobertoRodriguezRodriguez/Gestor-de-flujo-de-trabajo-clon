from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse


def _is_ajax(request) -> bool:
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def require_org_member(pk_kwarg='pk'):
    """
    Resolves the org from URL kwargs and verifies the request user is a member.
    Injects `org` and `org_membership` as keyword arguments into the view.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from organizations.models import Organization, OrganizationUser
            org = get_object_or_404(Organization, pk=kwargs.get(pk_kwarg))
            membership = OrganizationUser.objects.filter(
                organization=org, user=request.user
            ).first()
            if not membership:
                messages.error(request, 'No tienes acceso a esta organización.')
                return redirect('dashboard')
            kwargs['org'] = org
            kwargs['org_membership'] = membership
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def org_permission(perm_func, pk_kwarg='pk'):
    """
    Like require_org_member but also checks perm_func(membership).
    Redirects to org_detail when the user lacks the required permission.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from organizations.models import Organization, OrganizationUser
            org_pk = kwargs.get(pk_kwarg)
            org = get_object_or_404(Organization, pk=org_pk)
            membership = OrganizationUser.objects.filter(
                organization=org, user=request.user
            ).first()
            if not membership:
                messages.error(request, 'No tienes acceso a esta organización.')
                return redirect('dashboard')
            if not perm_func(membership):
                messages.error(request, 'No tienes permisos para realizar esta acción.')
                return redirect('org_detail', pk=org_pk)
            kwargs['org'] = org
            kwargs['org_membership'] = membership
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_project_member(pk_kwarg='pk'):
    """
    Resolves the project from URL kwargs and verifies the request user is a member.
    Injects `project` and `membership` as keyword arguments into the view.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from projects.models import Project, ProjectMember
            project = get_object_or_404(Project, pk=kwargs.get(pk_kwarg))
            membership = ProjectMember.objects.filter(
                project=project, user=request.user
            ).first()
            if not membership:
                if _is_ajax(request):
                    return JsonResponse({'error': 'Sin acceso al proyecto'}, status=403)
                messages.error(request, 'No tienes acceso a este proyecto.')
                return redirect('dashboard')
            kwargs['project'] = project
            kwargs['membership'] = membership
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def project_permission(perm_func, pk_kwarg='pk'):
    """
    Like require_project_member but also checks perm_func(membership).
    Returns a JSON 403 for AJAX requests; redirects to project_detail otherwise.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from projects.models import Project, ProjectMember
            project_pk = kwargs.get(pk_kwarg)
            project = get_object_or_404(Project, pk=project_pk)
            membership = ProjectMember.objects.filter(
                project=project, user=request.user
            ).first()
            if not membership:
                if _is_ajax(request):
                    return JsonResponse({'error': 'Sin acceso al proyecto'}, status=403)
                messages.error(request, 'No tienes acceso a este proyecto.')
                return redirect('dashboard')
            if not perm_func(membership):
                if _is_ajax(request):
                    return JsonResponse({'error': 'Sin permisos'}, status=403)
                messages.error(request, 'No tienes permisos para realizar esta acción.')
                return redirect('project_detail', pk=project_pk)
            kwargs['project'] = project
            kwargs['membership'] = membership
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
