import logging

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)


@login_required
def create_checkout_session(request):
    if request.user.is_premium:
        messages.warning(request, 'Ya eres Premium.')
        return redirect('pricing')

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': settings.STRIPE_PRICE_ID,
            'quantity': 1,
        }],
        mode='subscription',
        customer_email=request.user.email,
        # UUID stored here so the webhook can identify the user without relying on email.
        client_reference_id=str(request.user.pk),
        success_url=request.build_absolute_uri('/payments/success/') + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=request.build_absolute_uri('/pricing/?cancelled=true'),
    )
    return redirect(session.url)


@login_required
def checkout_success(request):
    session_id = request.GET.get('session_id')
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == 'paid':
                from accounts.models import User
                User.objects.filter(pk=request.user.pk).update(is_premium=True)
                request.user.is_premium = True
                messages.success(request, '¡Pago completado! Ya eres Premium.')
            else:
                messages.warning(request, 'El pago aún no se ha confirmado.')
        except Exception:
            logger.exception('Error verifying Stripe checkout session %s', session_id)
            messages.error(request, 'No se pudo verificar el pago. Contacta con soporte.')
    return redirect('pricing')


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_pk = session.get('client_reference_id')
        customer_id = session.get('customer')
        if user_pk:
            from accounts.models import User
            update_fields = {'is_premium': True}
            if customer_id:
                update_fields['stripe_customer_id'] = customer_id
            updated = User.objects.filter(pk=user_pk).update(**update_fields)
            if not updated:
                logger.error(
                    'Stripe webhook checkout.session.completed: no user found for pk=%s', user_pk
                )

    elif event['type'] == 'customer.subscription.deleted':
        customer_id = event['data']['object'].get('customer')
        if customer_id:
            from accounts.models import User
            updated = User.objects.filter(stripe_customer_id=customer_id).update(is_premium=False)
            if not updated:
                logger.error(
                    'Stripe webhook subscription.deleted: no user found for customer_id=%s', customer_id
                )

    return HttpResponse(status=200)
