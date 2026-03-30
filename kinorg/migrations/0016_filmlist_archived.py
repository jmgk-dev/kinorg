from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kinorg', '0015_stars_nullable'),
    ]

    operations = [
        migrations.AddField(
            model_name='filmlist',
            name='archived',
            field=models.BooleanField(default=False),
        ),
    ]
