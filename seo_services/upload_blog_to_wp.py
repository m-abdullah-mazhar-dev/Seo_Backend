from datetime import timezone
import requests
from bs4 import BeautifulSoup
from django.utils.text import slugify
import logging

from job.utility import get_or_create_category
logger = logging.getLogger(__name__)

# def upload_blog_to_wordpress(blog, wp_conn):
#     headers = {
#         'Authorization': f'Basic {wp_conn.access_token}',
#         'Content-Type': 'application/json',
#     }

#     # Get image URL from BlogImage
#     image_obj = blog.images.first()
#     image_url = image_obj.image_url if image_obj else None

#     # Get content and title
#     soup = BeautifulSoup(blog.content, 'html.parser')
#     title = soup.title.string.strip() if soup.title else blog.title
#     content_body = soup.body if soup.body else blog.content

#     content_html = str(content_body) if hasattr(content_body, 'prettify') else content_body
#     slug = slugify(title)

#     # Upload the blog post to WordPress
#     post_data = {
#         "title": title,
#         "slug": slug,
#         "content": f"<div>{content_html}</div>",
#         "status": "publish",
#     }

#     # Add featured media if image exists
#     if image_url:
#         media_headers = {
#             'Authorization': f'Basic {wp_conn.access_token}',
#             'Content-Disposition': f'attachment; filename={slug}.jpg',
#             'Content-Type': 'image/jpeg',
#         }

#         try:
#             img_data = requests.get(image_url).content
#             media_response = requests.post(
#                 f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/media",
#                 headers=media_headers,
#                 data=img_data
#             )

#             if media_response.status_code in [200, 201]:
#                 featured_media_id = media_response.json().get("id")
#                 post_data["featured_media"] = featured_media_id
#             else:
#                 print("⚠️ Image upload failed:", media_response.text)
#         except Exception as e:
#             print("❌ Exception during image upload:", str(e))

#     response = requests.post(
#         f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/posts",
#         headers=headers,
#         json=post_data
#     )

#     if response.status_code in [200, 201]:
#         print("✅ Blog uploaded to WordPress successfully.")
#     else:
#         print("❌ Failed to upload blog:", response.text)


def upload_blog_to_wordpress(blog, wp_conn,is_job_blog=False):
    logger.info("Starting blog upload process...")

    headers = {
        'Authorization': f'Basic {wp_conn.access_token}',
        'Content-Type': 'application/json',
    }
    logger.debug(f"Request headers prepared: {headers}")

    # # Get image URL from BlogImage
    # image_obj = blog.images.first()
    # image_url = image_obj.image_url if image_obj else None
    # logger.debug(f"Image URL extracted: {image_url}")

    image_url = None
    if is_job_blog:
        # For JobBlog, check if images relationship exists
        if hasattr(blog, 'images'):  # Try the related_name first
            image_obj = blog.images.first()
            image_url = image_obj.image_url if image_obj else None
        else:
            # Last resort: check if there's any JobBlogImage linked to this blog
            try:
                from .models import JobBlogImage
                image_obj = JobBlogImage.objects.filter(job_blog=blog).first()
                image_url = image_obj.image_url if image_obj else None
            except:
                image_url = None
    else:
        # For regular Blog, use the BlogImage relationship
        image_obj = blog.images.first() if hasattr(blog, 'images') else None
        image_url = image_obj.image_url if image_obj else None

    # Get content and title
    soup = BeautifulSoup(blog.content, 'html.parser')
    title = soup.title.string.strip() if soup.title else blog.title
    logger.debug(f"Blog title parsed: {title}")

    content_body = soup.body if soup.body else blog.content
    content_html = str(content_body) if hasattr(content_body, 'prettify') else content_body
    logger.debug("Blog content extracted.")

    slug = slugify(title)
    logger.debug(f"Slug generated: {slug}")
    # category_id = get_or_create_category(wp_conn, slug="blogs", name="Blogs", description="All blog articles")


    # Get or create category - you might want different categories for job blogs
    category_name = "Trucking Jobs" if is_job_blog else "Blogs"
    category_slug = "trucking-jobs" if is_job_blog else "blogs"
    category_id = get_or_create_category(wp_conn, slug=category_slug, name=category_name, description=f"{category_name} articles")

    # Upload the blog post to WordPress
    post_data = {
        "title": title,
        "slug": slug,
        "content": f"<div>{content_html}</div>",
        "status": "publish",
        "categories": [category_id], 
    }

    if image_url:
        logger.info("Uploading featured image to WordPress...")
        media_headers = {
            'Authorization': f'Basic {wp_conn.access_token}',
            'Content-Disposition': f'attachment; filename={slug}.jpg',
            'Content-Type': 'image/jpeg',
        }

        try:
            img_data = requests.get(image_url).content
            logger.debug(f"Fetched image data from: {image_url}")

            media_response = requests.post(
                f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/media",
                headers=media_headers,
                data=img_data
            )

            logger.debug(f"Image upload response: {media_response.status_code} - {media_response.text}")

            if media_response.status_code in [200, 201]:
                featured_media_id = media_response.json().get("id")
                post_data["featured_media"] = featured_media_id
                logger.info(f"Image uploaded. Media ID: {featured_media_id}")
            else:
                logger.warning(f"Image upload failed: {media_response.text}")
        except Exception as e:
            logger.exception(f"Exception during image upload: {e}")

    logger.info("Uploading blog post to WordPress...")
    response = requests.post(
        f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/posts",
        headers=headers,
        json=post_data
    )

    logger.debug(f"Post upload response: {response.status_code} - {response.text}")

    if response.status_code in [200, 201]:
        wp_post_id = response.json().get("id")
        # blog.wp_post_id = wp_post_id
        # blog.save()

        # Save WordPress ID to appropriate blog model
        if is_job_blog:
            blog.wp_post_id = wp_post_id
            blog.save()
        else:
            blog.wp_post_id = wp_post_id
            blog.save()
        logger.info(f"✅ Blog uploaded to WordPress successfully. wp_id: {wp_post_id}")
    else:
        logger.error(f"❌ Failed to upload blog: {response.text}")



