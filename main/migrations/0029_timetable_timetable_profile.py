# Generated by Django 5.0.6 on 2024-07-22 10:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0028_alter_timetable_table_alter_timetableentry_table'),
    ]

    operations = [
        migrations.AddField(
            model_name='timetable',
            name='timetable_profile',
            field=models.CharField(default=1, max_length=20, unique=True),
            preserve_default=False,
        ),
    ]
