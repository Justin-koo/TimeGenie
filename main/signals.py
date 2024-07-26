from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.dispatch import receiver

@receiver(post_save, sender=User)
def assign_student_group(sender, instance, created, **kwargs):
    if created:
        # Add logic here to determine if the user should be added to the 'Students' group
        # For now, we'll assume every new user is a student (adjust this logic as needed)
        students_group, _ = Group.objects.get_or_create(name='Students')
        instance.groups.add(students_group)
