# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('seo_services', '0033_remove_businesslocation_area_list_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicearea',
            name='center',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.AddField(
            model_name='servicearea',
            name='area_list',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
        migrations.AddField(
            model_name='servicearea',
            name='business_service_areas',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
    ]
