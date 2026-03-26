from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kinorg', '0013_add_media_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='pccscreening',
            name='film',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pcc_screenings',
                to='kinorg.film',
            ),
        ),
        migrations.AddField(
            model_name='pccscreening',
            name='hidden',
            field=models.BooleanField(default=False),
        ),
    ]
