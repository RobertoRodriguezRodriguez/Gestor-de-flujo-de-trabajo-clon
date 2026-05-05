from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
import markdown
from io import BytesIO
try:
    from xhtml2pdf import pisa
except ImportError:
    pisa = None
from .ai_summary_service import generate_executive_summary
from .models import Project, ProjectMember, Sprint
from .permissions import (
    can_edit_project, can_delete_project,
    can_manage_members, can_manage_sprints,
    can_manage_tags,
)
from shared.decorators import require_project_member, project_permission
from organizations.models import Organization, OrganizationUser

User = get_user_model()


@login_required
def project_create(request):
    user_orgs = OrganizationUser.objects.filter(user=request.user).select_related('organization')

    if request.method == 'POST':
        org_id = request.POST.get('organization')
        name = request.POST.get('name', '').strip()
        key = request.POST.get('key', '').strip().upper()
        description = request.POST.get('description', '')
        status = request.POST.get('status', 'planning')
        priority = request.POST.get('priority', 'medium')
        start_date = request.POST.get('start_date') or None
        due_date = request.POST.get('due_date') or None

        if not all([org_id, name, key]):
            messages.error(request, 'Organización, nombre y clave son obligatorios.')
        else:
            org = get_object_or_404(Organization, pk=org_id)
            if not OrganizationUser.objects.filter(organization=org, user=request.user).exists():
                messages.error(request, 'No eres miembro de esa organización.')
            elif Project.objects.filter(organization=org, key=key).exists():
                messages.error(request, f'La clave "{key}" ya existe en esta organización.')
            else:
                from django.db import IntegrityError
                try:
                    project = Project.objects.create(
                        organization=org, owner=request.user, key=key,
                        name=name, description=description, status=status,
                        priority=priority, start_date=start_date, due_date=due_date,
                        hour_budget=request.POST.get('hour_budget') or None,
                    )
                    ProjectMember.objects.create(project=project, user=request.user, role='owner')
                    messages.success(request, f'Proyecto "{project.name}" creado.')
                except IntegrityError:
                    messages.error(request, f'La clave "{key}" ya existe en esta organización.')
                return redirect('project_detail', pk=project.pk)

    return render(request, 'projects/project_form.html', {
        'title': 'Nuevo Proyecto',
        'user_orgs': user_orgs,
        'status_choices': Project.STATUS_CHOICES,
        'priority_choices': Project.PRIORITY_CHOICES,
    })


def _sprint_burndown(sprint):
    """Return burndown data dict for a sprint, or None if insufficient data."""
    from datetime import timedelta
    from django.utils import timezone

    if not sprint.start_date or not sprint.end_date:
        return None

    tasks = list(sprint.tasks.values('id', 'completed_at'))
    total = len(tasks)
    if total == 0:
        return None

    start = sprint.start_date.date()
    end = sprint.end_date.date()
    if end <= start:
        return None

    today = timezone.now().date()
    cutoff = min(end, today)

    # Day-by-day actual remaining (from sprint start to today/end)
    actual = []
    d = start
    while d <= cutoff:
        completed = sum(
            1 for t in tasks
            if t['completed_at'] and t['completed_at'].date() <= d
        )
        actual.append([d.isoformat(), total - completed])
        d += timedelta(days=1)

    completed_now = sum(
        1 for t in tasks
        if t['completed_at'] and t['completed_at'].date() <= cutoff
    )
    remaining = total - completed_now

    # Pace: compare actual remaining vs ideal remaining at today
    total_days = (end - start).days
    days_elapsed = min((today - start).days, total_days)
    ideal_now = total * (1 - days_elapsed / total_days)
    diff = remaining - ideal_now
    if sprint.status == 'completed':
        pace = 'done'
    elif diff < -0.5:
        pace = 'ahead'
    elif diff > 0.5:
        pace = 'behind'
    else:
        pace = 'on_track'

    return {
        'total': total,
        'completed': completed_now,
        'remaining': remaining,
        'pace': pace,
        'start': start.isoformat(),
        'end': end.isoformat(),
        'today': today.isoformat(),
        'actual': actual,
    }


