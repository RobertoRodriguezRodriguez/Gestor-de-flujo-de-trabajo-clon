import re
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q, Sum
from django.http import JsonResponse
from .models import Organization, OrganizationUser
from .permissions import can_manage_members, can_assign_role, is_last_owner
from shared.decorators import require_org_member, org_permission
from projects.models import Project

User = get_user_model()


@login_required
def dashboard(request):
    query = request.GET.get('q', '').strip()
    
    user_orgs = OrganizationUser.objects.filter(user=request.user).select_related('organization')
    user_projects = Project.objects.filter(
        members__user=request.user, deleted_at__isnull=True
    ).select_related('organization', 'owner').distinct()
    
    from tasks.models import Task
    from django.db.models import Q
    from django.utils import timezone
    
    if query:
        search_orgs = user_orgs.filter(organization__name__icontains=query)
        search_projects = user_projects.filter(
            Q(name__icontains=query) | 
            Q(key__icontains=query) | 
            Q(description__icontains=query)
        )
        search_tasks = Task.objects.filter(
            project__members__user=request.user,
            project__deleted_at__isnull=True
        ).filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(assignee__name__icontains=query)
        ).select_related('project', 'assignee').distinct()[:20]
        
        context = {
            'query': query,
            'search_orgs': search_orgs,
            'search_projects': search_projects,
            'search_tasks': search_tasks,
        }
    else:
        user_projects = user_projects[:6]
        my_tasks = Task.objects.filter(assignee=request.user).exclude(status='done')
        overdue_tasks = my_tasks.filter(due_date__lt=timezone.now().date())
    
        context = {
            'query': query,
            'user_orgs': user_orgs,
            'user_projects': user_projects,
            'my_tasks_count': my_tasks.count(),
            'overdue_count': overdue_tasks.count(),
        }
        
    return render(request, 'organizations/dashboard.html', context)


@login_required
def org_list(request):
    memberships = OrganizationUser.objects.filter(user=request.user).select_related('organization')
    return render(request, 'organizations/org_list.html', {'memberships': memberships})


@login_required
def org_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'El nombre es obligatorio.')
        else:
            org = Organization.objects.create(
                name=name,
                logo=request.FILES.get('logo'),
                crm_company_id=request.POST.get('crm_company_id', ''),
            )
            OrganizationUser.objects.create(organization=org, user=request.user, role='owner')
            messages.success(request, f'Organización "{org.name}" creada.')
            return redirect('org_detail', pk=org.pk)
    return render(request, 'organizations/org_form.html', {'title': 'Nueva Organización'})


@login_required
@require_org_member()
def org_detail(request, pk, org=None, org_membership=None):
    members = org.get_active_members()
    projects = Project.objects.filter(organization=org, deleted_at__isnull=True).select_related('owner')
    return render(request, 'organizations/org_detail.html', {
        'org': org,
        'membership': org_membership,
        'members': members,
        'projects': projects,
    })


@login_required
@org_permission(can_manage_members)
def org_invite(request, pk, org=None, org_membership=None):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'member')
        try:
            user = User.objects.get(email=email)
            _, created = OrganizationUser.objects.get_or_create(
                organization=org, user=user,
                defaults={'role': role}
            )
            if created:
                messages.success(request, f'{user.name} añadido/a a la organización.')
                if user != request.user:
                    from notifications.models import Notification
                    Notification.objects.create(
                        user=user,
                        type='org_added',
                        message=f'{request.user.name} te ha añadido a la organización "{org.name}".',
                    )
            else:
                messages.warning(request, f'{user.name} ya es miembro.')
        except User.DoesNotExist:
            messages.error(request, f'No se encontró usuario con email {email}.')
    return redirect('org_detail', pk=pk)


@login_required
@org_permission(can_manage_members)
def org_member_remove(request, pk, member_pk, org=None, org_membership=None):
    member = get_object_or_404(OrganizationUser, pk=member_pk, organization=org)
    if request.method == 'POST' and member.user != request.user:
        if member.role == 'owner' and is_last_owner(org):
            messages.error(request, 'No puedes eliminar al único propietario de la organización.')
            return redirect('org_detail', pk=pk)
        name = member.user.name
        member.delete()
        messages.success(request, f'{name} eliminado de la organización.')
    return redirect('org_detail', pk=pk)


@login_required
@org_permission(can_manage_members)
def org_member_update(request, pk, member_pk, org=None, org_membership=None):
    member = get_object_or_404(OrganizationUser, pk=member_pk, organization=org)
    if request.method == 'POST':
        role = request.POST.get('role')
        if role in ('member', 'admin', 'owner'):
            if not can_assign_role(org_membership, role):
                messages.error(request, 'Solo el propietario puede asignar el rol de propietario.')
                return redirect('org_detail', pk=pk)
            member.role = role
            member.save()
            messages.success(request, f'Rol de {member.user.name} actualizado.')
    return redirect('org_detail', pk=pk)


