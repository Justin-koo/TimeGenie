# Generated by Django 5.0.6 on 2024-07-03 08:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0011_intake'),
    ]

    operations = [
        migrations.AlterField(
            model_name='intake',
            name='sections',
            field=models.ManyToManyField(blank=True, related_name='intakes', to='main.section'),
        ),
    ]
