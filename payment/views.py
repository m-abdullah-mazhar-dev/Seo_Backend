from datetime import datetime, timezone
import stripe
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings

from payment.serializers import UserSubscriptionSerializer
from .models import Package, UserSubscription
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse

from django.contrib.auth import get_user_model
User = get_user_model()


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
        

class UpgradeSubscriptionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            new_package_id = request.data.get('new_package_id')
            new_package = Package.objects.get(id=new_package_id)
            subscription = UserSubscription.objects.get(user=user)

            if new_package.id == subscription.package.id:
                return Response({'error': 'You already have this package.'}, status=400)

            old_price = subscription.package.price
            new_price = new_package.price

            if new_price <= old_price:
                return Response({'error': 'Downgrade not allowed.'}, status=400)

            price_difference = (new_price - old_price) * 100  # in cents

            # Cancel current Stripe subscription (end of period)
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )

            # Create one-time PaymentIntent for price difference
            payment_intent = stripe.PaymentIntent.create(
                amount=int(price_difference),
                currency="usd",
                customer=subscription.stripe_customer_id,
                payment_method_types=['card'],
                metadata={
                    'user_id': user.id,
                    'upgrade_to': new_package.id,
                    'action': 'upgrade'
                }
            )

            return Response({
                'message': 'Upgrade initiated. Complete payment to proceed.',
                'client_secret': payment_intent.client_secret,
                'amount_due': str(new_price - old_price),
                'old_package': str(subscription.package.name),
                'new_package': str(new_package.name)
            })

        except Package.DoesNotExist:
            return Response({'error': 'New package not found.'}, status=404)
        except UserSubscription.DoesNotExist:
            return Response({'error': 'You have no active subscription.'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)



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
        # subscription_id = payment_intent['metadata'].get('subscription_id')
        metadata = payment_intent.get('metadata', {})
        action = metadata.get('action')

        # Upgrade logic
        if action == 'upgrade':
            user_id = metadata.get('user_id')
            new_package_id = metadata.get('upgrade_to')

            try:
                user = User.objects.get(id=user_id)
                subscription = UserSubscription.objects.get(user=user)
                new_package = Package.objects.get(id=new_package_id)

                # Create new subscription on Stripe
                new_stripe_sub = stripe.Subscription.create(
                    customer=subscription.stripe_customer_id,
                    items=[{'price': new_package.stripe_price_id}],
                    payment_behavior='default_incomplete',
                    expand=['latest_invoice.payment_intent'],
                    collection_method='charge_automatically',
                    off_session=False
                )

                # Update subscription model
                subscription.package = new_package
                subscription.stripe_subscription_id = new_stripe_sub.id
                subscription.status = 'active'
                subscription.save()

                print(f"✅ User {user.email} upgraded to {new_package.name}")

            except Exception as e:
                print(f"⚠️ Upgrade failed: {e}")
        else:

            subscription_id = metadata.get('subscription_id')
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



# class SubscriptionBaseView(APIView):
#     """Base class for subscription operations"""
    
#     def _get_current_subscription(self, user):
#         """Get current subscription or raise 404"""
#         try:
#             return UserSubscription.objects.get(user=user)
#         except UserSubscription.DoesNotExist:
#             return None
        

# from datetime import datetime
# from rest_framework.views import APIView
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response
# import stripe
# from django.conf import settings

# stripe.api_key = settings.STRIPE_SECRET_KEY

# class CreateSubscription(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         try:
#             package_id = request.data.get('package_id')
#             package = Package.objects.get(id=package_id)
#             user = request.user

#             # Check for existing subscription
#             if UserSubscription.objects.filter(user=user).exists():
#                 existing = UserSubscription.objects.get(user=user)
#                 return Response({
#                     'error': 'User already has subscription',
#                     'subscription_id': existing.stripe_subscription_id,
#                     'status': existing.status
#                 }, status=400)

#             # Create Stripe Customer
#             customer = stripe.Customer.create(
#                 email=user.email,
#                 name=f"{user.first_name} {user.last_name}",
#                 metadata={"user_id": user.id}
#             )

#             # Create Subscription
#             subscription = stripe.Subscription.create(
#                 customer=customer.id,
#                 items=[{'price': package.stripe_price_id}],
#                 payment_behavior='default_incomplete',
#                 expand=['latest_invoice.payment_intent'],
#                 payment_settings={
#                     'payment_method_types': ['card'],
#                     'save_default_payment_method': 'on_subscription'
#                 },
#                 collection_method='charge_automatically',
#                 off_session=False
#             )

#             # Handle payment intent
#             if not hasattr(subscription.latest_invoice, 'payment_intent'):
#                 payment_intent = stripe.PaymentIntent.create(
#                     amount=subscription.latest_invoice.amount_due,
#                     currency=subscription.latest_invoice.currency,
#                     customer=customer.id,
#                     payment_method_types=['card'],
#                     metadata={
#                         'subscription_id': subscription.id,
#                         'invoice_id': subscription.latest_invoice.id
#                     }
#                 )
#                 client_secret = payment_intent.client_secret
#             else:
#                 client_secret = subscription.latest_invoice.payment_intent.client_secret

#             # Save to database
#             UserSubscription.objects.create(
#                 user=user,
#                 package=package,
#                 stripe_customer_id=customer.id,
#                 stripe_subscription_id=subscription.id,
#                 status='incomplete',
#             )

#             return Response({
#                 'client_secret': client_secret,
#                 'subscription_id': subscription.id,
#                 'customer_id': customer.id,
#                 'requires_action': True
#             })

#         except Package.DoesNotExist:
#             return Response({'error': 'Package not found'}, status=404)
#         except stripe.error.StripeError as e:
#             return Response({'error': str(e)}, status=400)
#         except Exception as e:
#             return Response({'error': f"Server error: {str(e)}"}, status=500)
        
#     def get(self, request):
#         try:
#             subscription = UserSubscription.objects.get(user=request.user)
#             return Response({
#                 'status': subscription.status,
#                 'package': subscription.package.id,
#                 'current_period_end': subscription.current_period_end
#             })
#         except UserSubscription.DoesNotExist:
#             return Response({'error': 'No subscription found'}, status=404)
        
    

# class UpgradeSubscriptionAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         try:
#             user = request.user
#             new_package_id = request.data.get('new_package_id')
#             new_package = Package.objects.get(id=new_package_id)
            
#             # Get current subscription
#             try:
#                 current_sub = UserSubscription.objects.get(user=user)
#                 try:
#                     stripe_sub = stripe.Subscription.retrieve(current_sub.stripe_subscription_id)
#                 except stripe.error.InvalidRequestError:
#                     # Subscription doesn't exist in Stripe, treat as new
#                     return self._create_new_subscription(user, current_sub, new_package)
#             except UserSubscription.DoesNotExist:
#                 return Response({'error': 'No active subscription found'}, status=404)

#             # Check if same package
#             if new_package.id == current_sub.package.id:
#                 return Response({'error': 'Already subscribed to this package'}, status=400)

#             # Handle based on subscription status
#             if stripe_sub.status == 'active':
#                 return self._upgrade_active_subscription(current_sub, new_package, stripe_sub)
#             else:
#                 return self._handle_inactive_upgrade(user, current_sub, new_package, stripe_sub)

#         except Package.DoesNotExist:
#             return Response({'error': 'Package not found'}, status=404)
#         except Exception as e:
#             return Response({'error': str(e)}, status=500)

#     def _upgrade_active_subscription(self, current_sub, new_package, stripe_sub):
#         """Handle upgrade for active subscriptions with proper proration"""
#         try:
#             # Update subscription with proration
#             updated_sub = stripe.Subscription.modify(
#                 current_sub.stripe_subscription_id,
#                 items=[{
#                     'id': stripe_sub['items']['data'][0].id,
#                     'price': new_package.stripe_price_id,
#                 }],
#                 proration_behavior='create_prorations',
#                 payment_behavior='pending_if_incomplete',
#                 expand=['latest_invoice.payment_intent']
#             )

#             # Get payment intent if immediate payment is needed
#             payment_intent = None
#             if hasattr(updated_sub, 'latest_invoice') and hasattr(updated_sub.latest_invoice, 'payment_intent'):
#                 payment_intent = updated_sub.latest_invoice.payment_intent

#             # Update database
#             current_sub.package = new_package
#             if getattr(updated_sub, "current_period_end", None):
#                 current_sub.current_period_end = datetime.fromtimestamp(updated_sub.current_period_end)
#             current_sub.save()

#             return Response({
#                 'message': 'Upgrade successful',
#                 'client_secret': payment_intent.client_secret if payment_intent else None,
#                 'requires_action': payment_intent is not None,
#                 'subscription_id': current_sub.stripe_subscription_id,
#                 'is_prorated': True if payment_intent else False
#             })

#         except Exception as e:
#             return Response({'error': f"Upgrade failed: {str(e)}"}, status=500)

#     def _handle_inactive_upgrade(self, user, current_sub, new_package, stripe_sub):
#         """Handle upgrade for inactive/canceled subscriptions"""
#         try:
#             # Only attempt to cancel if subscription exists and isn't already canceled
#             if stripe_sub.status != 'canceled':
#                 try:
#                     stripe.Subscription.delete(current_sub.stripe_subscription_id)
#                 except stripe.error.InvalidRequestError:
#                     # Subscription already doesn't exist, proceed with new one
#                     pass

#             return self._create_new_subscription(user, current_sub, new_package)

#         except Exception as e:
#             return Response({'error': f"Failed to cancel old subscription: {str(e)}"}, status=500)

#     def _create_new_subscription(self, user, old_sub, new_package):
#         """Create brand new subscription"""
#         try:
#             subscription = stripe.Subscription.create(
#                 customer=old_sub.stripe_customer_id,
#                 items=[{'price': new_package.stripe_price_id}],
#                 payment_behavior='default_incomplete',
#                 expand=['latest_invoice.payment_intent'],
#                 payment_settings={
#                     'payment_method_types': ['card'],
#                     'save_default_payment_method': 'on_subscription'
#                 },
#                 collection_method='charge_automatically',
#                 off_session=False
#             )

#             # Get payment intent
#             payment_intent = None
#             if hasattr(subscription, 'latest_invoice') and hasattr(subscription.latest_invoice, 'payment_intent'):
#                 payment_intent = subscription.latest_invoice.payment_intent
#             else:
#                 payment_intent = stripe.PaymentIntent.create(
#                     amount=subscription.latest_invoice.amount_due,
#                     currency=subscription.latest_invoice.currency,
#                     customer=old_sub.stripe_customer_id,
#                     payment_method_types=['card'],
#                     metadata={
#                         'subscription_id': subscription.id,
#                         'invoice_id': subscription.latest_invoice.id
#                     }
#                 )

#             # Update database
#             old_sub.package = new_package
#             old_sub.stripe_subscription_id = subscription.id
#             old_sub.status = 'incomplete'
#             if getattr(subscription, "current_period_end", None):
#                 old_sub.current_period_end = datetime.fromtimestamp(subscription.current_period_end)
#             old_sub.save()

#             return Response({
#                 'client_secret': payment_intent.client_secret,
#                 'subscription_id': subscription.id,
#                 'requires_action': True,
#                 'is_new_subscription': True
#             })

#         except Exception as e:
#             return Response({'error': f"Failed to create new subscription: {str(e)}"}, status=500)


# from django.views.decorators.csrf import csrf_exempt
# from django.http import HttpResponse
# from datetime import datetime

# @csrf_exempt
# def stripe_webhook(request):
#     payload = request.body
#     sig_header = request.META['HTTP_STRIPE_SIGNATURE']
#     endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

#     try:
#         event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
#     except ValueError:
#         return HttpResponse(status=400)
#     except stripe.error.SignatureVerificationError:
#         return HttpResponse(status=400)

#     # Handle subscription updates
#     if event['type'] in ['customer.subscription.updated', 'customer.subscription.created']:
#         subscription = event['data']['object']
#         try:
#             user_sub = UserSubscription.objects.get(stripe_subscription_id=subscription.id)
#             user_sub.status = subscription.status
#             # Only set if Stripe sent it
#             if 'current_period_end' in subscription and subscription['current_period_end']:
#                 user_sub.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
            
#             # Special handling for upgrades
#             if event['type'] == 'customer.subscription.updated':
#                 print(f"Subscription updated: {subscription.id}")
#             user_sub.save()
#         except UserSubscription.DoesNotExist:
#             pass

#         # Handle invoice payment success
#     if event['type'] == 'invoice.payment_succeeded':
#         invoice = event['data']['object']
#         if invoice.get('subscription'):
#             try:
#                 user_sub = UserSubscription.objects.get(stripe_subscription_id=invoice['subscription'])
#                 user_sub.status = 'active'
                
#                 # Check if this is an upgrade invoice
#                 if invoice.billing_reason == 'subscription_update':
#                     print(f"Upgrade proration invoice paid: {invoice.amount_paid/100}")
                
#                 user_sub.save()
#             except UserSubscription.DoesNotExist:
#                 pass
#     elif event['type'] == 'payment_intent.succeeded':
#         pi = event['data']['object']
#         sub_id = pi.metadata.get('subscription_id')
#         if sub_id:
#             try:
#                 user_sub = UserSubscription.objects.get(stripe_subscription_id=sub_id)
#                 user_sub.status = 'active'
#                 user_sub.save()
#             except UserSubscription.DoesNotExist:
#                 pass


#     # Handle payment failures
#     elif event['type'] == 'invoice.payment_failed':
#         invoice = event['data']['object']
#         if invoice.get('subscription'):
#             try:
#                 user_sub = UserSubscription.objects.get(stripe_subscription_id=invoice['subscription'])
#                 user_sub.status = 'past_due'
#                 user_sub.save()
#             except UserSubscription.DoesNotExist:
#                 pass

#     return HttpResponse(status=200)



class SubscriptionDetailsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user_sub = UserSubscription.objects.select_related("package").get(user=request.user)
            stripe_sub = stripe.Subscription.retrieve(user_sub.stripe_subscription_id)

            # Try to get period dates from subscription root or fallback to items
            current_period_start = stripe_sub.get("current_period_start") or \
                stripe_sub["items"]["data"][0].get("current_period_start")
            current_period_end = stripe_sub.get("current_period_end") or \
                stripe_sub["items"]["data"][0].get("current_period_end")

            if not current_period_start or not current_period_end:
                return Response({
                    "plan_name": user_sub.package.name,
                    "status": stripe_sub["status"],
                    "message": "No active billing period for this subscription."
                }, status=200)

            # Convert timestamps
            current_period_start = datetime.fromtimestamp(current_period_start, tz=timezone.utc)
            current_period_end = datetime.fromtimestamp(current_period_end, tz=timezone.utc)

            # Calculate usage
            total_days = (current_period_end - current_period_start).days
            days_used = max(0, (datetime.now(timezone.utc) - current_period_start).days)
            days_remaining = max(0, (current_period_end - datetime.now(timezone.utc)).days)

            # Package details
            package = user_sub.package
            interval = stripe_sub["items"]["data"][0]["price"]["recurring"]["interval"]

            data = {
                "plan_name": package.name,
                "price": float(package.price),
                "interval": interval,
                "purchased_on": current_period_start.strftime("%Y-%m-%d"),
                "expires_on": current_period_end.strftime("%Y-%m-%d"),
                "status": stripe_sub["status"],
                "days_used": days_used,
                "days_remaining": days_remaining,
                "total_days": total_days,
            }
            return Response(data)

        except UserSubscription.DoesNotExist:
            return Response({"error": "No active subscription found."}, status=404)
        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            return Response({"error": f"Server error: {str(e)}"}, status=500)
        



class CancelSubscriptionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            # 1️⃣ Get subscription record from DB
            subscription = UserSubscription.objects.filter(user=user).first()
            if not subscription:
                return Response({"error": "No subscription found for this user."}, status=404)

            if not subscription.stripe_subscription_id:
                return Response({"error": "No Stripe subscription ID found in DB."}, status=400)

            try:
                # 2️⃣ Try to cancel immediately on Stripe
                canceled_sub = stripe.Subscription.delete(subscription.stripe_subscription_id)

                # 3️⃣ Update DB only if Stripe returned a valid subscription
                subscription.status = "canceled"
                if getattr(canceled_sub, "current_period_end", None):
                    subscription.current_period_end = datetime.fromtimestamp(
                        canceled_sub.current_period_end
                    )
                subscription.save()

                return Response({
                    "message": "Subscription canceled successfully.",
                    "stripe_status": canceled_sub.status,
                    "current_period_end": subscription.current_period_end
                })

            except stripe.error.InvalidRequestError as e:
                # This happens if subscription ID does not exist on Stripe
                subscription.status = "error"
                subscription.save()
                return Response({
                    "error": "Stripe subscription not found or already canceled.",
                    "details": str(e)
                }, status=404)

        except stripe.error.StripeError as e:
            return Response({"error": f"Stripe error: {str(e)}"}, status=400)
        except Exception as e:
            return Response({"error": f"Server error: {str(e)}"}, status=500)
