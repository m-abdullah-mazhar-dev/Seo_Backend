import requests
from django.utils.text import slugify

from g_matrix.google_service import build_service
from g_matrix.models import SearchConsoleToken
from job.models import JobBlogKeyword, JobTask



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


# def upload_job_post_to_wordpress(job_form, wp_conn, html_content, api_payload, page_id=None, job_template=None):
#     wp_conn = wp_conn

#     # Prefer AI request payload if available
#     if api_payload:
#         route = api_payload.get("route", "OTR")
#         position = api_payload.get("position", "Driver")
#         equipment = api_payload.get("hauling", "General Freight")
#         pay_structure = api_payload.get("pay_structure", "Pay Not Specified")
#         pay_value = api_payload.get("pay_type", "N/A")
#     else:
#         # Fallback to job_form if payload missing
#         route = "OTR"
#         position = "Company Driver"
#         equipment = job_form.hauling_equipment or "General Freight"
#         if job_form.cpm:
#             pay_structure = f"{job_form.cpm} CPM"
#             pay_value = f"${job_form.cpm}/mile"
#         elif job_form.driver_percentage:
#             pay_structure = f"{job_form.driver_percentage}% of load"
#             pay_value = f"{job_form.driver_percentage}%"
#         else:
#             pay_structure = "Pay Not Specified"
#             pay_value = "N/A"
    
#     title = f"{route.upper()} {position} – {equipment} – {pay_structure} – {pay_value}"
#     map_html = generate_map_html(api_payload)

#     # POST-PROCESSING: Clean up the HTML content for local routes
#     hiring_area = api_payload.get("hiring_area", {})
#     route_type = hiring_area.get("type", "").lower()

#     if route_type == "local":
#         html_content = html_content.replace('HIRING FROM:<br>+ Regions: <br>States:', '')
#     elif route_type == "otr":
#         html_content = html_content.replace('States:', '')

#     # ADD COST STRUCTURE TO HTML CONTENT IF AVAILABLE
#     cost_structure = api_payload.get("cost_structure")
#     if cost_structure:
#         cost_html = f"""
#         <h2>{cost_structure['title']}</h2>
#         """
        
#         # Add service fee info
#         if cost_structure.get("service_fee"):
#             cost_html += f"<p><strong>{cost_structure['service_fee']} COMPANY SERVICE FEE INCLUDES:</strong></p>"
#             if cost_structure.get("service_fee_includes"):
#                 cost_html += "<ul>"
#                 for item in cost_structure["service_fee_includes"]:
#                     cost_html += f"<li>{item}</li>"
#                 cost_html += "</ul>"
        
#         # Add weekly expenses
#         if cost_structure.get("weekly_expenses"):
#             cost_html += "<p><strong>WEEKLY EXPENSES:</strong></p><ul>"
#             for expense in cost_structure["weekly_expenses"]:
#                 cost_html += f"<li>{expense}</li>"
#             cost_html += "</ul>"
        
#         # Insert cost structure after DRIVER BENEFITS section
#         benefits_pattern = "DRIVER BENEFITS:"
#         benefits_index = html_content.find(benefits_pattern)
        
#         if benefits_index != -1:
#             # Find the end of the DRIVER BENEFITS section
#             import re
#             next_section_match = re.search(r'<br>[A-Z\s]+:', html_content[benefits_index:])
            
#             if next_section_match:
#                 insert_index = benefits_index + next_section_match.start()
#                 html_content = html_content[:insert_index] + cost_html + html_content[insert_index:]
#             else:
#                 ul_end_pattern = "</ul>"
#                 ul_end_index = html_content.find(ul_end_pattern, benefits_index)
                
#                 if ul_end_index != -1:
#                     insert_index = ul_end_index + len(ul_end_pattern)
#                     html_content = html_content[:insert_index] + cost_html + html_content[insert_index:]
#                 else:
#                     insert_index = benefits_index + len(benefits_pattern)
#                     html_content = html_content[:insert_index] + cost_html + html_content[insert_index:]
#         else:
#             html_content += cost_html

