import stripe
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings

from payment.serializers import UserSubscriptionSerializer
from .models import Package, UserSubscription
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse

stripe.api_key = settings.STRIPE_SECRET_KEY
class CreateSubscription(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            package_id = request.data.get('package_id')
            package = Package.objects.get(id=package_id)
            user = request.user

            # 1. Create Stripe Customer
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}",
                metadata={"user_id": user.id}
            )

            # 2. Create Subscription with explicit payment collection
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': package.stripe_price_id}],
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent'],
                payment_settings={
                    'payment_method_types': ['card'],
                    'save_default_payment_method': 'on_subscription'
                },
                collection_method='charge_automatically',  # Explicitly set
                off_session=False  # Ensure immediate payment
            )

            # 3. Verify and extract payment intent
            if not hasattr(subscription.latest_invoice, 'payment_intent'):
                # Manually create payment intent if missing
                payment_intent = stripe.PaymentIntent.create(
                    amount=subscription.latest_invoice.amount_due,
                    currency=subscription.latest_invoice.currency,
                    customer=customer.id,
                    payment_method_types=['card'],
                    metadata={
                        'subscription_id': subscription.id,
                        'invoice_id': subscription.latest_invoice.id
                    }
                )
                client_secret = payment_intent.client_secret
            else:
                client_secret = subscription.latest_invoice.payment_intent.client_secret

            # 4. Save to database
            UserSubscription.objects.create(
                user=user,
                package=package,
                stripe_customer_id=customer.id,
                stripe_subscription_id=subscription.id,
                status='incomplete',
            )

            return Response({
                'client_secret': client_secret,
                'subscription_id': subscription.id,
                'customer_id': customer.id,
                'requires_action': True if 'pi_' in client_secret else False
            })

        except Package.DoesNotExist:
            return Response({'error': 'Package not found'}, status=404)
        except stripe.error.StripeError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            return Response({'error': f"Server error: {str(e)}"}, status=500)
        
    def get(self, request):
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            serializer = UserSubscriptionSerializer(subscription)
            return Response(serializer.data)
        except UserSubscription.DoesNotExist:
            return Response({'error': 'No subscription found for the user.'}, status=404)


# @csrf_exempt
# def stripe_webhook(request):
#     payload = request.body
#     sig_header = request.META['HTTP_STRIPE_SIGNATURE']
#     endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

#     try:
#         event = stripe.Webhook.construct_event(
#             payload, sig_header, endpoint_secret
#         )
#     except ValueError:
#         return HttpResponse(status=400)
#     except stripe.error.SignatureVerificationError:
#         return HttpResponse(status=400)
    
#     print("🔔 Webhook received: ", event['type'])


#     if event['type'] == 'invoice.paid':
#         invoice = event['data']['object']
#         subscription_id = invoice['subscription']

#         # ✅ Update subscription to active
#         try:
#             user_subscription = UserSubscription.objects.get(stripe_subscription_id=subscription_id)
#             user_subscription.status = 'active'
#             user_subscription.save()
#             print(f'✅ Subscription {subscription_id} marked as active.')
#         except UserSubscription.DoesNotExist:
#             print(f'❌ Subscription {subscription_id} not found in database.')

#     if event['type'] == 'invoice.payment_failed':
#         invoice = event['data']['object']
#         subscription_id = invoice['subscription']

#         # ✅ Mark subscription as failed
#         try:
#             user_subscription = UserSubscription.objects.get(stripe_subscription_id=subscription_id)
#             user_subscription.status = 'incomplete'
#             user_subscription.save()
#             print(f'❌ Subscription {subscription_id} marked as payment_failed.')
#         except UserSubscription.DoesNotExist:
#             print(f'❌ Subscription {subscription_id} not found in database.')

#     return HttpResponse(status=200)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    print("🔔 Webhook received: ", event['type'])

    # Handle payment success
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        subscription_id = payment_intent['metadata'].get('subscription_id')

        if subscription_id:
            try:
                user_subscription = UserSubscription.objects.get(stripe_subscription_id=subscription_id)
                user_subscription.status = 'active'
                user_subscription.save()
                print(f'✅ Subscription {subscription_id} marked as active.')
            except UserSubscription.DoesNotExist:
                print(f'❌ Subscription {subscription_id} not found in database.')
        else:
            print('⚠️ No subscription_id found in payment_intent metadata.')

    # You can still keep invoice.paid if you want to support invoice-based payments too
    if event['type'] == 'invoice.paid':
        invoice = event['data']['object']
        subscription_id = invoice['subscription']

        try:
            user_subscription = UserSubscription.objects.get(stripe_subscription_id=subscription_id)
            user_subscription.status = 'active'
            user_subscription.save()
            print(f'✅ Subscription {subscription_id} marked as active.')
        except UserSubscription.DoesNotExist:
            print(f'❌ Subscription {subscription_id} not found in database.')

    if event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        subscription_id = invoice['subscription']

        try:
            user_subscription = UserSubscription.objects.get(stripe_subscription_id=subscription_id)
            user_subscription.status = 'incomplete'
            user_subscription.save()
            print(f'❌ Subscription {subscription_id} marked as payment_failed.')
        except UserSubscription.DoesNotExist:
            print(f'❌ Subscription {subscription_id} not found in database.')

    return HttpResponse(status=200)
