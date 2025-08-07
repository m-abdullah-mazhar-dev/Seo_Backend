from datetime import datetime, timedelta
from seo_services.models import Keyword
from .google_service import build_service
from .models import SearchConsoleToken

def sync_user_keywords(user):
    try:
        token = SearchConsoleToken.objects.get(user=user)
    except SearchConsoleToken.DoesNotExist:
        return {"error": "Token not found"}

    service = build_service(token.credentials)

    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=30)

    response = service.searchanalytics().query(
        siteUrl=token.site_url,
        body={
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'dimensions': ['query'],
            'rowLimit': 5000,
        }
    ).execute()

    keyword_map = {k.keyword.lower(): k for k in Keyword.objects.filter(service__onboarding_form__user=user)}
    print(keyword_map)

    for row in response.get('rows', []):
        query = row['keys'][0].lower()
        if query in keyword_map:
            k = keyword_map[query]
            k.clicks = row.get('clicks', 0)
            k.impressions = row.get('impressions', 0)
            k.ctr = row.get('ctr', 0)
            k.average_position = row.get('position', 0)
            k.save()

    return {"message": f"✅ Synced GSC data for user: {user.email}"}
