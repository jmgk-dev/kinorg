from django.contrib.postgres.indexes import GinIndex
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('kinorg', '0020_add_primary_country_index'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='film',
            index=GinIndex(fields=['collections'], name='film_collections_gin'),
        ),
    ]
