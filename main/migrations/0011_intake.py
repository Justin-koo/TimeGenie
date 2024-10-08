# Generated by Django 5.0.6 on 2024-07-03 06:43

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0010_classroom_status_alter_classroom_capacity'),
    ]

    operations = [
        migrations.CreateModel(
            name='Intake',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('intake_code', models.CharField(max_length=20)),
                ('total_student', models.IntegerField(default=0)),
                ('status', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sections', models.ManyToManyField(related_name='intakes', to='main.section')),
            ],
            options={
                'db_table': 'intakes',
            },
        ),
    ]
