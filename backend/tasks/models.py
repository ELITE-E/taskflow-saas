from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from goals.models import Goal

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

    # CRITICAL ADDITION: Link to the Goal model
    goal = models.ForeignKey(
        Goal,
        on_delete=models.SET_NULL, # If a Goal is deleted, the task remains (goal=null)
        null=True, blank=True, # Task can exist without a goal
        related_name='tasks',
        verbose_name=_("associated goal")
    )

    title = models.CharField(max_length=255, verbose_name=_("title"))
    description = models.TextField(blank=True, verbose_name=_("description"))
    priority_score = models.FloatField(
        default=0.0,
        verbose_name=_("priority score"),
        help_text=_("AI-calculated score for prioritization.")
    )
    celery_task_id = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text=_("The ID of the background process handling the AI scoring.")
    )
    is_prioritized = models.BooleanField(
        default=False,
        verbose_name=_("is prioritized"),
        help_text=_("Flag indicating if the task has been processed by the AI engine.")
    )
    
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
        ordering = ['is_completed','-priority_score', 'due_date', '-created_at']

    def __str__(self):
        return f"Task for {self.user.username}: {self.title}"