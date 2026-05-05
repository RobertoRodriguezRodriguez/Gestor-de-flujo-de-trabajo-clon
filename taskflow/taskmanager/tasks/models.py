import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#6366f1')

    class Meta:
        db_table = 'tag'
        unique_together = ('project', 'name')

    def __str__(self):
        return self.name


class Task(models.Model):
    TYPE_CHOICES = [
        ('task', 'Tarea'),
        ('bug', 'Bug'),
        ('story', 'Historia'),
        ('epic', 'Épica'),
        ('subtask', 'Subtarea'),
    ]
    STATUS_CHOICES = [
        ('backlog', 'Backlog'),
        ('todo', 'Por hacer'),
        ('in_progress', 'En progreso'),
        ('in_review', 'En revisión'),
        ('done', 'Hecho'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='tasks')
    sprint = models.ForeignKey('projects.Sprint', on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    assignees = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='tasks_assigned', db_table='task_assignee')
    task_responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='responsible_tasks',
    )
    parent_task = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subtasks')
    project_sequence = models.PositiveIntegerField(default=0)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='task')
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='backlog', db_index=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    position = models.IntegerField(default=0)
    estimated_min = models.IntegerField(null=True, blank=True, help_text='Estimación en minutos')
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    task_responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='responsible_tasks',
    )
    hours_requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='hours_requested_tasks',
    )
    hours_validated = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField(Tag, through='TaskTag', blank=True, related_name='tasks')

    class Meta:
        db_table = 'task'
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'
        ordering = ['position', '-created_at']

    def __str__(self):
        return f'[{self.project.key}-{self.project_sequence}] {self.title}'

    def save(self, *args, **kwargs):
        if not self.project_sequence:
            last = Task.objects.filter(project=self.project).order_by('-project_sequence').first()
            self.project_sequence = (last.project_sequence + 1) if last else 1
        if self.status == 'done' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != 'done':
            self.completed_at = None
        super().save(*args, **kwargs)

    def get_total_logged_minutes(self):
        return sum(t.minutes for t in self.time_logs.all())

    def is_overdue(self):
        if self.due_date and self.status != 'done':
            return self.due_date < timezone.now().date()
        return False


class TaskTag(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='task_tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='task_tags')

    class Meta:
        db_table = 'task_tag'
        unique_together = ('task', 'tag')


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        db_table = 'comment'
        ordering = ['created_at']

    def __str__(self):
        return f'Comentario de {self.user.name} en {self.task}'


class Attachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='attachments')
    file = models.FileField(upload_to='attachments/')
    filename = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'attachment'

    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            self.filename = self.file.name.split('/')[-1]
        super().save(*args, **kwargs)


class TimeLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='time_logs')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='time_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='time_logs')
    minutes = models.PositiveIntegerField()
    note = models.TextField(blank=True)
    logged_date = models.DateField(default=timezone.now)

    class Meta:
        db_table = 'time_log'
        ordering = ['-logged_date']

    def __str__(self):
        return f'{self.minutes} min — {self.task}'

    @property
    def hours_display(self):
        h = self.minutes // 60
        m = self.minutes % 60
        return f'{h}h {m}m' if h else f'{m}m'