# def upload_service_page_to_wordpress(service_page, optimized_html,service_name=None, area_name=None):
#     wp_conn = service_page.wordpress_connection
#     logger = logging.getLogger(__name__)

#     headers = {
#         'Authorization': f'Basic {wp_conn.access_token}',
#         'Content-Type': 'application/json',
#     }

#     # Parse title and content
#     soup = BeautifulSoup(optimized_html, "html.parser")
#     title = soup.title.string.strip() if soup.title else "Service Page"
#     content_body = soup.body if soup.body else optimized_html
#     content_html = str(content_body) if hasattr(content_body, 'prettify') else content_body

#     slug = slugify(title)

#     page_data = {
#         "title": title,
#         "slug": slug,
#         "content": f"<div>{content_html}</div>",
#         "status": "publish"
#     }

#     try:
#         # Upload or update page (naively assumes new upload)
#         response = requests.post(
#             f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/pages",
#             headers=headers,
#             json=page_data
#         )

#         logger.info(f"🔼 WordPress Page Upload Response: ")

#         if response.status_code in [200, 201]:
#             page_data = response.json()
#             final_url = page_data.get('link')
            
#             # Update the SEOTask with the WordPress URL
#             service_page.seo_tasks.filter(optimized_content=optimized_html).update(
#                 wp_page_url=final_url,
#                 last_metrics_update=timezone.now()
#             )
#             logger.info(f"✅ Service page uploaded to: {final_url}")
#             return final_url
#         else:
#             logger.error(f"❌ Failed to upload service page content: {response.text}")

#     except Exception as e:
#         logger.exception(f"❌ Exception during service page upload: {str(e)}")



def upload_service_page_to_wordpress(service_page, optimized_html, service_name=None, area_name=None):
    wp_conn = service_page.wordpress_connection
    logger = logging.getLogger(__name__)

    headers = {
        'Authorization': f'Basic {wp_conn.access_token}',
        'Content-Type': 'application/json',
    }

    # Parse title and content
    soup = BeautifulSoup(optimized_html, "html.parser")
    
    # Use custom title if service_name and area_name are provided
    if service_name and area_name:
        title = f"{service_name} in {area_name}"
    else:
        title = soup.title.string.strip() if soup.title else "Service Page"
    
    content_body = soup.body if soup.body else optimized_html
    content_html = str(content_body) if hasattr(content_body, 'prettify') else content_body

    # Create appropriate slug
    if service_name and area_name:
        slug = f"{slugify(service_name)}-in-{slugify(area_name)}"
    else:
        slug = slugify(title)

    page_data = {
        "title": title,
        "slug": slug,
        "content": f"<div>{content_html}</div>",
        "status": "publish"
    }

    try:
        # First check if page already exists with this slug
        check_response = requests.get(
            f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/pages?slug={slug}",
            headers=headers
        )
        
        if check_response.status_code == 200:
            existing_pages = check_response.json()
            if existing_pages:
                # Page exists, update it
                page_id = existing_pages[0]['id']
                response = requests.post(
                    f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/pages/{page_id}",
                    headers=headers,
                    json=page_data
                )
            else:
                # Page doesn't exist, create new
                response = requests.post(
                    f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/pages",
                    headers=headers,
                    json=page_data
                )
        else:
            # Fallback to creating new page
            response = requests.post(
                f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/pages",
                headers=headers,
                json=page_data
            )

        logger.info(f"🔼 WordPress Page Upload Response: {response.status_code}")

        if response.status_code in [200, 201]:
            page_data = response.json()
            final_url = page_data.get('link')
            logger.info(f"✅ Service page uploaded: {final_url}")
            return final_url
        else:
            logger.error(f"❌ Failed to upload service page content: {response.text}")
            return None

    except Exception as e:
        logger.exception(f"❌ Exception during service page upload: {str(e)}")
        return None