from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pdf_tools', '0003_add_rcroom'),
    ]

    operations = [
        migrations.CreateModel(
            name='RCCommand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cmd_type', models.CharField(max_length=20)),
                ('data', models.JSONField()),
                ('ts', models.FloatField()),
                ('consumed', models.BooleanField(db_index=True, default=False)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='commands', to='pdf_tools.rcroom')),
            ],
        ),
    ]
