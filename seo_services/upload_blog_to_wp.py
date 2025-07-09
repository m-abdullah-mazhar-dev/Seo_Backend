import requests
from bs4 import BeautifulSoup
from django.utils.text import slugify
import logging
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


def upload_blog_to_wordpress(blog, wp_conn):
    logger.info("Starting blog upload process...")

    headers = {
        'Authorization': f'Basic {wp_conn.access_token}',
        'Content-Type': 'application/json',
    }
    logger.debug(f"Request headers prepared: {headers}")

    # Get image URL from BlogImage
    image_obj = blog.images.first()
    image_url = image_obj.image_url if image_obj else None
    logger.debug(f"Image URL extracted: {image_url}")

    # Get content and title
    soup = BeautifulSoup(blog.content, 'html.parser')
    title = soup.title.string.strip() if soup.title else blog.title
    logger.debug(f"Blog title parsed: {title}")

    content_body = soup.body if soup.body else blog.content
    content_html = str(content_body) if hasattr(content_body, 'prettify') else content_body
    logger.debug("Blog content extracted.")

    slug = slugify(title)
    logger.debug(f"Slug generated: {slug}")

    # Upload the blog post to WordPress
    post_data = {
        "title": title,
        "slug": slug,
        "content": f"<div>{content_html}</div>",
        "status": "publish",
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
        logger.info("✅ Blog uploaded to WordPress successfully.")
    else:
        logger.error(f"❌ Failed to upload blog: {response.text}")



def upload_service_page_to_wordpress(service_page, optimized_html):
    wp_conn = service_page.wordpress_connection
    logger = logging.getLogger(__name__)

    headers = {
        'Authorization': f'Basic {wp_conn.access_token}',
        'Content-Type': 'application/json',
    }

    # Parse title and content
    soup = BeautifulSoup(optimized_html, "html.parser")
    title = soup.title.string.strip() if soup.title else "Service Page"
    content_body = soup.body if soup.body else optimized_html
    content_html = str(content_body) if hasattr(content_body, 'prettify') else content_body

    slug = slugify(title)

    page_data = {
        "title": title,
        "slug": slug,
        "content": f"<div>{content_html}</div>",
        "status": "publish"
    }

    try:
        # Upload or update page (naively assumes new upload)
        response = requests.post(
            f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/pages",
            headers=headers,
            json=page_data
        )

        logger.info(f"🔼 WordPress Page Upload Response: ")

        if response.status_code in [200, 201]:
            logger.info("✅ Service page content uploaded successfully.")
        else:
            logger.error(f"❌ Failed to upload service page content: {response.text}")

    except Exception as e:
        logger.exception(f"❌ Exception during service page upload: {str(e)}")