def _velocity_data(sprints):
    """Return list of velocity entries for completed/active sprints, oldest-first, max 8."""
    from django.utils import timezone

    eligible = sorted(
        [s for s in sprints if s.status in ('completed', 'active')],
        key=lambda s: s.start_date or timezone.now(),
    )
    eligible = eligible[-8:]  # keep most recent 8

    result = []
    for sprint in eligible:
        tasks = list(sprint.tasks.values('status', 'estimated_hours'))
        done = [t for t in tasks if t['status'] == 'done']

        hours_done = sum(float(t['estimated_hours']) for t in done if t['estimated_hours'])
        hours_total = sum(float(t['estimated_hours']) for t in tasks if t['estimated_hours'])

        label = sprint.name if len(sprint.name) <= 12 else sprint.name[:11] + '…'

        result.append({
            'name': sprint.name,
            'label': label,
            'status': sprint.status,
            'tasks_done': len(done),
            'tasks_total': len(tasks),
            'hours_done': round(hours_done, 1),
            'hours_total': round(hours_total, 1),
        })

    return result


@login_required
@require_project_member()
def project_detail(request, pk, project=None, membership=None):
    import json
    sprints = project.sprints.all().order_by('-start_date')
    members = project.members.select_related('user').all()
    tags = project.tags.all()
    stats = project.get_task_stats()
    hour_stats = project.get_hour_stats()

    from tasks.models import Task, TimeLog
    from django.db.models import Sum

    tasks_by_status = {}
    for status_key, status_label in Task.STATUS_CHOICES:
        tasks_by_status[status_key] = {
            'label': status_label,
            'tasks': project.tasks.filter(status=status_key, parent_task__isnull=True)
                          .select_related('assignee', 'sprint').prefetch_related('tags').order_by('position'),
        }

    hours_by_task = [
        {
            'task__id': r['task__id'],
            'task__title': r['task__title'],
            'task__project_sequence': r['task__project_sequence'],
            'task__status': r['task__status'],
            'task__estimated_hours': round(r['task__estimated_min'] / 60, 2) if r['task__estimated_min'] else None,
            'logged': round(r['logged_min'] / 60, 2),
        }
        for r in TimeLog.objects
        .filter(project=project)
        .values('task__id', 'task__title', 'task__project_sequence', 'task__status', 'task__estimated_min')
        .annotate(logged_min=Sum('minutes'))
        .order_by('-logged_min')
    ]

    hours_by_member = [
        {**r, 'logged': round(r['logged_min'] / 60, 2)}
        for r in TimeLog.objects
        .filter(project=project)
        .values('user__id', 'user__name', 'user__avatar')
        .annotate(logged_min=Sum('minutes'))
        .order_by('-logged_min')
    ]

    from django.db.models import Count

    assignee_rows = list(
        project.tasks
        .values('assignee__id', 'assignee__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    assignee_dist = [
        {
            'name': r['assignee__name'] or 'Sin asignar',
            'id': str(r['assignee__id']) if r['assignee__id'] else None,
            'count': r['count'],
        }
        for r in assignee_rows
    ]

    burndown_data = {}
    for sprint in sprints:
        bd = _sprint_burndown(sprint)
        if bd:
            burndown_data[str(sprint.pk)] = bd

    velocity_data = _velocity_data(list(sprints))

    return render(request, 'projects/project_detail.html', {
        'project': project,
        'membership': membership,
        'sprints': sprints,
        'members': members,
        'tags': tags,
        'stats': stats,
        'hour_stats': hour_stats,
        'hours_by_task': hours_by_task,
        'hours_by_member': hours_by_member,
        'tasks_by_status': tasks_by_status,
        'active_sprint': sprints.filter(status='active').first(),
        'burndown_json': json.dumps(burndown_data),
        'velocity_json': json.dumps(velocity_data),
        'assignee_dist_json': json.dumps(assignee_dist),
    })


@login_required
@project_permission(can_edit_project)
def project_edit(request, pk, project=None, membership=None):
    if request.method == 'POST':
        project.name = request.POST.get('name', project.name)
        project.description = request.POST.get('description', project.description)
        project.status = request.POST.get('status', project.status)
        project.priority = request.POST.get('priority', project.priority)
        project.start_date = request.POST.get('start_date') or None
        project.due_date = request.POST.get('due_date') or None
        project.hour_budget = request.POST.get('hour_budget') or None
        project.save()
        messages.success(request, 'Proyecto actualizado.')
        return redirect('project_detail', pk=pk)

    return render(request, 'projects/project_form.html', {
        'title': 'Editar Proyecto',
        'project': project,
        'status_choices': Project.STATUS_CHOICES,
        'priority_choices': Project.PRIORITY_CHOICES,
    })


@login_required
@project_permission(can_delete_project)
def project_delete(request, pk, project=None, membership=None):
    if request.method == 'POST':
        project.soft_delete()
        messages.success(request, f'Proyecto "{project.name}" eliminado.')
        return redirect('dashboard')
    return render(request, 'projects/project_confirm_delete.html', {'project': project})


@login_required
@project_permission(can_manage_members)
def project_add_member(request, pk, project=None, membership=None):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'developer')
        try:
            user = User.objects.get(email=email)
            _, created = ProjectMember.objects.get_or_create(
                project=project, user=user, defaults={'role': role}
            )
            if created:
                messages.success(request, f'{user.name} añadido al proyecto.')
                if user != request.user:
                    from notifications.models import Notification
                    Notification.objects.create(
                        user=user,
                        project=project,
                        type='project_added',
                        message=f'{request.user.name} te ha añadido al proyecto "{project.name}".',
                    )
            else:
                messages.warning(request, f'{user.name} ya es miembro.')
        except User.DoesNotExist:
            messages.error(request, 'Usuario no encontrado.')
    return redirect('project_detail', pk=pk)