#     category_id = get_or_create_category(wp_conn, slug="jobs", name="Jobs", description="Trucking job listings")

#     slug = slugify(title)
#     post_data = {
#         "title": title,
#         "slug": slug,
#         "content": f"<div>{html_content}</div>{map_html}",
#         "status": "publish",
#         "categories": [category_id], 
#     }

#     headers = {
#         'Authorization': f'Basic {wp_conn.access_token}',
#         'Content-Type': 'application/json',
#     }

#     # Determine the API endpoint based on whether we're creating or updating
#     if page_id:
#         # Update existing post
#         endpoint = f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/posts/{page_id}"
#         response = requests.put(endpoint, headers=headers, json=post_data)
#     else:
#         # Create new post
#         endpoint = f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/posts"
#         response = requests.post(endpoint, headers=headers, json=post_data)

#     if response.status_code not in [200, 201]:
#         raise Exception(f"WordPress {'update' if page_id else 'upload'} failed: {response.text}")
    
#     response_data = response.json()
#     page_url = response_data.get('link')  # This is the published URL
#     post_id = response_data.get('id')

#     # Store the WordPress post ID for future updates
#     if job_template and not job_template.wp_page_id and post_id:
#         job_template.wp_page_id = post_id
#         job_template.save()

#     logger.info(f"✅ Job Post {'updated' if page_id else 'uploaded'} to WordPress. URL: {page_url}")

#     return page_url

def upload_job_post_to_wordpress(job_form, wp_conn, html_content, api_payload, page_id=None, job_template=None):
    wp_conn = wp_conn

    # BUILD TITLE DIRECTLY FROM JOB FORM ONLY (the only change needed)
    route = getattr(job_form, 'route', '')
    position = getattr(job_form, 'position', '')
    equipment = getattr(job_form, 'hauling_equipment', '')
    
    # Format the components
    route_display = route.upper() if route else "OTR"
    position_display = position.replace('_', ' ').title() if position else "Driver"
    equipment_display = equipment.title() if equipment else "General Freight"
    
    # Determine pay information from form data
    if job_form.cpm:
        pay_display = f"{job_form.cpm} CPM"
    elif job_form.driver_percentage:
        pay_display = f"{job_form.driver_percentage}% of Load"
    elif job_form.drivers_weekly_earning:
        pay_display = f"${job_form.drivers_weekly_earning}/week"
    else:
        pay_display = "Pay Not Specified"
    
    # Build the title from form data
    title_components = [
        route_display,
        position_display, 
        equipment_display,
        pay_display
    ]
    
    # Remove any empty components and join with dashes
    title_components = [comp for comp in title_components if comp and comp.strip()]
    title = " – ".join(title_components)

    # REST OF THE FUNCTION REMAINS EXACTLY THE SAME AS ORIGINAL
    map_html = generate_map_html(api_payload)

    # POST-PROCESSING: Clean up the HTML content for local routes
    hiring_area = api_payload.get("hiring_area", {})
    route_type = hiring_area.get("type", "").lower()

    if route_type == "local":
        html_content = html_content.replace('HIRING FROM:<br>+ Regions: <br>States:', '')
    elif route_type == "otr":
        html_content = html_content.replace('States:', '')

    # ADD COST STRUCTURE TO HTML CONTENT IF AVAILABLE
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
        benefits_pattern = "DRIVER BENEFITS:"
        benefits_index = html_content.find(benefits_pattern)
        
        if benefits_index != -1:
            # Find the end of the DRIVER BENEFITS section
            import re
            next_section_match = re.search(r'<br>[A-Z\s]+:', html_content[benefits_index:])
            
            if next_section_match:
                insert_index = benefits_index + next_section_match.start()
                html_content = html_content[:insert_index] + cost_html + html_content[insert_index:]
            else:
                ul_end_pattern = "</ul>"
                ul_end_index = html_content.find(ul_end_pattern, benefits_index)
                
                if ul_end_index != -1:
                    insert_index = ul_end_index + len(ul_end_pattern)
                    html_content = html_content[:insert_index] + cost_html + html_content[insert_index:]
                else:
                    insert_index = benefits_index + len(benefits_pattern)
                    html_content = html_content[:insert_index] + cost_html + html_content[insert_index:]
        else:
            html_content += cost_html

    category_id = get_or_create_category(wp_conn, slug="jobs", name="Jobs", description="Trucking job listings")

    slug = slugify(title)
    post_data = {
        "title": title,
        "slug": slug,
        "content": f"<div>{html_content}</div>{map_html}",
        "status": "publish",
        "categories": [category_id], 
    }

    headers = {
        'Authorization': f'Basic {wp_conn.access_token}',
        'Content-Type': 'application/json',
    }

    # Determine the API endpoint based on whether we're creating or updating
    if page_id:
        # Update existing post
        endpoint = f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/posts/{page_id}"
        response = requests.put(endpoint, headers=headers, json=post_data)
    else:
        # Create new post
        endpoint = f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/posts"
        response = requests.post(endpoint, headers=headers, json=post_data)

    if response.status_code not in [200, 201]:
        raise Exception(f"WordPress {'update' if page_id else 'upload'} failed: {response.text}")
    
    response_data = response.json()
    page_url = response_data.get('link')  # This is the published URL
    post_id = response_data.get('id')

    # Store the WordPress post ID for future updates
    if job_template and not job_template.wp_page_id and post_id:
        job_template.wp_page_id = post_id
        job_template.save()

    logger.info(f"✅ Job Post {'updated' if page_id else 'uploaded'} to WordPress. URL: {page_url}")

    return page_url


