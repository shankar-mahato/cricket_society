from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create profile when user is created"""
    if created:
        try:
            UserProfile.objects.get_or_create(user=instance)
        except Exception as e:
            # Log error but don't fail user creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating profile for user {instance.username}: {str(e)}", exc_info=True)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Automatically save profile when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()

