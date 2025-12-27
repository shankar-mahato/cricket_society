from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class UserProfile(models.Model):
    """Extended user profile with additional information and distributor hierarchy"""
    USER_TYPE_CHOICES = [
        ('master_dl', 'Master DL'),
        ('dl', 'DL User'),
        ('end_user', 'End User'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True, 
                                        help_text="User profile picture")
    bio = models.TextField(max_length=500, blank=True, null=True)
    
    # Distributor hierarchy fields
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='end_user',
                                 help_text="Type of user in the distributor system")
    master_dl = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='dl_users', 
                                   help_text="Master DL who created this DL user")
    dl_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='end_users',
                                help_text="DL User assigned to this end user")
    
    # DL-specific fields
    dl_code = models.CharField(max_length=50, unique=True, null=True, blank=True,
                               help_text="Unique code for DL user")
    is_active = models.BooleanField(default=True)
    
    # Client-specific fields (for end users)
    max_win_limit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                        default=Decimal('0.00'),
                                        help_text="Maximum win limit for this client")
    match_commission = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                          default=Decimal('0.00'),
                                          help_text="Commission percentage for matches")
    session_commission = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                            default=Decimal('0.00'),
                                            help_text="Commission percentage for sessions")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile - {self.get_user_type_display()}"

    def save(self, *args, **kwargs):
        if not self.dl_code and self.user_type == 'dl':
            # Generate unique DL code
            import secrets
            self.dl_code = secrets.token_urlsafe(16)[:12].upper()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
