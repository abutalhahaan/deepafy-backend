from django.db.models.signals import post_save
from django.dispatch import receiver

from identity.models import UserIdentity
from security.models import SecurityProfile


@receiver(
    post_save,
    sender=UserIdentity,
    dispatch_uid="security.create_profile_for_identity",
)
def create_security_profile(sender, instance, created, **kwargs):
    if created:
        SecurityProfile.objects.get_or_create(
            identity=instance,
        )