def fix_html_content_issues(html_content, job_form, api_payload):
    """Fix common issues in the generated HTML content"""
    
    # Fix percentage display in cost structure
    if "250.00% COMPANY SERVICE FEE" in html_content:
        html_content = html_content.replace("250.00% COMPANY SERVICE FEE", "$250.00 COMPANY SERVICE FEE")
    
    # Fix truck fleet information
    truck_make_year = getattr(job_form, 'truck_make_year', '')
    if "FLEET INCLUDES 2020" in html_content and truck_make_year:
        html_content = html_content.replace("FLEET INCLUDES 2020", f"FLEET INCLUDES {truck_make_year}")
    
    # Fix governed speed
    governed_speed = getattr(job_form, 'truck_governed_speed', '')
    if "TRUCKS GOVERNED AT 70" in html_content and governed_speed:
        html_content = html_content.replace("TRUCKS GOVERNED AT 70", f"TRUCKS GOVERNED AT {governed_speed} MPH")
    
    # Fix referral bonus formatting
    if "REFERRAL BONUS – 500" in html_content:
        referral_bonus = getattr(job_form, 'referral_bonus_amount', '')
        if referral_bonus:
            html_content = html_content.replace("REFERRAL BONUS – 500", f"REFERRAL BONUS – ${referral_bonus}")
        else:
            html_content = html_content.replace("REFERRAL BONUS – 500", "REFERRAL BONUS AVAILABLE")
    
    # Fix home time formatting
    home_time_list = getattr(job_form, 'home_time', [])
    if home_time_list and "HOME TIME:" in html_content:
        home_time_html = "HOME TIME:<br>"
        for item in home_time_list:
            home_time_html += f"● {item}<br>"
        # Replace the entire HOME TIME section
        import re
        home_time_pattern = r'HOME TIME:.*?(?=<br>[A-Z]|</div>|$)'
        html_content = re.sub(home_time_pattern, home_time_html.strip(), html_content, flags=re.DOTALL)
    
    # Fix equipment section to show all equipment
    equipment_benefits = []
    if getattr(job_form, 'equip_fridge', False):
        equipment_benefits.append("FRIDGES")
    if getattr(job_form, 'equip_inverter', False):
        equipment_benefits.append("INVERTERS")
    if getattr(job_form, 'equip_microwave', False):
        equipment_benefits.append("MICROWAVES")
    if getattr(job_form, 'equip_led', False):
        equipment_benefits.append("LED LIGHTING")
    if getattr(job_form, 'equip_apu', False):
        equipment_benefits.append("APU")
    
    if equipment_benefits and "EQUIPMENT:" in html_content:
        equipment_html = "EQUIPMENT:<br>"
        for item in equipment_benefits:
            equipment_html += f"● {item}<br>"
        # Replace the entire EQUIPMENT section
        equipment_pattern = r'EQUIPMENT:.*?(?=<br>[A-Z]|</div>|$)'
        html_content = re.sub(equipment_pattern, equipment_html.strip(), html_content, flags=re.DOTALL)
    
    # Fix company info section
    company_name = getattr(job_form, 'company_name', '')
    if "📢 Barlow and Marks Co" in html_content and company_name:
        html_content = html_content.replace("📢 Barlow and Marks Co", f"📢 {company_name}")
    
    # Fix MC/DOT number display
    mc_dot = getattr(job_form, 'mc_dot_number', '')
    if "🆔 915 /" in html_content and mc_dot:
        html_content = html_content.replace("🆔 915 /", f"🆔 {mc_dot}")
    
    return html_content

