from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from projects.models import Project, ProjectMember
from .models import Task, Tag, Comment, Attachment, TimeLog, TaskTag
from .permissions import can_delete_comment
from projects.permissions import (
    can_create_task, can_edit_task, can_delete_task,
    can_update_task_status, can_log_time, can_upload_attachment,
    can_manage_tags,
)
from shared.decorators import require_project_member, project_permission


def _parse_hm(post, h_field, m_field):
    """Lee campos h + min del POST y devuelve el total en minutos (int), o None si ambos son 0."""
    try:
        h = int(post.get(h_field, 0) or 0)
        m = int(post.get(m_field, 0) or 0)
        total = h * 60 + m
        return total if total > 0 else None
    except (ValueError, TypeError):
        return None


def _notify_status_change(task, project, changed_by, old_status, new_status):
    """Send notifications when a task status changes."""
    from notifications.models import Notification

    # Notify assignee when someone else changes the status
    if task.assignee and task.assignee != changed_by:
        status_label = dict(Task.STATUS_CHOICES).get(new_status, new_status)
        Notification.objects.create(
            user=task.assignee, task=task, project=project,
            type='status_changed',
            message=f'{changed_by.name} cambió el estado de "{task.title}" a {status_label}.',
        )

    # Notify task_responsible when the task they are supervising is completed
    if new_status == 'done' and task.task_responsible and task.task_responsible != changed_by:
        Notification.objects.create(
            user=task.task_responsible, task=task, project=project,
            type='task_completed',
            message=f'La tarea "{task.title}" que supervisabas ha sido completada.',
        )


def _parse_hours(post):
    """Convierte campos estimated_h + estimated_m del POST a horas decimales, o None."""
    try:
        h = int(post.get('estimated_h', 0) or 0)
        m = int(post.get('estimated_m', 0) or 0)
        total = h + m / 60
        return Decimal(str(round(total, 2))) if total > 0 else None
    except (ValueError, TypeError, InvalidOperation):
        return None


