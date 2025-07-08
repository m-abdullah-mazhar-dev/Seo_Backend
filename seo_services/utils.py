# utils.py (create this if not exists in your app)
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_stripe_product_and_price(package, amount_cents, currency="usd", interval="month"):
    # 1. Create Stripe Product
    product = stripe.Product.create(
        name=package.name,
        description=f"{package.name} Subscription Package",
        metadata={
            "package_name": package.name,
            "interval": str(package.interval),
            "service_limit": str(package.service_limit),
            "service_area_limit": str(package.service_area_limit),
            "business_location_limit": str(package.business_location_limit),
            "blog_limit": str(package.blog_limit),
            "keyword_limit": str(package.keyword_limit),
        }
    )

    # 2. Create Stripe Price
    price = stripe.Price.create(
        product=product.id,
        unit_amount=amount_cents,
        currency=currency,
        recurring={"interval": interval},
    )

    return product.id, price.id
