# Generated by Django 5.0.6 on 2024-06-03 11:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_alter_course_created_at_section'),
    ]

    operations = [
        migrations.RenameField(
            model_name='section',
            old_name='code',
            new_name='section_code',
        ),
        migrations.RenameField(
            model_name='section',
            old_name='duration',
            new_name='section_duration',
        ),
        migrations.RenameField(
            model_name='section',
            old_name='type',
            new_name='section_type',
        ),
    ]