@login_required
@project_permission(can_create_task, pk_kwarg='project_pk')
def task_create(request, project_pk, project=None, membership=None):
    if request.method == 'POST':
        parsed_hours = _parse_hours(request.POST) or None
        responsible_id = request.POST.get('task_responsible') or None

        task = Task.objects.create(
            project=project,
            title=request.POST.get('title'),
            description=request.POST.get('description', ''),
            type=request.POST.get('type', 'task'),
            status=request.POST.get('status', 'backlog'),
            priority=request.POST.get('priority', 'medium'),
            start_date=request.POST.get('start_date') or None,
            due_date=request.POST.get('due_date') or None,
            estimated_hours=parsed_hours,
            task_responsible_id=responsible_id,
            hours_requester=request.user if (responsible_id and parsed_hours) else None,
            sprint_id=request.POST.get('sprint') or None,
            parent_task_id=request.POST.get('parent_task') or None,
        )
        assignee_ids = [pk for pk in request.POST.getlist('assignees') if pk]
        if assignee_ids:
            task.assignees.set(assignee_ids)
        for tag_id in request.POST.getlist('tags'):
            TaskTag.objects.get_or_create(task=task, tag_id=tag_id)

        from notifications.models import Notification
        for assignee in task.assignees.exclude(pk=request.user.pk):
            Notification.objects.create(
                user=assignee, task=task, project=project,
                type='task_assigned',
                message=f'Se te asignó la tarea: {task.title}',
            )
        if task.task_responsible and estimated_hours and task.task_responsible != request.user:
            Notification.objects.create(
                user=task.task_responsible, task=task, project=project,
                type='hours_validation_requested',
                message=f'{request.user.name} solicita que valides la estimación de {estimated_hours}h para: {task.title}',
            )
        elif responsible_id and not parsed_hours:
            messages.warning(request, 'Has asignado un responsable sin horas estimadas. El responsable no recibirá notificación hasta que añadas una estimación.')

        messages.success(request, f'Tarea "{task.title}" creada.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'task_id': str(task.id)})
        return redirect('task_detail', project_pk=project_pk, pk=task.pk)

    members = project.members.select_related('user')
    sprints = project.sprints.filter(status__in=['planned', 'active'])
    tags = project.tags.all()
    parent_tasks = project.tasks.filter(parent_task__isnull=True).exclude(type='subtask')

    return render(request, 'tasks/task_form.html', {
        'project': project, 'members': members, 'sprints': sprints,
        'tags': tags, 'parent_tasks': parent_tasks,
        'type_choices': Task.TYPE_CHOICES, 'status_choices': Task.STATUS_CHOICES,
        'priority_choices': Task.PRIORITY_CHOICES, 'title': 'Nueva Tarea',
    })


@login_required
@require_project_member(pk_kwarg='project_pk')
def task_detail(request, project_pk, pk, project=None, membership=None):
    task = get_object_or_404(Task, pk=pk, project=project)
    comments = task.comments.filter(deleted_at__isnull=True).select_related('user').all()
    attachments = task.attachments.select_related('uploaded_by').all()
    time_logs = task.time_logs.select_related('user').all()
    subtasks = task.subtasks.prefetch_related('assignees').all()
    total_logged = task.get_total_logged_minutes()

    estimated_total_min = int(float(task.estimated_hours) * 60) if task.estimated_hours else 0

    return render(request, 'tasks/task_detail.html', {
        'project': project, 'task': task, 'membership': membership,
        'comments': comments, 'attachments': attachments,
        'time_logs': time_logs, 'subtasks': subtasks,
        'total_logged': total_logged,
        'estimated_total_min': estimated_total_min,
        'total_logged_display': f'{total_logged // 60}h {total_logged % 60}m' if total_logged else '0m',
        'status_choices': Task.STATUS_CHOICES,
        'priority_choices': Task.PRIORITY_CHOICES,
        'members': project.members.select_related('user'),
        'sprints': project.sprints.filter(status__in=['planned', 'active']),
    })


@login_required
@project_permission(can_edit_task, pk_kwarg='project_pk')
def task_edit(request, project_pk, pk, project=None, membership=None):
    task = get_object_or_404(Task, pk=pk, project=project)

    if request.method == 'POST':
        old_status = task.status
        old_assignee = task.assignee
        old_responsible_id = task.task_responsible_id

        task.title = request.POST.get('title', task.title)
        task.description = request.POST.get('description', task.description)
        task.type = request.POST.get('type', task.type)
        task.status = request.POST.get('status', task.status)
        task.priority = request.POST.get('priority', task.priority)
        task.start_date = request.POST.get('start_date') or None
        task.due_date = request.POST.get('due_date') or None
        task.sprint_id = request.POST.get('sprint') or None

        new_hours = _parse_hours(request.POST)
        hours_changed = str(new_hours) != str(task.estimated_hours)
        if hours_changed:
            task.hours_validated = False
        task.estimated_hours = new_hours
        new_responsible_id = request.POST.get('task_responsible') or None
        responsible_changed = str(new_responsible_id) != str(old_responsible_id)
        task.task_responsible_id = new_responsible_id
        task.sprint_id = request.POST.get('sprint') or None
        task.assignee_id = request.POST.get('assignee') or None
        task.save()

        task.task_tags.all().delete()
        for tag_id in request.POST.getlist('tags'):
            TaskTag.objects.get_or_create(task=task, tag_id=tag_id)

        from notifications.models import Notification

        # New or changed assignee
        if task.assignee and task.assignee != old_assignee and task.assignee != request.user:
            Notification.objects.create(
                user=task.assignee, task=task, project=project,
                type='task_assigned',
                message=f'Se te asignó la tarea: {task.title}',
            )

        # Hours validation request (new responsible or changed hours)
        should_notify_responsible = (
            task.task_responsible and task.estimated_hours
            and task.task_responsible != request.user
            and (responsible_changed or hours_changed)
        )
        if should_notify_responsible:
            task.hours_requester = request.user
            task.save(update_fields=['hours_requester'])
            Notification.objects.create(
                user=task.task_responsible, task=task, project=project,
                type='hours_validation_requested',
                message=f'{request.user.name} solicita que valides la estimación de {task.estimated_hours}h para: {task.title}',
            )
        elif new_responsible_id and not task.estimated_hours:
            messages.warning(request, 'Has asignado un responsable sin horas estimadas. El responsable no recibirá notificación hasta que añadas una estimación.')

        # Status change notifications
        if task.status != old_status:
            _notify_status_change(task, project, request.user, old_status, task.status)

        messages.success(request, 'Tarea actualizada.')
        return redirect('task_detail', project_pk=project_pk, pk=pk)

    members = project.members.select_related('user')
    sprints = project.sprints.filter(status__in=['planned', 'active'])
    tags = project.tags.all()
    selected_tag_ids = list(task.task_tags.values_list('tag_id', flat=True))
    selected_assignee_ids = list(task.assignees.values_list('id', flat=True))

    est = task.estimated_hours or 0
    est_total_min = round(float(est) * 60)
    est_h, est_m = divmod(est_total_min, 60)
    return render(request, 'tasks/task_form.html', {
        'project': project, 'task': task, 'members': members,
        'sprints': sprints, 'tags': tags, 'selected_tag_ids': selected_tag_ids,
        'selected_assignee_ids': selected_assignee_ids,
        'type_choices': Task.TYPE_CHOICES, 'status_choices': Task.STATUS_CHOICES,
        'priority_choices': Task.PRIORITY_CHOICES, 'title': 'Editar Tarea',
        'est_h': est_h, 'est_m': est_m,
    })


@login_required
@require_POST
@project_permission(can_delete_task, pk_kwarg='project_pk')
def task_delete(request, project_pk, pk, project=None, membership=None):
    task = get_object_or_404(Task, pk=pk, project=project)
    task_title = task.title
    task.delete()
    messages.success(request, f'Tarea "{task_title}" eliminada.')
    return redirect('project_detail', pk=project_pk)


@login_required
@require_POST
@project_permission(can_edit_task, pk_kwarg='project_pk')
def task_update_title(request, project_pk, pk, project=None, membership=None):
    task = get_object_or_404(Task, pk=pk, project=project)
    title = request.POST.get('title', '').strip()
    if not title:
        return JsonResponse({'error': 'El título no puede estar vacío.'}, status=400)
    if len(title) > 300:
        return JsonResponse({'error': 'El título es demasiado largo.'}, status=400)
    task.title = title
    task.save(update_fields=['title', 'updated_at'])
    return JsonResponse({'ok': True, 'title': task.title})


@login_required
@require_POST
@project_permission(can_update_task_status, pk_kwarg='project_pk')
def task_update_status(request, project_pk, pk, project=None, membership=None):
    task = get_object_or_404(Task, pk=pk, project=project)
    new_status = request.POST.get('status')
    if new_status in dict(Task.STATUS_CHOICES) and new_status != task.status:
        old_status = task.status
        task.status = new_status
        task.save()
        _notify_status_change(task, project, request.user, old_status, new_status)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'status': task.status})
    return redirect('task_detail', project_pk=project_pk, pk=pk)