# from .views import map_job_form_to_api_payload

# def upload_job_post_to_wordpress(job_form, wp_conn, html_content, api_payload=None):
#     # Use api_payload if provided, otherwise fallback to job_form data
#     if not api_payload:
#         api_payload = map_job_form_to_api_payload(job_form)
    
#     route = api_payload.get("route", "OTR")
#     position = api_payload.get("position", "Driver")
#     equipment = api_payload.get("hauling", "General Freight")
#     pay_structure = api_payload.get("pay_structure", "Pay Not Specified")
#     pay_value = api_payload.get("pay_type", "N/A")
    
#     title = f"{route.upper()} {position} – {equipment} – {pay_structure} – {pay_value}"
#     map_html = generate_map_html(api_payload)

#     # POST-PROCESSING: Clean up the HTML content for local routes
#     hiring_area = api_payload.get("hiring_area", {})
#     route_type = hiring_area.get("type", "").lower()

#     if route_type == "local":
#         html_content = html_content.replace('HIRING FROM:<br>+ Regions: <br>States:', '')
#     elif route_type == "otr":
#         html_content = html_content.replace('States:', '')

#     # ADD COST STRUCTURE TO HTML CONTENT IF AVAILABLE
#     cost_structure = api_payload.get("cost_structure")
#     if cost_structure:
#         cost_html = f"""
#         <h2>{cost_structure['title']}</h2>
#         """
        
#         # Add service fee info
#         if cost_structure.get("service_fee"):
#             cost_html += f"<p><strong>{cost_structure['service_fee']} COMPANY SERVICE FEE INCLUDES:</strong></p>"
#             if cost_structure.get("service_fee_includes"):
#                 cost_html += "<ul>"
#                 for item in cost_structure["service_fee_includes"]:
#                     cost_html += f"<li>{item}</li>"
#                 cost_html += "</ul>"
        
#         # Add weekly expenses
#         if cost_structure.get("weekly_expenses"):
#             cost_html += "<p><strong>WEEKLY EXPENSES:</strong></p><ul>"
#             for expense in cost_structure["weekly_expenses"]:
#                 cost_html += f"<li>{expense}</li>"
#             cost_html += "</ul>"
        
#         # Insert cost structure after DRIVER BENEFITS section
#         benefits_pattern = "DRIVER BENEFITS:"
#         benefits_index = html_content.find(benefits_pattern)
        
#         if benefits_index != -1:
#             # Find the end of the DRIVER BENEFITS section
#             import re
#             next_section_match = re.search(r'<br>[A-Z\s]+:', html_content[benefits_index:])
            
