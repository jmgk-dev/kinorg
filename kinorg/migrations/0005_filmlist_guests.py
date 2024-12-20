# Generated by Django 5.1 on 2024-09-05 17:05

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kinorg', '0004_alter_filmlist_owner'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='filmlist',
            name='guests',
            field=models.ManyToManyField(related_name='guestlists', related_query_name='guestlist', to=settings.AUTH_USER_MODEL),
        ),
    ]
