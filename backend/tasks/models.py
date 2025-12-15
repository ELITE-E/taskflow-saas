from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Task(models.Model):
    """
    Represents an operational task for the user, tied to a goal.
    """
    # Link to the CustomUser Model
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name=_("user")
    )

    title = models.CharField(max_length=255, verbose_name=_("title"))
    description = models.TextField(blank=True, verbose_name=_("description"))
    
    # Task planning fields
    due_date = models.DateField(
        null=True, blank=True,
        verbose_name=_("due date"),
        help_text=_("The deadline for the task.")
    )
    
    # Estimate of time/complexity for AI prioritization (e.g., 1=low, 5=high)
    effort_estimate = models.PositiveSmallIntegerField(
        default=3,
        verbose_name=_("effort estimate"),
        help_text=_("Estimated effort required (1=low to 5=high).")
    )

    # Status fields
    is_completed = models.BooleanField(default=False, verbose_name=_("is completed"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))
    
    class Meta:
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")
        # Default sorting: active tasks first, then by earliest due date
        ordering = ['is_completed', 'due_date', '-created_at']

    def __str__(self):
        return f"Task for {self.user.username}: {self.title}"