@login_required
@project_permission(can_manage_members)
def project_member_update(request, pk, member_pk, project=None, membership=None):
    member = get_object_or_404(ProjectMember, pk=member_pk, project=project)
    if request.method == 'POST':
        role = request.POST.get('role')
        if role in ('owner', 'manager', 'developer', 'viewer'):
            member.role = role
            member.save()
            messages.success(request, f'Rol de {member.user.name} actualizado.')
    return redirect('project_detail', pk=pk)


@login_required
@project_permission(can_manage_members)
def project_member_remove(request, pk, member_pk, project=None, membership=None):
    member = get_object_or_404(ProjectMember, pk=member_pk, project=project)
    if request.method == 'POST' and member.user != request.user:
        name = member.user.name
        member.delete()
        messages.success(request, f'{name} eliminado del proyecto.')
    return redirect('project_detail', pk=pk)


@login_required
@project_permission(can_manage_members, pk_kwarg='pk')
def member_hour_history(request, pk, user_pk, project=None, membership=None):
    from tasks.models import TimeLog
    from django.db.models import Sum

    target_user = get_object_or_404(User, pk=user_pk)
    if not ProjectMember.objects.filter(project=project, user=target_user).exists():
        messages.error(request, 'Este usuario no es miembro del proyecto.')
        return redirect('project_detail', pk=pk)

    logs = (
        TimeLog.objects
        .filter(project=project, user=target_user)
        .select_related('task')
        .order_by('-logged_date', '-task__project_sequence')
    )

    total_min = logs.aggregate(total=Sum('minutes'))['total'] or 0
    total_hours = round(total_min / 60, 2)

    by_task = [
        {**r, 'total': round(r['total_min'] / 60, 2)}
        for r in TimeLog.objects
        .filter(project=project, user=target_user)
        .values('task__id', 'task__title', 'task__project_sequence', 'task__status')
        .annotate(total_min=Sum('minutes'))
        .order_by('-total_min')
    ]

    return render(request, 'projects/member_hour_history.html', {
        'project': project,
        'membership': membership,
        'target_user': target_user,
        'logs': logs,
        'by_task': by_task,
        'total_hours': total_hours,
    })


