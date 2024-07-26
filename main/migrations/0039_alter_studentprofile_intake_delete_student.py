# Generated by Django 5.0.6 on 2024-07-26 08:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0038_studentprofile_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentprofile',
            name='intake',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='students', to='main.intake'),
        ),
        migrations.DeleteModel(
            name='Student',
        ),
    ]
