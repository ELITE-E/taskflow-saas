from django.db import models
from django.contrib.auth.models import AbstractBaseUser,PermissionsMixin 
from django.utils.translation import gettext_lazy as _
from .managers import CustomUserManager

# Create your models here.
class CustomUser(AbstractBaseUser,PermissionsMixin):
    """
    Docstring for CustomUser
    CustomUser model extending the permissionMixin&Absst_name=models.CharField(_('firstname',max_length=30,blank=False))tractBaseUser .
    Uses email as the unique auth field

    """
    email=models.EmailField(
        _('email_address'),
        unique=True
        #Unique & required enforces strong validation rules here
    )

    username=models.CharField(
        _('username'),
        max_length=150,
        blank=False,
        unique=True,
        null=True
    )

    first_name=models.CharField(_('firstname'),max_length=150,blank=False)
    last_name=models.CharField(_('lastname'),max_length=150,blank=False)
    # Core permissions fields for superuser capabilities
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), auto_now_add=True)

    # Custom field specific to your application
    # This will be used in Module 2 for scheduling tasks optimally
    timezone = models.CharField(
        _('Timezone'),
        max_length=60,
        default='UTC',
        help_text=_('User timezone for scheduling tasks.'),
    )
    
    # ------------------ Model Configuration ------------------
    objects = CustomUserManager()

    # The field used for authentication (login)
    USERNAME_FIELD = 'email'
    
    # Fields required when creating a user via the createsuperuser command
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        # Ensure all core permissions are inherited
        permissions = (
            ('can_view_tasks', 'Can view all tasks'),
        )

    def get_full_name(self):
        """Returns the first_name plus the last_name, with a space in between."""
        return f'{self.first_name} {self.last_name}'

    def get_short_name(self):
        """Returns the short name for the user."""
        return self.first_name

    def __str__(self):
        return self.email
