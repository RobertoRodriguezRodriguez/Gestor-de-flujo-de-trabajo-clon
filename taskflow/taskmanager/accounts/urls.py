from django.urls import path
from . import views
from . import stripe_views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('login/2fa/', views.two_factor_verify, name='two_factor_verify'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/2fa/setup/', views.two_factor_setup, name='two_factor_setup'),
    path('profile/2fa/disable/', views.two_factor_disable, name='two_factor_disable'),
    path('pricing/', views.pricing_view, name='pricing'),
    path('set-theme/', views.set_theme_view, name='set_theme'),
    path('users/<uuid:pk>/', views.user_profile_view, name='user_profile'),
    path('payments/checkout/', stripe_views.create_checkout_session, name='checkout'),
    path('payments/success/', stripe_views.checkout_success, name='checkout_success'),
    path('payments/webhook/', stripe_views.stripe_webhook, name='stripe_webhook'),
]