@login_required
@org_permission(can_manage_members)
def org_edit(request, pk, org=None, org_membership=None):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'El nombre es obligatorio.')
        else:
            org.name = name
            org.crm_company_id = request.POST.get('crm_company_id', '')
            if 'logo' in request.FILES:
                org.logo = request.FILES['logo']
            org.save()
            messages.success(request, f'Organización "{org.name}" actualizada.')
            return redirect('org_detail', pk=org.pk)
    return render(request, 'organizations/org_form.html', {'title': 'Editar Organización', 'org': org})


def _can_view_org_hours(membership):
    return membership is not None and membership.role in ('owner', 'admin')


@login_required
@org_permission(_can_view_org_hours)
def org_hours_overview(request, pk, org=None, org_membership=None):
    from tasks.models import TimeLog

    projects = Project.objects.filter(
        organization=org, deleted_at__isnull=True
    ).prefetch_related('time_logs')

    per_project = []
    total_budget = 0
    total_consumed = 0
    for project in projects:
        consumed_min = project.time_logs.aggregate(total=Sum('minutes'))['total'] or 0
        consumed = round(consumed_min / 60, 2)
        budget = project.hour_budget
        if budget:
            total_budget += float(budget)
        total_consumed += consumed
        remaining = float(budget) - consumed if budget else None
        pct = min(round(consumed / float(budget) * 100), 100) if budget else 0
        per_project.append({
            'project': project,
            'budget': budget,
            'consumed': consumed,
            'remaining': remaining,
            'pct': pct,
        })
    per_project.sort(key=lambda r: r['consumed'], reverse=True)

    per_member = (
        TimeLog.objects
        .filter(task__project__organization=org, task__project__deleted_at__isnull=True)
        .values('user__id', 'user__name', 'user__avatar')
        .annotate(logged_min=Sum('minutes'))
        .order_by('-logged_min')
    )

    member_project_breakdown = (
        TimeLog.objects
        .filter(task__project__organization=org, task__project__deleted_at__isnull=True)
        .values('user__id', 'user__name', 'task__project__id', 'task__project__name', 'task__project__key')
        .annotate(logged_min=Sum('minutes'))
        .order_by('user__name', '-logged_min')
    )
    breakdown_by_user = {}
    for row in member_project_breakdown:
        uid = str(row['user__id'])
        breakdown_by_user.setdefault(uid, []).append({
            'project__id': row['task__project__id'],
            'project__name': row['task__project__name'],
            'project__key': row['task__project__key'],
            'logged': round(row['logged_min'] / 60, 2),
        })

    per_member_with_breakdown = []
    for row in per_member:
        uid = str(row['user__id'])
        per_member_with_breakdown.append({
            'uid': uid,
            'name': row['user__name'],
            'logged': round(row['logged_min'] / 60, 2),
            'projects': breakdown_by_user.get(uid, []),
        })

    all_projects = list(projects)
    all_members = org.get_active_members()

    return render(request, 'organizations/org_hours_overview.html', {
        'org': org,
        'membership': org_membership,
        'per_project': per_project,
        'per_member': per_member_with_breakdown,
        'total_budget': total_budget or None,
        'total_consumed': total_consumed,
        'total_remaining': (total_budget - total_consumed) if total_budget else None,
        'total_pct': min(round(total_consumed / total_budget * 100), 100) if total_budget else 0,
        'all_projects': all_projects,
        'all_members': all_members,
    })


@login_required
@org_permission(_can_view_org_hours)
def org_hours_export(request, pk, org=None, org_membership=None):
    import csv
    import io
    from datetime import date
    from tasks.models import TimeLog

    fmt = request.GET.get('format', 'csv')
    date_from = request.GET.get('date_from') or None
    date_to = request.GET.get('date_to') or None
    project_id = request.GET.get('project') or None
    user_id = request.GET.get('user') or None

    qs = (
        TimeLog.objects
        .filter(task__project__organization=org, task__project__deleted_at__isnull=True)
        .select_related('task', 'task__project', 'user')
        .order_by('logged_date', 'task__project__name', 'user__name')
    )
    if date_from:
        qs = qs.filter(logged_date__gte=date_from)
    if date_to:
        qs = qs.filter(logged_date__lte=date_to)
    if project_id:
        qs = qs.filter(task__project_id=project_id)
    if user_id:
        qs = qs.filter(user_id=user_id)

    safe_org_name = re.sub(r'[^\w\-]', '_', org.name)[:40]
    filename_base = f'horas_{safe_org_name}_{date.today()}'
    headers = ['Fecha', 'Proyecto', 'Clave', 'Tarea', 'Ref. tarea', 'Usuario', 'Horas', 'Nota']

    def row_data(log):
        return [
            log.logged_date.strftime('%Y-%m-%d'),
            log.task.project.name,
            log.task.project.key,
            log.task.title,
            f'{log.task.project.key}-{log.task.project_sequence}',
            log.user.name,
            round(log.minutes / 60, 2),
            log.note or '',
        ]

    if fmt == 'xlsx':
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
        from django.http import HttpResponse

        wb = Workbook()
        ws = wb.active
        ws.title = 'Horas'
        ws.append(headers)
        header_fill = PatternFill('solid', fgColor='111111')
        header_font = Font(bold=True, color='FFFFFF')
        for col, _ in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        for log in qs:
            ws.append(row_data(log))
        for col in ws.columns:
            max_len = max(len(str(c.value or '')) for c in col)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 60)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename_base}.xlsx"'
        return response

    from django.http import HttpResponse
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
    response.write('﻿')
    writer = csv.writer(response)
    writer.writerow(headers)
    for log in qs:
        writer.writerow(row_data(log))
    return response


