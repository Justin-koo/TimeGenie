# Generated by Django 5.0.6 on 2024-07-03 09:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_alter_intake_sections'),
    ]

    operations = [
        migrations.AlterField(
            model_name='intake',
            name='status',
            field=models.IntegerField(),
        ),
    ]
