import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('manager', 'Manager'),
        ('member', 'Miembro'),
    ]
    BASE_THEME_CHOICES = [
        ('dark', 'Oscuro'),
        ('light', 'Claro'),
    ]
    ACCENT_CHOICES = [
        ('default', 'Por defecto'),
        ('pink', 'Rosa'),
        ('red', 'Rojo'),
        ('blue', 'Azul'),
        ('green', 'Verde'),
    ]
    PREMIUM_THEMES = {'pink', 'red', 'blue', 'green'}

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    description = models.TextField(blank=True, default='')
    company_role = models.CharField(max_length=100, blank=True, default='')
    hours_pool = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    base_theme = models.CharField(max_length=10, choices=BASE_THEME_CHOICES, default='dark')
    color_theme = models.CharField(max_length=20, choices=ACCENT_CHOICES, default='default')
    last_login_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'user'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f'{self.name} ({self.email})'

    def get_initials(self):
        parts = self.name.split()
        if len(parts) >= 2:
            return f'{parts[0][0]}{parts[1][0]}'.upper()
        return self.name[:2].upper()
