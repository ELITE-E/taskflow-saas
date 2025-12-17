from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

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
    

class GoalWeights(models.Model):
    """
    Stores strategic weights for importance score computation on a per-user basis.
    All weights are normalized values between 0.0 and 1.0.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="goal_weights"
    )

    # Individual category weights
    work_bills = models.FloatField(
        default=0.25,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Importance weight for financial and career tasks."
    )
    study = models.FloatField(
        default=0.25,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Importance weight for education and skill building."
    )
    health = models.FloatField(
        default=0.25,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Importance weight for physical and mental well-being."
    )
    relationships = models.FloatField(
        default=0.25,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Importance weight for social and family life."
    )

    class Meta:
        verbose_name = "Goal Weights"
        verbose_name_plural = "Goal Weights"

    def __str__(self):
        return f"Weights for {self.user.username}"

    def clean(self):
        """
        Ensures the sum of all weights equals exactly 1.0 (100%).
        Note: Using a small epsilon for float comparison to avoid precision issues.
        """
        total = self.work_bills + self.study + self.health + self.relationships
        
        # Check if total is within a tiny margin of 1.0
        if not (0.999 <= total <= 1.001):
            raise ValidationError(
                f"The sum of all weights must be exactly 1.0. Current sum: {total}"
            )

    def save(self, *args, **kwargs):
        """
        Overridden to ensure full_clean is called before saving to the database,
        enforcing the weight-sum validation logic.
        """
        self.full_clean()
        super().save(*args, **kwargs)