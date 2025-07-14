import requests
from django.utils.text import slugify


def upload_job_post_to_wordpress(job_form, job_page, html_content):
    wp_conn = job_page.wordpress_connection
    title = f"{job_form.company_name} - Hiring CDL Drivers"

    slug = slugify(title)
    post_data = {
        "title": title,
        "slug": slug,
        "content": f"<div>{html_content}</div>",
        "status": "publish"
    }

    headers = {
        'Authorization': f'Basic {wp_conn.access_token}',
        'Content-Type': 'application/json',
    }

    response = requests.post(
        f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/posts",
        headers=headers,
        json=post_data
    )

    if response.status_code not in [200, 201]:
        raise Exception(f"WordPress upload failed: {response.text}")




import json
from django.utils.html import escape
from datetime import datetime

def generate_structured_job_html(job_form):
    """
    Generates structured HTML (schema.org/JobPosting) for Google for Jobs.
    """

    # Optional cleanups / helpers
    def safe(value):
        return escape(value) if value else ""

    today = datetime.utcnow().date().isoformat()

    job_posting = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": f"CDL Truck Driver - {job_form.company_name}",
        "description": f"""
            <ul>
                <li><strong>Weekly Earnings:</strong> {safe(job_form.drivers_weekly_earning)}</li>
                <li><strong>Miles per Week:</strong> {safe(job_form.drivers_weekly_miles)}</li>
                <li><strong>CPM:</strong> {safe(job_form.cpm)}</li>
                <li><strong>Driver % Pay:</strong> {safe(job_form.driver_percentage)}</li>
                <li><strong>Equipment:</strong> {safe(job_form.hauling_equipment)}</li>
                <li><strong>Transmission:</strong> {"Automatic" if job_form.transmission_automatic else ""} {"Manual" if job_form.transmission_manual else ""}</li>
                <li><strong>Cash Advance:</strong> {"Yes" if job_form.offer_cash_advances else "No"} - {safe(job_form.cash_advance_amount)}</li>
                <li><strong>Referral Bonus:</strong> {"Yes" if job_form.referral_bonus else "No"} - {safe(job_form.referral_bonus_amount)}</li>
                <li><strong>Fuel Card:</strong> {"Yes" if job_form.fuel_card else "No"} - {safe(job_form.fuel_card_type)}</li>
                <li><strong>Pet Friendly:</strong> {"Yes" if job_form.allow_pets_pessenger else "No"}</li>
                <li><strong>Speed:</strong> {safe(job_form.truck_governed_speed)}</li>
                <li><strong>Toll Passes:</strong> {safe(job_form.toll_passes)}</li>
            </ul>
        """,
        "datePosted": today,
        "employmentType": [],
        "hiringOrganization": {
            "@type": "Organization",
            "name": safe(job_form.company_name),
            "sameAs": safe(job_form.company_website),
            "logo": job_form.company_logo.url if job_form.company_logo else "",
        },
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": safe(job_form.company_address),
                "addressLocality": "USA",  # Add dynamic city/state if parsed
                "addressRegion": "",
                "postalCode": "",
                "addressCountry": "US"
            }
        },
        "validThrough": f"{datetime.utcnow().date().replace(year=datetime.utcnow().year + 1)}",
        "baseSalary": {
            "@type": "MonetaryAmount",
            "currency": "USD",
            "value": {
                "@type": "QuantitativeValue",
                "value": float(job_form.cpm.replace("$", "").replace(",", "") or 0.55),
                "unitText": "HOUR"
            }
        }
    }

    # Employment Type
    if job_form.position_1099:
        job_posting["employmentType"].append("CONTRACTOR")
    if job_form.position_w2:
        job_posting["employmentType"].append("FULL_TIME")

    # Add fallback
    if not job_posting["employmentType"]:
        job_posting["employmentType"].append("OTHER")

    # Generate final HTML
    html = f"""
    <html>
    <head>
        <title>{safe(job_form.company_name)} - CDL Driver Job</title>
        <script type="application/ld+json">
        {json.dumps(job_posting, indent=4)}
        </script>
    </head>
    <body>
        <h1>CDL Driver Job - {safe(job_form.company_name)}</h1>
        <p><strong>Location:</strong> {safe(job_form.company_address)}</p>
        <p><strong>Weekly Earnings:</strong> {safe(job_form.drivers_weekly_earning)}</p>
        <p><strong>Miles per Week:</strong> {safe(job_form.drivers_weekly_miles)}</p>
        <p><strong>Equipment:</strong> {safe(job_form.hauling_equipment)}</p>
        <p><strong>Speed:</strong> {safe(job_form.truck_governed_speed)}</p>
        <p><strong>Contact:</strong> {safe(job_form.hiring_email)} | {safe(job_form.contact_phone)}</p>
    </body>
    </html>
    """

    return html.strip()
