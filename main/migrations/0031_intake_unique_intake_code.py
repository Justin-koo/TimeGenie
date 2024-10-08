# Generated by Django 5.0.6 on 2024-07-24 14:57

import django.db.models.functions.text
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0030_alter_intake_intake_code_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='intake',
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower('intake_code'), name='unique_intake_code'),
        ),
    ]
