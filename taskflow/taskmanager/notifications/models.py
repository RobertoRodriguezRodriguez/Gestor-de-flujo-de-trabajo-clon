import uuid
from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = [
        ('task_assigned', 'Tarea asignada'),
        ('task_due', 'Tarea por vencer'),
        ('task_completed', 'Tarea completada'),
        ('comment_added', 'Nuevo comentario'),
        ('status_changed', 'Estado cambiado'),
        ('sprint_started', 'Sprint iniciado'),
        ('mentioned', 'Mencionado'),
        ('hours_validation_requested', 'Validación de horas solicitada'),
        ('hours_validated', 'Estimación de horas validada'),
        ('hours_exceeded', 'Horas estimadas superadas'),
        ('org_added', 'Añadido a organización'),
        ('project_added', 'Añadido a proyecto'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    task = models.ForeignKey('tasks.Task', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notification'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.type}] {self.user.name}: {self.message[:50]}'