@login_required
@require_project_member(pk_kwarg='project_pk')
def task_list_data(request, project_pk, project=None, membership=None):
    from django.db.models import Case, When, IntegerField, Value, F
    from django.urls import reverse

    SORT_MAP = {
        'key':       'project_sequence',
        'title':     'title',
        'type':      'type',
        'status':    None,
        'priority':  None,
        'assignee':  'assignee__name',
        'due_date':  None,
        'created_at':'created_at',
    }
    sort  = request.GET.get('sort', 'created_at')
    order = request.GET.get('order', 'desc')
    if sort not in SORT_MAP:
        sort = 'created_at'
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page = 1
    per_page = 25

    qs = project.tasks.filter(parent_task__isnull=True).select_related('assignee')

    if sort == 'status':
        expr = Case(
            When(status='backlog',     then=Value(1)),
            When(status='todo',        then=Value(2)),
            When(status='in_progress', then=Value(3)),
            When(status='in_review',   then=Value(4)),
            When(status='done',        then=Value(5)),
            default=Value(0), output_field=IntegerField(),
        )
        qs = qs.order_by(expr.desc() if order == 'desc' else expr)
    elif sort == 'priority':
        expr = Case(
            When(priority='low',      then=Value(1)),
            When(priority='medium',   then=Value(2)),
            When(priority='high',     then=Value(3)),
            When(priority='critical', then=Value(4)),
            default=Value(0), output_field=IntegerField(),
        )
        qs = qs.order_by(expr.desc() if order == 'desc' else expr)
    elif sort == 'due_date':
        f = F('due_date')
        qs = qs.order_by(f.desc(nulls_last=True) if order == 'desc' else f.asc(nulls_last=True))
    else:
        field = SORT_MAP[sort]
        qs = qs.order_by(f'-{field}' if order == 'desc' else field)

    total = qs.count()
    pages = max(1, (total + per_page - 1) // per_page)
    page  = min(page, pages)
    today = timezone.now().date()

    task_list = []
    for t in qs[(page - 1) * per_page: page * per_page]:
        overdue = bool(t.due_date and t.status != 'done' and t.due_date < today)
        task_list.append({
            'pk':               str(t.pk),
            'key':              f'{project.key}-{t.project_sequence}',
            'title':            t.title,
            'type':             t.type,
            'type_display':     t.get_type_display(),
            'status':           t.status,
            'status_display':   t.get_status_display(),
            'priority':         t.priority,
            'priority_display': t.get_priority_display(),
            'assignee_name':    t.assignee.name if t.assignee else None,
            'assignee_initials':t.assignee.get_initials() if t.assignee else None,
            'due_date':         t.due_date.strftime('%d %b %Y') if t.due_date else None,
            'is_overdue':       overdue,
            'url':              reverse('task_detail', args=[project_pk, t.pk]),
        })

    return JsonResponse({
        'tasks':    task_list,
        'total':    total,
        'page':     page,
        'per_page': per_page,
        'pages':    pages,
        'sort':     sort,
        'order':    order,
    })


@login_required
@require_POST
@project_permission(can_update_task_status, pk_kwarg='project_pk')
def task_reorder(request, project_pk, project=None, membership=None):
    import json
    from django.db import transaction

    try:
        data = json.loads(request.body)
        task_id = data['task_id']
        new_status = data['status']
        order = data.get('order', [])
    except (json.JSONDecodeError, KeyError, TypeError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    if new_status not in dict(Task.STATUS_CHOICES):
        return JsonResponse({'error': 'Invalid status'}, status=400)

    task = get_object_or_404(Task, pk=task_id, project=project)

    with transaction.atomic():
        old_status = task.status
        task.status = new_status
        task.save()
        for i, tid in enumerate(order):
            Task.objects.filter(pk=tid, project=project).update(position=i)

    if old_status != new_status:
        _notify_status_change(task, project, request.user, old_status, new_status)

    return JsonResponse({'success': True})


@login_required
@require_POST
@require_project_member(pk_kwarg='project_pk')
def comment_create(request, project_pk, task_pk, project=None, membership=None):
    task = get_object_or_404(Task, pk=task_pk, project=project)
    content = request.POST.get('content', '').strip()
    if content:
        Comment.objects.create(task=task, user=request.user, content=content)
        from notifications.models import Notification
        comment_msg = f'{request.user.name} comentó en: {task.title}'
        notified = {request.user.pk}
        for recipient in (task.assignee, task.task_responsible):
            if recipient and recipient.pk not in notified:
                Notification.objects.create(
                    user=recipient, task=task, project=project,
                    type='comment_added',
                    message=comment_msg,
                )
                notified.add(recipient.pk)
    return redirect('task_detail', project_pk=project_pk, pk=task_pk)


@login_required
@require_POST
@require_project_member(pk_kwarg='project_pk')
def comment_delete(request, project_pk, task_pk, pk, project=None, membership=None):
    comment = get_object_or_404(Comment, pk=pk, task__project=project)
    if not can_delete_comment(request.user, comment):
        messages.error(request, 'Solo puedes eliminar tus propios comentarios.')
        return redirect('task_detail', project_pk=project_pk, pk=task_pk)
    comment.deleted_at = timezone.now()
    comment.save()
    return redirect('task_detail', project_pk=project_pk, pk=task_pk)


@login_required
@require_POST
@project_permission(can_upload_attachment, pk_kwarg='project_pk')
def attachment_upload(request, project_pk, task_pk, project=None, membership=None):
    task = get_object_or_404(Task, pk=task_pk, project=project)
    file = request.FILES.get('file')
    if file:
        if file.size > 10 * 1024 * 1024:
            messages.error(request, 'El archivo no puede superar los 10 MB.')
        else:
            Attachment.objects.create(task=task, uploaded_by=request.user, file=file)
            messages.success(request, 'Archivo adjunto subido.')
    return redirect('task_detail', project_pk=project_pk, pk=task_pk)


@login_required
@require_POST
@project_permission(can_log_time, pk_kwarg='project_pk')
def timelog_create(request, project_pk, task_pk, project=None, membership=None):
    task = get_object_or_404(Task, pk=task_pk, project=project)
    minutes = _parse_hm(request.POST, 'log_h', 'log_m')
    if minutes and minutes > 0:
        TimeLog.objects.create(
            task=task, project=project, user=request.user,
            minutes=minutes,
            note=request.POST.get('note', ''),
            logged_date=request.POST.get('logged_date') or timezone.now().date(),
        )
        h, m = divmod(minutes, 60)
        messages.success(request, f'{h}h {m}min registradas.' if h else f'{m}min registradas.')
    return redirect('task_detail', project_pk=project_pk, pk=task_pk)


@login_required
@require_POST
@require_project_member(pk_kwarg='project_pk')
def task_validate_hours(request, project_pk, pk, project=None, membership=None):
    task = get_object_or_404(Task, pk=pk, project=project)
    if request.user != task.task_responsible:
        messages.error(request, 'Solo el responsable de horas puede validar la estimación.')
        return redirect('task_detail', project_pk=project_pk, pk=pk)

    from notifications.models import Notification
    action = request.POST.get('action')

    # Notificar a asignado y/o solicitante (sin duplicar ni notificar al propio responsable)
    notified = {request.user.pk}
    notify_recipients = []
    for candidate in (task.assignee, task.hours_requester):
        if candidate and candidate.pk not in notified:
            notify_recipients.append(candidate)
            notified.add(candidate.pk)

    if action == 'validate':
        task.hours_validated = True
        task.save(update_fields=['hours_validated'])
        messages.success(request, 'Estimación de horas validada.')
        for recipient in notify_recipients:
            Notification.objects.create(
                user=recipient, task=task, project=project,
                type='hours_validated',
                message=f'{request.user.name} ha aprobado la estimación de {task.estimated_hours}h para: {task.title}',
            )
    elif action == 'reject':
        hours_before = task.estimated_hours
        task.hours_validated = False
        task.estimated_hours = None
        task.hours_requester = None
        task.save(update_fields=['hours_validated', 'estimated_hours', 'hours_requester'])
        messages.info(request, 'Estimación rechazada. El creador puede introducir una nueva.')
        for recipient in notify_recipients:
            Notification.objects.create(
                user=recipient, task=task, project=project,
                type='hours_validated',
                message=f'{request.user.name} ha rechazado la estimación de {hours_before}h para: {task.title}. Por favor, introduce una nueva estimación.',
            )
    return redirect('task_detail', project_pk=project_pk, pk=pk)


@login_required
@project_permission(can_manage_tags, pk_kwarg='project_pk')
def tag_create(request, project_pk, project=None, membership=None):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        color = request.POST.get('color', '#6366f1')
        if name:
            Tag.objects.get_or_create(project=project, name=name, defaults={'color': color})
            messages.success(request, f'Etiqueta "{name}" creada.')
    return redirect('project_detail', pk=project_pk)


@login_required
def my_tasks(request):
    tasks = Task.objects.filter(assignee=request.user).select_related(
        'project', 'sprint'
    ).order_by('due_date', '-priority')
    status_filter = request.GET.get('status', '')
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    return render(request, 'tasks/my_tasks.html', {
        'tasks': tasks,
        'status_choices': Task.STATUS_CHOICES,
        'selected_status': status_filter,
    })
