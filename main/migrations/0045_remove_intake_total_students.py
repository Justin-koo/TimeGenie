# Generated by Django 5.0.6 on 2024-07-26 15:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0044_remove_feedback_delayed_lunch_start_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='intake',
            name='total_students',
        ),
    ]
