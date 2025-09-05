import requests
from django.utils.text import slugify

from job.models import JobTask



def get_or_create_category(wp_conn, slug, name=None, description=""):
    """
    Ensures the category with the given slug exists. Creates if it doesn't.
    """
    headers = {
        'Authorization': f'Basic {wp_conn.access_token}',
        'Content-Type': 'application/json',
    }

    # 1. Try to GET the category
    response = requests.get(
        f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/categories?slug={slug}",
        headers=headers,
    )

    if response.status_code == 200:
        categories = response.json()
        if categories:
            return categories[0]['id']

    # 2. Create the category
    data = {
        "name": name or slug.capitalize(),
        "slug": slug,
        "description": description
    }

    response = requests.post(
        f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/categories",
        headers=headers,
        json=data
    )

    if response.status_code in [200, 201]:
        return response.json()['id']
    else:
        raise Exception(f"❌ Failed to create '{slug}' category: {response.text}")

import re

def upload_job_post_to_wordpress(job_form, wp_conn, html_content,api_payload, job_task ):
    wp_conn = wp_conn

        # Prefer AI request payload if available (more reliable than free-text AI response)
    if api_payload:
        route = api_payload.get("route", "OTR")
        position = api_payload.get("position", "Driver")
        equipment = api_payload.get("hauling", "General Freight")
        pay_structure = api_payload.get("pay_structure", "Pay Not Specified")
        pay_value = api_payload.get("pay_type", "N/A")
    else:
        # Fallback to job_form if payload missing
        route = "OTR"
        position = "Company Driver"
        equipment = job_form.hauling_equipment or "General Freight"
        if job_form.cpm:
            pay_structure = f"{job_form.cpm} CPM"
            pay_value = f"${job_form.cpm}/mile"
        elif job_form.driver_percentage:
            pay_structure = f"{job_form.driver_percentage}% of load"
            pay_value = f"{job_form.driver_percentage}%"
        else:
            pay_structure = "Pay Not Specified"
            pay_value = "N/A"
    # title = f"{job_form.company_name} - Hiring CDL Drivers"
    title = f"{route.upper()} {position} – {equipment} – {pay_structure} – {pay_value}"
    map_html = generate_map_html(api_payload)

        # POST-PROCESSING: Clean up the HTML content for local routes
    hiring_area = api_payload.get("hiring_area", {})
    route_type = hiring_area.get("type", "").lower()

    if route_type == "local":
        # Simple string replacement for the exact pattern
        html_content = html_content.replace('HIRING FROM:<br>+ Regions: <br>States:', '')

    elif route_type == "otr":
    # For OTR routes, remove only the empty "States:" line but keep "HIRING FROM: + Regions: USA"
        html_content = html_content.replace('States:', '')  # Remove just the States label

        
        # ADD COST STRUCTURE TO HTML CONTENT IF AVAILABLE
     # ADD COST STRUCTURE TO HTML CONTENT AFTER DRIVER BENEFITS SECTION
    cost_structure = api_payload.get("cost_structure")
    if cost_structure:
        cost_html = f"""
        <h2>{cost_structure['title']}</h2>
        """
        
        # Add service fee info
        if cost_structure.get("service_fee"):
            cost_html += f"<p><strong>{cost_structure['service_fee']} COMPANY SERVICE FEE INCLUDES:</strong></p>"
            if cost_structure.get("service_fee_includes"):
                cost_html += "<ul>"
                for item in cost_structure["service_fee_includes"]:
                    cost_html += f"<li>{item}</li>"
                cost_html += "</ul>"
        
        # Add weekly expenses
        if cost_structure.get("weekly_expenses"):
            cost_html += "<p><strong>WEEKLY EXPENSES:</strong></p><ul>"
            for expense in cost_structure["weekly_expenses"]:
                cost_html += f"<li>{expense}</li>"
            cost_html += "</ul>"
        
        # Insert cost structure after DRIVER BENEFITS section
        # Look for the DRIVER BENEFITS section in the HTML
        benefits_pattern = "DRIVER BENEFITS:"
        benefits_index = html_content.find(benefits_pattern)
        
        if benefits_index != -1:
            # Find the end of the DRIVER BENEFITS section
            # Look for the next section header (all caps followed by colon)
            import re
            next_section_match = re.search(r'<br>[A-Z\s]+:', html_content[benefits_index:])
            
            if next_section_match:
                # Insert after DRIVER BENEFITS section but before next section
                insert_index = benefits_index + next_section_match.start()
                html_content = html_content[:insert_index] + cost_html + html_content[insert_index:]
            else:
                # If no next section found, insert at the end of DRIVER BENEFITS
                # Find the end of the list items
                ul_end_pattern = "</ul>"
                ul_end_index = html_content.find(ul_end_pattern, benefits_index)
                
                if ul_end_index != -1:
                    # Insert after the closing </ul> of benefits
                    insert_index = ul_end_index + len(ul_end_pattern)
                    html_content = html_content[:insert_index] + cost_html + html_content[insert_index:]
                else:
                    # Fallback: insert after DRIVER BENEFITS text
                    insert_index = benefits_index + len(benefits_pattern)
                    html_content = html_content[:insert_index] + cost_html + html_content[insert_index:]
        else:
            # Fallback: append to end if DRIVER BENEFITS section not found
            html_content += cost_html

    category_id = get_or_create_category(wp_conn, slug="jobs", name="Jobs", description="Trucking job listings")

    slug = slugify(title)
    post_data = {
        "title": title,
        "slug": slug,
        "content": f"<div>{html_content}</div>{map_html}",
        # "content": f"<div>{html_content}</div>",
        "status": "publish",
        "categories": [category_id], 
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
    
    response_data = response.json()
    page_url = response_data.get('link') # This is the published URL
    post_id = response_data.get('id')

    # Update the JobTask with the URL and publish date
    job_task.wp_page_url = page_url
    job_task.published_date = timezone.now()
    job_task.save()

    logger.info(f"✅ Job Post uploaded to WordPress. URL: {page_url}")
    return page_url



def generate_map_html(api_payload):
    """
    Generate USA map HTML based on route type and hiring area.
    - Local: radius only, no map
    - Regional: highlight states on USA map
    - OTR: show full USA map
    """
    route = api_payload.get("route", "").lower()
    hiring_area = api_payload.get("hiring_area", {})
    states = hiring_area.get("states", [])
    radius = hiring_area.get("radius")
    route_type = hiring_area.get("type", "").lower()

    effective_route = route_type if route_type else route
    # Local → no map, just radius text
    if effective_route  == "local" and radius:
        return f"<p><strong>Hiring Radius:</strong> Within {radius} miles</p>"

    # Regional → highlight specific states
    if effective_route  == "regional" and states:
        states_js = ",".join([f'"{s}"' for s in states])
        return f"""
        <div id="regional-map" style="width: 100%; height: 500px;"></div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.3/d3.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/topojson/1.6.9/topojson.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/datamaps/0.5.9/datamaps.usa.min.js"></script>
        <script>
        var states = [{states_js}];
        var map = new Datamap({{
            element: document.getElementById('regional-map'),
            scope: 'usa',
            fills: {{
                defaultFill: '#D6DBDF',
                highlight: '#2E86C1'
            }},
            data: states.reduce((acc, s) => {{
                acc[s] = {{ fillKey: 'highlight' }};
                return acc;
            }}, {{}})
        }});
        </script>
        """

    # OTR → full USA map
    if effective_route  == "otr":
        return """
        <div id="otr-map" style="width: 100%; height: 500px;"></div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.3/d3.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/topojson/1.6.9/topojson.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/datamaps/0.5.9/datamaps.usa.min.js"></script>
        <script>
        var map = new Datamap({
            element: document.getElementById('otr-map'),
            scope: 'usa',
            fills: { defaultFill: '#2E86C1' }
        });
        </script>
        """

    return ""




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
import logging
from django.utils import timezone
logger = logging.getLogger(__name__)

def create_initial_job_blog_task(user, job_onboarding):
    onboarding_form = user.onboardingform.last()  # get the latest
    if not onboarding_form or not onboarding_form.package:
        return None
    
    package = onboarding_form.package 
    current_month = timezone.now().strftime("%Y-%m")
    
    task = JobTask.objects.create(
        user=user,
        job_onboarding=job_onboarding,
        task_type='job_blog_writing',
        next_run=timezone.now(),
        status='pending',
        count_this_month=0,
        month_year=current_month,
        is_active=True
    )
    
    logger.info(f"✅ Initial job blog task created for user {user.email}")
    return task



def map_cost_structure(job_form):
    """Map cost breakdown based on driving position"""
    position = (job_form.position or "").lower().strip()

    cost_section = {
        "title": "",
        "service_fee": None,
        "service_fee_includes": job_form.service_fee_includes or [],
        "weekly_expenses": []
    }

    # --- Owner Operator ---
    if position == "owner operator":
        cost_section["title"] = "Owner-Operator Cost Breakdown"
        cost_section["service_fee"] = f"{job_form.company_service_fee}%"

        if job_form.trailer_rent:
            cost_section["weekly_expenses"].append(f"TRAILER RENT – ${job_form.trailer_rent}/WEEK")

        if job_form.insurance_physical_damage:
            cost_section["weekly_expenses"].append(f"PHYSICAL DAMAGE INSURANCE – ${job_form.insurance_physical_damage}/WEEK")

        if job_form.insurance_liability_cargo:
            cost_section["weekly_expenses"].append(f"LIABILITY & CARGO INSURANCE – ${job_form.insurance_liability_cargo}/WEEK")

        if job_form.ifta_fee:
            cost_section["weekly_expenses"].append(f"IFTA – ${job_form.ifta_fee}/WEEK")

        if job_form.tablet_cost:
            if job_form.tablet_cost.lower() == "driver":
                cost_section["weekly_expenses"].append("TABLET & DATA – DRIVER PROVIDED")
            else:
                cost_section["weekly_expenses"].append(f"TABLET & DATA – ${job_form.tablet_cost}/WEEK")

        if job_form.tolls_fuel:
            cost_section["weekly_expenses"].append(f"{job_form.tolls_fuel}")
        else:
            cost_section["weekly_expenses"].append("TOLLS & FUEL")


    # --- Lease-to-Rent ---
    elif position == "lease-to-rent":
        cost_section["title"] = "Lease-To-Rent Cost Breakdown"
        cost_section["service_fee"] = "$500 FIXED"

        if job_form.truck_lease_weekly:
            cost_section["weekly_expenses"].append(f"TRUCK LEASE – ${job_form.truck_lease_weekly}/WEEK")

        if job_form.trailer_rent:
            cost_section["weekly_expenses"].append(f"TRAILER RENT – ${job_form.trailer_rent}/WEEK")

        if job_form.insurance_physical_damage:
            cost_section["weekly_expenses"].append(f"PHYSICAL DAMAGE INSURANCE – ${job_form.insurance_physical_damage}/WEEK")

        if job_form.insurance_liability_cargo:
            cost_section["weekly_expenses"].append(f"LIABILITY & CARGO INSURANCE – ${job_form.insurance_liability_cargo}/WEEK")

        if job_form.ifta_fee:
            cost_section["weekly_expenses"].append(f"IFTA – ${job_form.ifta_fee}/WEEK")

        if job_form.tablet_cost:
            if job_form.tablet_cost.lower() == "driver":
                cost_section["weekly_expenses"].append("TABLET & DATA – DRIVER PROVIDED")
            else:
                cost_section["weekly_expenses"].append(f"TABLET & DATA – ${job_form.tablet_cost}/WEEK")

        if job_form.tolls_fuel:
            cost_section["weekly_expenses"].append(f"{job_form.tolls_fuel}")
        else:
            cost_section["weekly_expenses"].append("TOLLS & FUEL")


    # --- Lease-to-Purchase ---
    elif position == "lease-to-purchase":
        cost_section["title"] = "Lease-To-Purchase Cost Breakdown"
        cost_section["service_fee"] = "$500 FIXED"

        if job_form.truck_lease_weekly:
            cost_section["weekly_expenses"].append(f"TRUCK LEASE – ${job_form.truck_lease_weekly}/WEEK")

        if job_form.trailer_rent:
            cost_section["weekly_expenses"].append(f"TRAILER RENT – ${job_form.trailer_rent}/WEEK")

        if job_form.insurance_physical_damage:
            cost_section["weekly_expenses"].append(f"PHYSICAL DAMAGE INSURANCE – ${job_form.insurance_physical_damage}/WEEK")

        if job_form.insurance_liability_cargo:
            cost_section["weekly_expenses"].append(f"LIABILITY & CARGO INSURANCE – ${job_form.insurance_liability_cargo}/WEEK")

        if job_form.ifta_fee:
            cost_section["weekly_expenses"].append(f"IFTA – ${job_form.ifta_fee}/WEEK")

        if job_form.tablet_cost:
            if job_form.tablet_cost.lower() == "driver":
                cost_section["weekly_expenses"].append("TABLET & DATA – DRIVER PROVIDED")
            else:
                cost_section["weekly_expenses"].append(f"TABLET & DATA – ${job_form.tablet_cost}/WEEK")

        if job_form.down_payment:
            cost_section["weekly_expenses"].append(f"DOWN PAYMENT – ${job_form.down_payment}")
        if job_form.tolls_fuel:
            cost_section["weekly_expenses"].append(f"{job_form.tolls_fuel}")
        else:
            cost_section["weekly_expenses"].append("TOLLS & FUEL")

    return cost_section
