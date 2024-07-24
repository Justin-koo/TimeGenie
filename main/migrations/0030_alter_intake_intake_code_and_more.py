# Generated by Django 5.0.6 on 2024-07-24 14:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0029_timetable_timetable_profile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='intake',
            name='intake_code',
            field=models.CharField(max_length=20, unique=True),
        ),
        migrations.AddConstraint(
            model_name='timetable',
            constraint=models.UniqueConstraint(fields=('timetable_profile',), name='unique_timetable_profile'),
        ),
    ]
