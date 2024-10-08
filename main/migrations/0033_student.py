# Generated by Django 5.0.6 on 2024-07-26 06:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0032_remove_intake_unique_intake_code_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('username', models.CharField(max_length=20, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('password', models.CharField(max_length=128)),
                ('intake', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='students', to='main.intake')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
