from celery import shared_task
from django.contrib.auth import get_user_model
from .models import SearchConsoleToken
from .utils import sync_user_keywords
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task
def sync_all_user_keywords():
    logger.info("🔁 Starting GSC keyword sync for all users...")

    tokens = SearchConsoleToken.objects.select_related("user").all()

    for token in tokens:
        user = token.user
        logger.info(f"🔄 Syncing for user: {user.email}")
        try:
            result = sync_user_keywords(user)
            logger.info(result)
        except Exception as e:
            logger.error(f"❌ Failed to sync keywords for {user.email}: {e}")

    logger.info("✅ Finished syncing GSC data.")