#             if next_section_match:
#                 insert_index = benefits_index + next_section_match.start()
#                 html_content = html_content[:insert_index] + cost_html + html_content[insert_index:]
#             else:
#                 ul_end_pattern = "</ul>"
#                 ul_end_index = html_content.find(ul_end_pattern, benefits_index)
                
#                 if ul_end_index != -1:
#                     insert_index = ul_end_index + len(ul_end_pattern)
#                     html_content = html_content[:insert_index] + cost_html + html_content[insert_index:]
#                 else:
#                     insert_index = benefits_index + len(benefits_pattern)
#                     html_content = html_content[:insert_index] + cost_html + html_content[insert_index:]
#         else:
#             html_content += cost_html

#     category_id = get_or_create_category(wp_conn, slug="jobs", name="Jobs", description="Trucking job listings")

#     slug = slugify(title)
#     post_data = {
#         "title": title,
#         "slug": slug,
#         "content": f"<div>{html_content}</div>{map_html}",
#         "status": "publish",
#         "categories": [category_id], 
#     }

#     headers = {
#         'Authorization': f'Basic {wp_conn.access_token}',
#         'Content-Type': 'application/json',
#     }

#     response = requests.post(
#         f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/posts",
#         headers=headers,
#         json=post_data
#     )

#     if response.status_code not in [200, 201]:
#         raise Exception(f"WordPress upload failed: {response.text}")
    
#     response_data = response.json()
#     page_url = response_data.get('link')
    
#     logger.info(f"✅ Job Post uploaded to WordPress. URL: {page_url}")

#     return page_url


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
from datetime import datetime, timedelta

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
        # cost_section["service_fee"] = f"{job_form.company_service_fee}%"
        if job_form.company_service_fee:
            cost_section["service_fee"] = f"${job_form.company_service_fee}"

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
        # cost_section["service_fee"] = f"{job_form.company_service_fee}%"
        if job_form.company_service_fee:
            cost_section["service_fee"] = f"${job_form.company_service_fee}"

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
        # cost_section["service_fee"] = f"{job_form.company_service_fee}%"
        if job_form.company_service_fee:
            cost_section["service_fee"] = f"${job_form.company_service_fee}"

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
            cost_section["weekly_expenses"].append(f"DOWN PAYMENT – ${job_form.down_payment_amount}")
        if job_form.tolls_fuel:
            cost_section["weekly_expenses"].append(f"{job_form.tolls_fuel}")
        else:
            cost_section["weekly_expenses"].append("TOLLS & FUEL")

    return cost_section

# With proper HTML conversion:
def convert_template_to_html(job_template):
    """
    Convert markdown-like template to proper HTML
    """
    # First, handle bold text (**text**)
    html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', job_template)
    
    # Handle bullet points (* item)
    html_content = re.sub(r'\*\s+(.*?)(?=\n|$)', r'<li>\1</li>', html_content)
    
    # Wrap bullet points in <ul>
    if '<li>' in html_content:
        html_content = html_content.replace('<li>', '<ul><li>', 1)
        html_content += '</ul>'
    
    # Handle line breaks
    html_content = html_content.replace('\n', '<br>')
    
    return f"<div>{html_content}</div>"


import re

def process_job_template_html(job_template):
    """
    Properly convert job template markdown to HTML
    """
    if not job_template:
        return "<div></div>"
    
    # Convert **bold** to <strong>
    html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', job_template)
    
    # Convert * bullet points to list items
    lines = html_content.split('\n')
    in_list = False
    processed_lines = []
    
    for line in lines:
        # Check if this line is a bullet point
        if line.strip().startswith('* ') and len(line.strip()) > 2:
            if not in_list:
                processed_lines.append('<ul>')
                in_list = True
            # Remove the asterisk and add list item
            list_item = line.replace('* ', '').strip()
            processed_lines.append(f'<li>{list_item}</li>')
        else:
            if in_list:
                processed_lines.append('</ul>')
                in_list = False
            processed_lines.append(line)
    
    # Close list if still open
    if in_list:
        processed_lines.append('</ul>')
    
    # Join lines with proper line breaks
    html_content = '<br>'.join(processed_lines)
    
    return f"<div>{html_content}</div>"



