import io
import base64

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from django_otp.plugins.otp_totp.models import TOTPDevice
from .forms import LoginForm, RegisterForm, ProfileForm

User = get_user_model()
PREMIUM_THEMES = {'pink', 'red', 'blue', 'green'}


def _rate_limited_response(request, template):
    return render(request, template, {'rate_limited': True}, status=429)


def _get_confirmed_device(user):
    return TOTPDevice.objects.filter(user=user, confirmed=True).first()


def _qr_b64(device):
    import qrcode
    img = qrcode.make(device.config_url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


@ratelimit(key='ip', rate='5/m', method='POST', block=False)
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if getattr(request, 'limited', False):
        return _rate_limited_response(request, 'accounts/login.html')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            if _get_confirmed_device(user):
                request.session['2fa_user_pk'] = str(user.pk)
                request.session['2fa_backend'] = user.backend
                return redirect('two_factor_verify')
            user.last_login_at = timezone.now()
            user.save(update_fields=['last_login_at'])
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)

    return render(request, 'accounts/login.html', {'form': form})


@ratelimit(key='ip', rate='5/m', method='POST', block=False)
def two_factor_verify(request):
    user_pk = request.session.get('2fa_user_pk')
    if not user_pk:
        return redirect('login')
    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return redirect('login')

    error = None
    if request.method == 'POST':
        if getattr(request, 'limited', False):
            error = 'Demasiados intentos. Espera un momento e inténtalo de nuevo.'
        else:
            token = request.POST.get('token', '').strip()
            device = _get_confirmed_device(user)
            if device and device.verify_token(token):
                del request.session['2fa_user_pk']
                backend = request.session.pop('2fa_backend',
                    'django.contrib.auth.backends.ModelBackend')
                user.backend = backend
                user.last_login_at = timezone.now()
                user.save(update_fields=['last_login_at'])
                login(request, user)
                return redirect(request.GET.get('next', 'dashboard'))
            error = 'Código incorrecto. Inténtalo de nuevo.'

    return render(request, 'accounts/2fa_verify.html', {'error': error})


@ratelimit(key='ip', rate='3/m', method='POST', block=False)
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if getattr(request, 'limited', False):
        return _rate_limited_response(request, 'accounts/register.html')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Bienvenido/a, {user.name}!')
            return redirect('dashboard')

    return render(request, 'accounts/register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def profile_view(request):
    from django.db.models import Sum, Count, Q
    from tasks.models import Task, TimeLog

    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        instance = form.save(commit=False)
        instance.save(update_fields=['name', 'email', 'avatar'])
        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('profile')

    total_min = (
        TimeLog.objects.filter(user=request.user)
        .aggregate(total=Sum('minutes'))['total'] or 0
    )
    total_hours = round(total_min / 60, 2)

    task_counts = Task.objects.filter(assignee=request.user).aggregate(
        done=Count('id', filter=Q(status='done')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        in_review=Count('id', filter=Q(status='in_review')),
        total=Count('id'),
    )

    hours_by_project = (
        TimeLog.objects.filter(user=request.user)
        .values(
            'task__project__id', 'task__project__name', 'task__project__key',
            'task__project__organization__id', 'task__project__organization__name',
        )
        .annotate(logged_min=Sum('minutes'))
        .order_by('task__project__organization__name', '-logged_min')
    )
    tasks_by_project = (
        Task.objects.filter(assignee=request.user)
        .values('project__id')
        .annotate(total=Count('id'), done=Count('id', filter=Q(status='done')))
    )
    tasks_map = {str(r['project__id']): r for r in tasks_by_project}

    orgs_map = {}
    for row in hours_by_project:
        oid = str(row['task__project__organization__id'])
        pid = str(row['task__project__id'])
        if oid not in orgs_map:
            orgs_map[oid] = {'name': row['task__project__organization__name'], 'projects': []}
        t = tasks_map.get(pid, {})
        orgs_map[oid]['projects'].append({
            'id': row['task__project__id'],
            'name': row['task__project__name'],
            'key': row['task__project__key'],
            'logged': round(row['logged_min'] / 60, 2),
            'tasks_total': t.get('total', 0),
            'tasks_done': t.get('done', 0),
        })
    activity_by_org = list(orgs_map.values())

    return render(request, 'accounts/profile.html', {
        'form': form,
        'totp_enabled': _get_confirmed_device(request.user) is not None,
        'total_hours': total_hours,
        'task_counts': task_counts,
        'activity_by_org': activity_by_org,
    })


@login_required
def two_factor_setup(request):
    if _get_confirmed_device(request.user):
        messages.info(request, 'La autenticación en dos pasos ya está activada.')
        return redirect('profile')

    device, _ = TOTPDevice.objects.get_or_create(
        user=request.user, confirmed=False,
        defaults={'name': f'e-asy ({request.user.email})'},
    )

    error = None
    if request.method == 'POST':
        token = request.POST.get('token', '').strip()
        if device.verify_token(token):
            device.confirmed = True
            device.save()
            messages.success(request, 'Autenticación en dos pasos activada correctamente.')
            return redirect('profile')
        error = 'Código incorrecto. Escanea el QR con tu app e inténtalo de nuevo.'

    return render(request, 'accounts/2fa_setup.html', {
        'device': device,
        'qr_b64': _qr_b64(device),
        'secret': device.config_url.split('secret=')[1].split('&')[0],
        'error': error,
    })


@login_required
@require_POST
def two_factor_disable(request):
    device = _get_confirmed_device(request.user)
    if not device:
        messages.info(request, 'La autenticación en dos pasos no está activada.')
        return redirect('profile')

    token = request.POST.get('token', '').strip()
    if device.verify_token(token):
        TOTPDevice.objects.filter(user=request.user).delete()
        messages.success(request, 'Autenticación en dos pasos desactivada.')
    else:
        messages.error(request, 'Código incorrecto. El 2FA no se ha desactivado.')

    return redirect('profile')


@login_required
def pricing_view(request):
    free_features = [
        'Proyectos ilimitados',
        'Gestión de tareas (Kanban y lista)',
        'Organizaciones y equipos',
        'Notificaciones en tiempo real',
        'Modo claro y oscuro',
        'Perfil con avatar',
    ]
    premium_features = [
        'Temas de color exclusivos (Rosa, Rojo, Azul, Verde)',
        'Temas combinados claro/oscuro con color',
        'Soporte prioritario',
        'Próximamente: informes avanzados',
        'Próximamente: integraciones externas',
    ]
    return render(request, 'accounts/pricing.html', {
        'free_features': free_features,
        'premium_features': premium_features,
    })


@login_required
@require_POST
def set_theme_view(request):
    base = request.POST.get('base')
    color = request.POST.get('color')
    fields = []

    if base is not None:
        if base not in {'dark', 'light'}:
            return JsonResponse({'error': 'Base inválida'}, status=400)
        request.user.base_theme = base
        fields.append('base_theme')

    if color is not None:
        valid_colors = {'default'} | PREMIUM_THEMES
        if color not in valid_colors:
            return JsonResponse({'error': 'Color inválido'}, status=400)
        if color in PREMIUM_THEMES and not request.user.is_premium:
            return JsonResponse({'error': 'Requiere plan Premium'}, status=403)
        request.user.color_theme = color
        fields.append('color_theme')

    if fields:
        request.user.save(update_fields=fields)
    return JsonResponse({'ok': True})