@login_required
@project_permission(can_manage_sprints)
def sprint_create(request, pk, project=None, membership=None):
    if request.method == 'POST':
        Sprint.objects.create(
            project=project,
            name=request.POST.get('name'),
            goal=request.POST.get('goal', ''),
            status=request.POST.get('status', 'planned'),
            start_date=request.POST.get('start_date') or None,
            end_date=request.POST.get('end_date') or None,
        )
        messages.success(request, 'Sprint creado.')
    return redirect('project_detail', pk=pk)


@login_required
@project_permission(can_manage_sprints)
def sprint_update(request, pk, sprint_pk, project=None, membership=None):
    sprint = get_object_or_404(Sprint, pk=sprint_pk, project=project)
    if request.method == 'POST':
        sprint.name = request.POST.get('name', sprint.name)
        sprint.goal = request.POST.get('goal', sprint.goal)
        sprint.status = request.POST.get('status', sprint.status)
        sprint.start_date = request.POST.get('start_date') or sprint.start_date
        sprint.end_date = request.POST.get('end_date') or sprint.end_date
        sprint.save()
        messages.success(request, 'Sprint actualizado.')
    return redirect('project_detail', pk=pk)


@login_required
@require_project_member()
def project_roadmap(request, pk, project=None, membership=None):
    import json
    from tasks.models import Task

    tasks_qs = project.tasks.select_related('assignee', 'parent_task', 'sprint').filter(
        type__in=('task', 'story', 'epic', 'bug')
    )
    sprints_qs = project.sprints.all().order_by('start_date')

    STATUS_COLORS = {
        'backlog': '#6b7280',
        'todo': '#3b82f6',
        'in_progress': '#f59e0b',
        'in_review': '#8b5cf6',
        'done': '#22c55e',
    }

    tasks_data = []
    for t in tasks_qs:
        tasks_data.append({
            'id': str(t.pk),
            'key': f'{project.key}-{t.project_sequence}',
            'title': t.title,
            'status': t.status,
            'color': STATUS_COLORS.get(t.status, '#6b7280'),
            'start': t.start_date.isoformat() if t.start_date else None,
            'end': t.due_date.isoformat() if t.due_date else None,
            'parent_id': str(t.parent_task_id) if t.parent_task_id else None,
            'assignee': t.assignee.get_initials() if t.assignee else None,
            'sprint_id': str(t.sprint_id) if t.sprint_id else None,
            'url': f'/projects/{project.pk}/tasks/{t.pk}/',  # matches task_detail URL pattern

        })

    sprints_data = []
    for s in sprints_qs:
        sprints_data.append({
            'id': str(s.pk),
            'name': s.name,
            'start': s.start_date.date().isoformat() if s.start_date else None,
            'end': s.end_date.date().isoformat() if s.end_date else None,
            'status': s.status,
        })

    return render(request, 'projects/project_roadmap.html', {
        'project': project,
        'membership': membership,
        'tasks_json': json.dumps(tasks_data),
        'sprints_json': json.dumps(sprints_data),
    })