from django.utils import timezone
from django.core import serializers
import json

def sync_job_keywords(user):
    """
    Fetches Search Console data for all keywords linked to a user's job blogs
    and updates their metrics. Returns the updated keyword data.
    """
    try:
        # 1. Get the user's Search Console token
        try:
            token = SearchConsoleToken.objects.get(user=user)
        except SearchConsoleToken.DoesNotExist:
            return {"error": "Search Console token not found"}

        # 2. Get all keywords for this user's job blogs
        user_keywords = JobBlogKeyword.objects.filter(job_blog__job_task__user=user)
        if not user_keywords.exists():
            return {"message": "No keywords found for user's job blogs."}

        # Create a lookup dictionary: keyword_lowercase -> Model Instance
        keyword_map = {k.keyword.lower(): k for k in user_keywords}
        print(f"Keywords to sync for user {user.email}: {list(keyword_map.keys())}")

        # 3. Build the service and query GSC
        service = build_service(token.credentials)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30) # Last 30 days

        response = service.searchanalytics().query(
            siteUrl=token.site_url,
            body={
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['query'], # This is the key - we want data by query (keyword)
                'rowLimit': 5000,
            }
        ).execute()

        # 4. Process the response and update the keyword models
        updated_keywords = []
        updated_count = 0
        
        for row in response.get('rows', []):
            query = row['keys'][0].lower() # The search query from GSC
            if query in keyword_map:
                keyword_obj = keyword_map[query]
                keyword_obj.clicks = row.get('clicks', 0)
                keyword_obj.impressions = row.get('impressions', 0)
                keyword_obj.ctr = row.get('ctr', 0)
                keyword_obj.average_position = row.get('position', 0)
                keyword_obj.last_updated = timezone.now()
                keyword_obj.save()
                updated_count += 1
                
                # Store the updated data for response
                updated_keywords.append({
                    'id': keyword_obj.id,
                    'keyword': keyword_obj.keyword,
                    'clicks': keyword_obj.clicks,
                    'impressions': keyword_obj.impressions,
                    'ctr': keyword_obj.ctr,
                    'average_position': keyword_obj.average_position,
                    'last_updated': keyword_obj.last_updated.isoformat() if keyword_obj.last_updated else None,
                    'blog_title': keyword_obj.job_blog.title,
                    'blog_url': keyword_obj.job_blog.wp_post_url
                })
                
                print(f"Updated '{query}': {keyword_obj.clicks} clicks")

        # 5. Also include keywords that were processed but had no data in GSC
        all_processed_keywords = []
        for keyword_obj in user_keywords:
            keyword_data = {
                'id': keyword_obj.id,
                'keyword': keyword_obj.keyword,
                'clicks': keyword_obj.clicks,
                'impressions': keyword_obj.impressions,
                'ctr': keyword_obj.ctr,
                'average_position': keyword_obj.average_position,
                'last_updated': keyword_obj.last_updated.isoformat() if keyword_obj.last_updated else None,
                'blog_title': keyword_obj.job_blog.title,
                'blog_url': keyword_obj.job_blog.wp_post_url,
                'has_data_in_gsc': keyword_obj.keyword.lower() in [k['keyword'].lower() for k in updated_keywords]
            }
            all_processed_keywords.append(keyword_data)

        return {
            "status": "success",
            "message": f"Synced GSC data for {updated_count} keywords",
            "details": {
                "user": user.email,
                "total_keywords_processed": len(user_keywords),
                "keywords_with_data": updated_count,
                "time_period": f"{start_date} to {end_date}"
            },
            "keywords": all_processed_keywords  # This is the key addition!
        }

    except Exception as e:
        print(f"❌ Error in sync_job_keywords: {str(e)}")
        return {"error": str(e)}
    

