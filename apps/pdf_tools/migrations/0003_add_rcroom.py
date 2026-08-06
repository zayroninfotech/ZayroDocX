from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pdf_tools', '0002_add_eyeroom'),
    ]

    operations = [
        migrations.CreateModel(
            name='RCRoom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(db_index=True, max_length=9, unique=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('offer', models.JSONField(blank=True, null=True)),
                ('answer', models.JSONField(blank=True, null=True)),
                ('host_ice', models.JSONField(default=list)),
                ('viewer_ice', models.JSONField(default=list)),
                ('closed', models.BooleanField(default=False)),
            ],
        ),
    ]
