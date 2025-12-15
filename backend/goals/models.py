from django.db import models

# Create your models here.
# goals/models.py

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Goal(models.Model):
    """
    Represents a strategic goal set by the user.
    """
    # Link to the CustomUser Model
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='goals',
        verbose_name=_("user")
    )

    title = models.CharField(max_length=255, verbose_name=_("title"))
    
    description = models.TextField(blank=True, verbose_name=_("description"))

    # Critical field for prioritization logic (e.g., 1-10)
    weight = models.PositiveSmallIntegerField(
        default=5,
        verbose_name=_("weight"),
        help_text=_("Strategic importance of the goal (e.g., 1-10).")
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))
    
    # Soft delete mechanism
    is_archived = models.BooleanField(default=False, verbose_name=_("is archived"))

    class Meta:
        verbose_name = _("Goal")
        verbose_name_plural = _("Goals")
        ordering = ['-weight', 'created_at']

    def __str__(self):
        return f"{self.user.username}'s Goal: {self.title}"