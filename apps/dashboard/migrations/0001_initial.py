from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ToolPrivilege',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True)),
                ('slug', models.CharField(max_length=80, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('category', models.CharField(max_length=60)),
                ('requires_login', models.BooleanField(default=False)),
                ('icon', models.CharField(default='fa-file-pdf', max_length=80)),
            ],
            options={'ordering': ['category', 'name']},
        ),
    ]