@login_required
@org_permission(_can_view_org_hours)
def org_hours_monthly(request, pk, org=None, org_membership=None):
    from tasks.models import TimeLog
    from django.db.models.functions import TruncMonth
    from datetime import date

    current_year = date.today().year
    year = int(request.GET.get('year', current_year))

    rows = (
        TimeLog.objects
        .filter(
            task__project__organization=org,
            task__project__deleted_at__isnull=True,
            logged_date__year=year,
        )
        .annotate(month=TruncMonth('logged_date'))
        .values('user__id', 'user__name', 'month')
        .annotate(logged_min=Sum('minutes'))
        .order_by('user__name', 'month')
    )

    MONTH_NAMES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                   'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

    users_map = {}
    active_months = set()

    for row in rows:
        uid = str(row['user__id'])
        month_num = row['month'].month
        active_months.add(month_num)
        if uid not in users_map:
            users_map[uid] = {'name': row['user__name'], 'months': {}, 'total': 0}
        hours = round(row['logged_min'] / 60, 2)
        users_map[uid]['months'][month_num] = hours
        users_map[uid]['total'] += hours

    months = sorted(active_months)
    month_labels = [MONTH_NAMES[m - 1] for m in months]

    month_totals = {m: 0.0 for m in months}
    for u in users_map.values():
        for m, h in u['months'].items():
            month_totals[m] += h

    pivot_rows = [
        {
            'name': u['name'],
            'cells': [u['months'].get(m, None) for m in months],
            'total': u['total'],
        }
        for u in sorted(users_map.values(), key=lambda x: x['name'])
    ]

    grand_total = sum(u['total'] for u in users_map.values())

    return render(request, 'organizations/org_hours_monthly.html', {
        'org': org,
        'membership': org_membership,
        'year': year,
        'prev_year': year - 1,
        'next_year': year + 1,
        'months': months,
        'month_labels': month_labels,
        'month_totals': [month_totals[m] for m in months],
        'pivot_rows': pivot_rows,
        'grand_total': grand_total,
        'has_data': bool(pivot_rows),
    })


@login_required
def global_search(request):
    from projects.models import ProjectMember
    from tasks.models import Task
    from django.urls import reverse

    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'tasks': [], 'projects': [], 'users': []})

    member_project_ids = ProjectMember.objects.filter(
        user=request.user
    ).values_list('project_id', flat=True)

    task_qs = (
        Task.objects
        .filter(project_id__in=member_project_ids, title__icontains=q)
        .select_related('project')
        .order_by('-updated_at')[:5]
    )
    tasks = [
        {
            'title': t.title,
            'key': f'{t.project.key}-{t.project_sequence}',
            'project': t.project.name,
            'url': reverse('task_detail', kwargs={'project_pk': str(t.project_id), 'pk': str(t.pk)}),
        }
        for t in task_qs
    ]

    proj_qs = (
        Project.objects
        .filter(
            id__in=member_project_ids,
            deleted_at__isnull=True,
        )
        .filter(Q(name__icontains=q) | Q(key__icontains=q))
        .order_by('name')[:5]
    )
    projects = [
        {
            'title': p.name,
            'key': p.key,
            'url': reverse('project_detail', kwargs={'pk': str(p.pk)}),
        }
        for p in proj_qs
    ]

    org_ids = OrganizationUser.objects.filter(
        user=request.user
    ).values_list('organization_id', flat=True)
    user_qs = (
        User.objects
        .filter(
            Q(name__icontains=q) | Q(email__icontains=q),
            organization_memberships__organization_id__in=org_ids,
            is_active=True,
        )
        .exclude(pk=request.user.pk)
        .distinct()
        .order_by('name')[:5]
    )
    users = [
        {
            'title': u.name,
            'subtitle': u.email,
            'initials': u.get_initials(),
        }
        for u in user_qs
    ]

    return JsonResponse({'tasks': tasks, 'projects': projects, 'users': users})
