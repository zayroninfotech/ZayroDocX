from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pdf_tools', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='RCRoom',
        ),
    ]