@login_required
def project_create_ai(request):
    """AJAX endpoint: recibe descripción en lenguaje natural y devuelve JSON estructurado."""
    if not request.user.is_premium:
        return JsonResponse({'error': 'Esta función es exclusiva para usuarios Premium.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)

    import json as _json
    try:
        body = _json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Datos inválidos.'}, status=400)

    description = body.get('description', '').strip()
    if not description:
        return JsonResponse({'error': 'La descripción no puede estar vacía.'}, status=400)

    if len(description) > 5000:
        return JsonResponse({'error': 'La descripción es demasiado larga (máx. 5000 caracteres).'}, status=400)

    from .ai_service import parse_project_from_natural_language
    result = parse_project_from_natural_language(description)

    if 'error' in result:
        return JsonResponse({'error': result['error']}, status=422)

    return JsonResponse({'data': result})


@login_required
def project_create_ai_confirm(request):
    """Crea el proyecto y tareas a partir de los datos confirmados por el usuario."""
    if not request.user.is_premium:
        return JsonResponse({'error': 'Esta función es exclusiva para usuarios Premium.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)

    import json as _json
    from django.db import transaction
    from tasks.models import Task

    try:
        body = _json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Datos inválidos.'}, status=400)

    org_id = body.get('organization')
    if not org_id:
        return JsonResponse({'error': 'Debes seleccionar una organización.'}, status=400)

    org = get_object_or_404(Organization, pk=org_id)
    if not OrganizationUser.objects.filter(organization=org, user=request.user).exists():
        return JsonResponse({'error': 'No eres miembro de esa organización.'}, status=403)

    name = body.get('name', '').strip()
    key = body.get('key', '').strip().upper()
    if not name or not key:
        return JsonResponse({'error': 'Nombre y clave son obligatorios.'}, status=400)

    if Project.objects.filter(organization=org, key=key).exists():
        return JsonResponse({'error': f'La clave "{key}" ya existe en esta organización.'}, status=409)

    try:
        with transaction.atomic():
            project = Project.objects.create(
                organization=org,
                owner=request.user,
                key=key[:10],
                name=name[:200],
                description=body.get('description', ''),
                status=body.get('status', 'planning'),
                priority=body.get('priority', 'medium'),
                start_date=body.get('start_date') or None,
                due_date=body.get('due_date') or None,
                hour_budget=body.get('hour_budget') or None,
            )
            ProjectMember.objects.create(project=project, user=request.user, role='owner')

            # Crear tareas sugeridas
            tasks_data = body.get('tasks', [])
            for i, task_data in enumerate(tasks_data):
                if not task_data.get('title'):
                    continue
                Task.objects.create(
                    project=project,
                    title=task_data['title'][:300],
                    type=task_data.get('type', 'task'),
                    priority=task_data.get('priority', 'medium'),
                    description=task_data.get('description', ''),
                    estimated_hours=task_data.get('estimated_hours') or None,
                    status='backlog',
                    position=i,
                )

        return JsonResponse({
            'success': True,
            'redirect': f'/projects/{project.pk}/',
            'project_name': project.name,
        })

    except Exception as e:
        return JsonResponse({'error': f'Error al crear el proyecto: {str(e)}'}, status=500)


@login_required
@require_project_member()
def project_executive_summary_pdf(request, pk, project, membership):
    """Genera un PDF con el resumen ejecutivo del proyecto vía IA."""
    if not request.user.is_premium:
        messages.error(request, "Esta función es exclusiva para usuarios Premium.")
        return redirect('project_detail', pk=pk)
    
    # Obtener todas las tareas
    tasks = project.tasks.select_related('assignee').all()
    
    # Generar Markdown con Gemini
    markdown_text = generate_executive_summary(project, tasks)
    
    # Convertir Markdown a HTML
    html_content = markdown.markdown(markdown_text, extensions=['extra', 'nl2br'])
    
    # Renderizar plantilla Django con el HTML
    context = {
        'project': project,
        'summary_html': html_content,
        'date_generated': timezone.now()
    }
    rendered_html = render_to_string('projects/pdf_summary.html', context, request=request)
    
    # Generar PDF si xhtml2pdf está disponible, si no devolver HTML imprimible
    if pisa is not None:
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(rendered_html.encode("utf-8")), result)
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"Resumen_Ejecutivo_{project.key}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        messages.error(request, "Error al generar el PDF.")
        return redirect('project_detail', pk=pk)

    # Fallback: HTML imprimible (Ctrl+P → Guardar como PDF en el navegador)
    response = HttpResponse(rendered_html, content_type='text/html; charset=utf-8')
    return response

@login_required
@require_project_member()
def project_board_chat(request, pk, project=None, membership=None):
    if not request.user.is_premium:
        return JsonResponse({'error': 'Esta función es exclusiva para usuarios Premium.'}, status=403)
        
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)
        
    import json as _json
    from .ai_board_service import chat_with_board
    
    try:
        body = _json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Datos inválidos.'}, status=400)
        
    message = body.get('message', '').strip()
    if not message:
        return JsonResponse({'error': 'El mensaje no puede estar vacío.'}, status=400)
        
    # Construir board_data
    tasks = project.tasks.select_related('assignee').all()
    members = project.members.select_related('user').all()
    
    board_data = {
        'project_name': project.name,
        'members': [{'id': str(m.user.pk), 'name': m.user.name, 'role': m.role} for m in members],
        'tasks': [
            {
                'id': str(t.pk),
                'title': t.title,
                'status': t.status,
                'priority': t.priority,
                'type': t.type,
                'assignee_id': str(t.assignee.pk) if t.assignee else None,
                'assignee_name': t.assignee.name if t.assignee else None,
            } for t in tasks
        ]
    }
    
    result = chat_with_board(message, board_data)
    if 'error' in result:
        return JsonResponse({'error': result['error']}, status=422)
        
    return JsonResponse(result)

@login_required
@require_project_member()
def project_board_chat_apply(request, pk, project=None, membership=None):
    if not request.user.is_premium:
        return JsonResponse({'error': 'Esta función es exclusiva para usuarios Premium.'}, status=403)
        
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)
        
    import json as _json
    from django.db import transaction
    from tasks.models import Task
    
    try:
        body = _json.loads(request.body)
        actions = body.get('actions', [])
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Datos inválidos.'}, status=400)
        
    from projects.models import ProjectMember as _PM
    members_by_user_id = {
        str(m.user_id): m.user
        for m in project.members.select_related('user').all()
    }

    applied_count = 0
    try:
        with transaction.atomic():
            for action in actions:
                action_type = action.get('action')
                if action_type == 'update_status':
                    task_id = action.get('task_id')
                    new_status = action.get('new_status')
                    if task_id and new_status:
                        Task.objects.filter(pk=task_id, project=project).update(status=new_status)
                        applied_count += 1
                elif action_type == 'edit_task':
                    task_id = action.get('task_id')
                    if task_id:
                        try:
                            task = Task.objects.get(pk=task_id, project=project)
                            if 'title' in action and action['title']:
                                task.title = action['title']
                            if 'priority' in action and action['priority']:
                                task.priority = action['priority']
                            if 'description' in action and action['description'] is not None:
                                task.description = action['description']
                            if 'assignee_id' in action:
                                assignee_id = str(action['assignee_id']) if action['assignee_id'] else None
                                task.assignee = members_by_user_id.get(assignee_id) if assignee_id else None
                            task.save()
                            applied_count += 1
                        except Task.DoesNotExist:
                            pass
                elif action_type == 'create_task':
                    title = action.get('title')
                    if title:
                        assignee_id = str(action['assignee_id']) if action.get('assignee_id') else None
                        assignee = members_by_user_id.get(assignee_id) if assignee_id else None

                        parent = None
                        if action.get('parent_id'):
                            try:
                                parent = Task.objects.get(pk=action['parent_id'], project=project)
                            except Task.DoesNotExist:
                                pass

                        max_pos = project.tasks.filter(status=action.get('status', 'todo')).count()
                        Task.objects.create(
                            project=project,
                            title=title,
                            type=action.get('type', 'task'),
                            status=action.get('status', 'todo'),
                            parent_task=parent,
                            assignee=assignee,
                            position=max_pos
                        )
                        applied_count += 1
                        
        return JsonResponse({'success': True, 'applied_count': applied_count})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