import requests
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

# def fetch_wordpress_post_data(wp_connection, page_url):
#     """
#     WordPress se live post data fetch karta hai
#     """
#     try:
#         # Cache key banate hain for better performance
#         cache_key = f"wp_post_{hash(page_url)}"
#         cached_data = cache.get(cache_key)
#         if cached_data:
#             return cached_data
        
#         # Extract post ID from URL
#         if not page_url:
#             return None
            
#         # URL se post ID extract karte hain
#         url_parts = page_url.strip('/').split('/')
#         post_slug = url_parts[-1] if url_parts[-1] else url_parts[-2]
        
#         # WordPress API endpoint - slug se data fetch karte hain
#         api_url = f"{wp_connection.site_url.rstrip('/')}/wp-json/wp/v2/posts?slug={post_slug}"
        
#         headers = {
#             'Authorization': f'Basic {wp_connection.access_token}',
#             'Content-Type': 'application/json',
#         }
        
#         logger.info(f"Fetching WordPress data from: {api_url}")
        
#         response = requests.get(api_url, headers=headers, timeout=15)
        
#         if response.status_code == 200:
#             posts_data = response.json()
#             if posts_data and len(posts_data) > 0:
#                 post_data = posts_data[0]
#                 result = {
#                     'title': post_data.get('title', {}).get('rendered', ''),
#                     'content': post_data.get('content', {}).get('rendered', ''),
#                     'excerpt': post_data.get('excerpt', {}).get('rendered', ''),
#                     'status': post_data.get('status', ''),
#                     'date': post_data.get('date', ''),
#                     'modified': post_data.get('modified', '')
#                 }
                
#                 # 30 minutes ke liye cache karo
#                 cache.set(cache_key, result, 1800)
#                 return result
        
#         logger.warning(f"WordPress API returned status: {response.status_code}")
#         return None
            
#     except Exception as e:
#         logger.error(f"WordPress fetch error: {e}")
#         return None


# utils.py
import requests
from django.utils.html import strip_tags

def fetch_wordpress_post_data(wp_connection, post_url):
    """
    Fetch WordPress post data using the REST API
    """
    try:
        # Extract post ID or slug from URL
        from urllib.parse import urlparse
        parsed_url = urlparse(post_url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        if not path_parts:
            return None
        
        # Try to get by slug (last part of URL)
        slug = path_parts[-1]
        
        headers = {
            'Authorization': f'Basic {wp_connection.access_token}',
            'Content-Type': 'application/json',
        }
        
        # Try to get post by slug
        response = requests.get(
            f"{wp_connection.site_url.rstrip('/')}/wp-json/wp/v2/posts?slug={slug}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            posts = response.json()
            if posts and len(posts) > 0:
                return posts[0]
        
        return None
        
    except Exception as e:
        print(f"Error fetching WordPress post data: {e}")
        return None
    



import requests
import logging

logger = logging.getLogger(__name__)

def delete_wordpress_post(wp_conn, post_id):
    """
    Delete a WordPress post by ID
    """
    try:
        if not wp_conn or not post_id:
            logger.warning("Missing WordPress connection or post ID")
            return False
            
        headers = {
            'Authorization': f'Basic {wp_conn.access_token}',
            'Content-Type': 'application/json',
        }
        
        
        response = requests.delete(
            f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}",
            headers=headers,
            params={'force': 'false'}  
        )
        
        if response.status_code in [200, 202]:
            logger.info(f"✅ WordPress post {post_id} moved to trash successfully")
            return True
        else:

            response = requests.delete(
                f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}",
                headers=headers,
                params={'force': 'true'}  # Permanent delete
            )
            
            if response.status_code in [200, 202]:
                logger.info(f"✅ WordPress post {post_id} permanently deleted successfully")
                return True
            else:
                logger.error(f"❌ Failed to delete WordPress post {post_id}: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error deleting WordPress post {post_id}: {str(e)}")
        return False