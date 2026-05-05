import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Project(models.Model):
    STATUS_CHOICES = [
        ('planning', 'Planificación'),
        ('active', 'Activo'),
        ('on_hold', 'En pausa'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='projects')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_projects')
    key = models.CharField(max_length=10, help_text='Clave corta del proyecto, ej: TM')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    hour_budget = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'project'
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        unique_together = ('organization', 'key')
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.key}] {self.name}'

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def get_hour_stats(self):
        from django.db.models import Sum
        consumed_min = self.time_logs.aggregate(total=Sum('minutes'))['total'] or 0
        consumed = round(consumed_min / 60, 2)
        if self.hour_budget:
            remaining = float(self.hour_budget) - consumed
            pct = min(round(consumed / float(self.hour_budget) * 100), 100)
        else:
            remaining = None
            pct = 0
        return {'budget': self.hour_budget, 'consumed': consumed, 'remaining': remaining, 'pct': pct}

    def get_task_stats(self):
        tasks = self.tasks.all()
        total = tasks.count()
        done = tasks.filter(status='done').count()
        return {
            'total': total,
            'done': done,
            'progress': round((done / total * 100) if total > 0 else 0),
        }


class ProjectMember(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Propietario'),
        ('manager', 'Manager'),
        ('developer', 'Desarrollador'),
        ('viewer', 'Observador'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='developer')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'project_member'
        unique_together = ('project', 'user')
        verbose_name = 'Miembro del proyecto'
        verbose_name_plural = 'Miembros del proyecto'

    def __str__(self):
        return f'{self.user.name} → {self.project.name}'


class Sprint(models.Model):
    STATUS_CHOICES = [
        ('planned', 'Planificado'),
        ('active', 'Activo'),
        ('completed', 'Completado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sprints')
    name = models.CharField(max_length=200)
    goal = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sprint'
        verbose_name = 'Sprint'
        verbose_name_plural = 'Sprints'
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.project.key} — {self.name}'
