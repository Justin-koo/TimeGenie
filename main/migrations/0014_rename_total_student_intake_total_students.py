# Generated by Django 5.0.6 on 2024-07-03 10:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0013_alter_intake_status'),
    ]

    operations = [
        migrations.RenameField(
            model_name='intake',
            old_name='total_student',
            new_name='total_students',
        ),
    ]
