# tasks/tests/test_engine.py
"""
AI Engine Unit Tests
====================

Comprehensive test suite for the mathematical "Brain" of the prioritization system.

This module tests:
1. Urgency computation (deterministic, date-based)
2. Importance computation (weighted relevance)
3. Quadrant assignment (Eisenhower Matrix)
4. GoalWeights validation (sum must equal 1.0)

Test Philosophy:
----------------
- Test MATH, not just models
- Test edge cases (None, overdue, far-future)
- Test boundary conditions (exactly 0.0, exactly 1.0)
- Tests are deterministic and do not require external services
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from goals.models import GoalWeights
from tasks.ai_engine.urgency import (
    MAX_LOOKAHEAD_DAYS,
    compute_urgency,
    _compute_due_date_component,
    _compute_effort_component,
)
from tasks.ai_engine.orchestrator import AIOrchestrator


User = get_user_model()


# ===========================================================================
# URGENCY SCORE TESTS
# ===========================================================================


class TestComputeUrgency(TestCase):
    """
    Test suite for the compute_urgency function.
    
    Tests cover:
    - Overdue tasks (must return 1.0)
    - Tasks due today (must return ~1.0)
    - Tasks due in the future (linear decay)
    - Tasks with no due date (effort-only contribution)
    - Edge cases (None values, invalid formats)
    """

    def setUp(self) -> None:
        """Set up a fixed reference time for deterministic testing."""
        # Fixed reference: January 15, 2024 at noon UTC
        self.fixed_now = datetime.datetime(
            2024, 1, 15, 12, 0, 0, tzinfo=datetime.timezone.utc
        )

    # -----------------------------------------------------------------------
    # Overdue Task Tests
    # -----------------------------------------------------------------------

    def test_overdue_task_returns_maximum_urgency(self) -> None:
        """An overdue task (past due date) must return exactly 1.0."""
        # Task was due yesterday
        overdue_date = "2024-01-14"
        
        result = compute_urgency(due_date=overdue_date, effort_hours=3, now=self.fixed_now)
        
        self.assertEqual(result, 1.0, "Overdue task must have urgency of 1.0")

    def test_severely_overdue_task_still_returns_one(self) -> None:
        """A task overdue by many days still returns exactly 1.0 (clamped)."""
        # Task was due 100 days ago
        severely_overdue = "2023-10-07"
        
        result = compute_urgency(due_date=severely_overdue, now=self.fixed_now)
        
        self.assertEqual(result, 1.0, "Severely overdue task must still be 1.0")

    # -----------------------------------------------------------------------
    # Due Today Tests
    # -----------------------------------------------------------------------

    def test_task_due_today_returns_near_maximum(self) -> None:
        """A task due today should have urgency close to 1.0."""
        due_today = "2024-01-15"
        
        result = compute_urgency(due_date=due_today, effort_hours=3, now=self.fixed_now)
        
        # Due today means days_until=0, so due_component=1.0
        # With effort=3: effort_component = (3-1)/4 = 0.5
        # urgency = 1.0 * 0.8 + 0.5 * 0.2 = 0.9
        self.assertGreaterEqual(result, 0.8, "Task due today should be high urgency")
        self.assertLessEqual(result, 1.0)

    # -----------------------------------------------------------------------
    # Future Due Date Tests (Linear Decay)
    # -----------------------------------------------------------------------

    def test_task_due_in_one_day(self) -> None:
        """A task due tomorrow has high but not maximum urgency."""
        due_tomorrow = "2024-01-16"
        
        result = compute_urgency(due_date=due_tomorrow, effort_hours=1, now=self.fixed_now)
        
        # days_until=1, due_component = 1 - 1/30 ≈ 0.9667
        # effort=1: effort_component = 0
        # urgency = 0.9667 * 0.8 + 0 * 0.2 ≈ 0.7733
        self.assertGreater(result, 0.7)
        self.assertLess(result, 0.9)

    def test_task_due_in_fifteen_days(self) -> None:
        """A task due in 15 days (midpoint) should have ~0.4 urgency."""
        due_in_15_days = "2024-01-30"
        
        result = compute_urgency(due_date=due_in_15_days, effort_hours=1, now=self.fixed_now)
        
        # days_until=15, due_component = 1 - 15/30 = 0.5
        # effort=1: effort_component = 0
        # urgency = 0.5 * 0.8 + 0 * 0.2 = 0.4
        self.assertAlmostEqual(result, 0.4, places=2)

    def test_task_due_in_thirty_days(self) -> None:
        """A task due at the MAX_LOOKAHEAD_DAYS horizon should have minimal urgency."""
        due_in_30_days = "2024-02-14"
        
        result = compute_urgency(due_date=due_in_30_days, effort_hours=1, now=self.fixed_now)
        
        # days_until=30, due_component = 1 - 30/30 = 0.0
        # effort=1: effort_component = 0
        # urgency = 0.0
        self.assertAlmostEqual(result, 0.0, places=2)

    def test_task_due_in_forty_days_returns_near_zero(self) -> None:
        """A task due beyond MAX_LOOKAHEAD_DAYS should have ~0.0 urgency."""
        due_in_40_days = "2024-02-24"
        
        result = compute_urgency(due_date=due_in_40_days, effort_hours=1, now=self.fixed_now)
        
        # days_until=40 > MAX_LOOKAHEAD_DAYS
        # due_component = max(0, 1 - 40/30) = max(0, -0.33) = 0.0
        self.assertAlmostEqual(result, 0.0, places=2)

    # -----------------------------------------------------------------------
    # No Due Date Tests (Effort-Only)
    # -----------------------------------------------------------------------

    def test_no_due_date_with_minimum_effort(self) -> None:
        """No deadline + minimum effort (1) should return 0.0."""
        result = compute_urgency(due_date=None, effort_hours=1, now=self.fixed_now)
        
        # due_component = 0 (no date)
        # effort_component = (1-1)/4 = 0
        # urgency = 0 * 0.8 + 0 * 0.2 = 0.0
        self.assertEqual(result, 0.0)

    def test_no_due_date_with_maximum_effort(self) -> None:
        """No deadline + maximum effort (5) should return 0.2."""
        result = compute_urgency(due_date=None, effort_hours=5, now=self.fixed_now)
        
        # due_component = 0 (no date)
        # effort_component = (5-1)/4 = 1.0
        # urgency = 0 * 0.8 + 1.0 * 0.2 = 0.2
        self.assertEqual(result, 0.2)

    def test_no_due_date_with_medium_effort(self) -> None:
        """No deadline + medium effort (3) should return 0.1."""
        result = compute_urgency(due_date=None, effort_hours=3, now=self.fixed_now)
        
        # effort_component = (3-1)/4 = 0.5
        # urgency = 0 * 0.8 + 0.5 * 0.2 = 0.1
        self.assertEqual(result, 0.1)

    # -----------------------------------------------------------------------
    # Effort Impact Tests
    # -----------------------------------------------------------------------

    def test_effort_boosts_urgency_for_same_due_date(self) -> None:
        """Higher effort should increase urgency for the same due date."""
        due_date = "2024-01-25"  # 10 days out
        
        low_effort_result = compute_urgency(due_date=due_date, effort_hours=1, now=self.fixed_now)
        high_effort_result = compute_urgency(due_date=due_date, effort_hours=5, now=self.fixed_now)
        
        self.assertGreater(
            high_effort_result, 
            low_effort_result,
            "High effort should boost urgency compared to low effort"
        )
        
        # The difference should be exactly 0.2 (the effort weight)
        difference = high_effort_result - low_effort_result
        self.assertAlmostEqual(difference, 0.2, places=3)

    # -----------------------------------------------------------------------
    # Edge Cases and Defensive Programming
    # -----------------------------------------------------------------------

    def test_none_due_date_and_none_effort(self) -> None:
        """Both None values should return 0.0."""
        result = compute_urgency(due_date=None, effort_hours=None, now=self.fixed_now)
        
        self.assertEqual(result, 0.0)

    def test_invalid_date_format_returns_zero(self) -> None:
        """An invalid date string should be handled gracefully."""
        result = compute_urgency(due_date="not-a-date", effort_hours=3, now=self.fixed_now)
        
        # Invalid date → due_component=0, only effort contributes
        # effort_component = 0.5, urgency = 0 * 0.8 + 0.5 * 0.2 = 0.1
        self.assertAlmostEqual(result, 0.1, places=2)

    def test_effort_clamped_to_valid_range(self) -> None:
        """Effort values outside [1, 5] should be clamped."""
        # Effort below minimum
        result_low = compute_urgency(due_date=None, effort_hours=0, now=self.fixed_now)
        self.assertEqual(result_low, 0.0)  # Clamped to 1, then (1-1)/4 = 0
        
        # Effort above maximum  
        result_high = compute_urgency(due_date=None, effort_hours=10, now=self.fixed_now)
        self.assertEqual(result_high, 0.2)  # Clamped to 5, then (5-1)/4 = 1.0 → 1.0 * 0.2 = 0.2

    def test_date_object_input(self) -> None:
        """Should accept datetime.date objects, not just strings."""
        due_date = datetime.date(2024, 1, 20)  # 5 days from fixed_now
        
        result = compute_urgency(due_date=due_date, effort_hours=1, now=self.fixed_now)
        
        # days_until=5, due_component = 1 - 5/30 ≈ 0.8333
        # urgency = 0.8333 * 0.8 ≈ 0.6667
        self.assertGreater(result, 0.6)
        self.assertLess(result, 0.7)


class TestDueDateComponent(TestCase):
    """
    Unit tests for the _compute_due_date_component helper function.
    
    Isolated tests for the temporal proximity logic.
    """

    def setUp(self) -> None:
        self.fixed_now = datetime.datetime(
            2024, 1, 15, 12, 0, 0, tzinfo=datetime.timezone.utc
        )

    def test_none_returns_zero(self) -> None:
        """None due date should return 0.0 component."""
        result = _compute_due_date_component(None, self.fixed_now)
        self.assertEqual(result, 0.0)

    def test_overdue_returns_one(self) -> None:
        """Past due date should return 1.0."""
        result = _compute_due_date_component("2024-01-10", self.fixed_now)
        self.assertEqual(result, 1.0)

    def test_due_today_returns_one(self) -> None:
        """Due today (days_until=0) should return 1.0."""
        result = _compute_due_date_component("2024-01-15", self.fixed_now)
        self.assertEqual(result, 1.0)


class TestEffortComponent(TestCase):
    """
    Unit tests for the _compute_effort_component helper function.
    """

    def test_none_returns_zero(self) -> None:
        """None effort should return 0.0 component."""
        result = _compute_effort_component(None)
        self.assertEqual(result, 0.0)

    def test_minimum_effort_returns_zero(self) -> None:
        """Effort of 1 should return 0.0."""
        result = _compute_effort_component(1)
        self.assertEqual(result, 0.0)

    def test_maximum_effort_returns_one(self) -> None:
        """Effort of 5 should return 1.0."""
        result = _compute_effort_component(5)
        self.assertEqual(result, 1.0)

    def test_midpoint_effort(self) -> None:
        """Effort of 3 should return 0.5."""
        result = _compute_effort_component(3)
        self.assertEqual(result, 0.5)


# ===========================================================================
# GOAL WEIGHTS VALIDATION TESTS
# ===========================================================================


class TestGoalWeightsValidation(TestCase):
    """
    Test suite for GoalWeights model validation.
    
    Ensures the weight-sum constraint (must equal 1.0) is enforced.
    """

    def setUp(self) -> None:
        """Create a test user for GoalWeights."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    def test_valid_weights_sum_to_one(self) -> None:
        """Weights that sum to exactly 1.0 should save successfully."""
        weights = GoalWeights(
            user=self.user,
            work_bills=0.4,
            study=0.3,
            health=0.2,
            relationships=0.1
        )
        
        # Should not raise
        weights.full_clean()
        weights.save()
        
        self.assertEqual(GoalWeights.objects.count(), 1)

    def test_equal_weights_are_valid(self) -> None:
        """Default equal weights (0.25 each) should be valid."""
        weights = GoalWeights(
            user=self.user,
            work_bills=0.25,
            study=0.25,
            health=0.25,
            relationships=0.25
        )
        
        weights.full_clean()
        weights.save()
        
        total = weights.work_bills + weights.study + weights.health + weights.relationships
        self.assertAlmostEqual(total, 1.0, places=3)

    def test_weights_below_one_raises_validation_error(self) -> None:
        """Weights summing to less than 1.0 should raise ValidationError."""
        weights = GoalWeights(
            user=self.user,
            work_bills=0.2,
            study=0.2,
            health=0.2,
            relationships=0.2  # Sum = 0.8
        )
        
        with self.assertRaises(ValidationError) as ctx:
            weights.full_clean()
        
        self.assertIn("sum of all weights must be exactly 1.0", str(ctx.exception).lower())

    def test_weights_above_one_raises_validation_error(self) -> None:
        """Weights summing to more than 1.0 should raise ValidationError."""
        weights = GoalWeights(
            user=self.user,
            work_bills=0.5,
            study=0.5,
            health=0.2,
            relationships=0.1  # Sum = 1.3
        )
        
        with self.assertRaises(ValidationError) as ctx:
            weights.full_clean()
        
        self.assertIn("sum of all weights must be exactly 1.0", str(ctx.exception).lower())

    def test_floating_point_precision_tolerance(self) -> None:
        """Weights within epsilon of 1.0 should be accepted (float precision)."""
        # This tests the 0.999 <= total <= 1.001 tolerance
        weights = GoalWeights(
            user=self.user,
            work_bills=0.333,
            study=0.333,
            health=0.334,
            relationships=0.0  # Sum = 1.0
        )
        
        # Should not raise due to tolerance
        weights.full_clean()

    def test_individual_weights_clamped_to_range(self) -> None:
        """Individual weights must be between 0.0 and 1.0."""
        # Negative weight
        weights_negative = GoalWeights(
            user=self.user,
            work_bills=-0.1,
            study=0.5,
            health=0.3,
            relationships=0.3
        )
        
        with self.assertRaises(ValidationError):
            weights_negative.full_clean()


# ===========================================================================
# IMPORTANCE CALCULATION TESTS
# ===========================================================================


class TestImportanceCalculation(TestCase):
    """
    Test suite for importance score calculation.
    
    Importance = Σ(relevance_score[domain] × weight[domain])
    
    This ensures the weighted average formula is correctly implemented.
    """

    def setUp(self) -> None:
        """Initialize orchestrator for testing."""
        # Patch the ExternalAIScorer to avoid API calls
        self.patcher = patch(
            "tasks.ai_engine.orchestrator.ExternalAIScorer"
        )
        self.mock_ai = self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()

    def test_perfect_alignment_with_dominant_weight(self) -> None:
        """
        A task with 1.0 relevance to a category with 0.5 weight
        should contribute 0.5 to importance.
        """
        orchestrator = AIOrchestrator()
        
        relevance = {
            "work_bills": 1.0,
            "study": 0.0,
            "health": 0.0,
            "relationships": 0.0
        }
        weights = {
            "work_bills": 0.5,
            "study": 0.2,
            "health": 0.2,
            "relationships": 0.1
        }
        
        importance = orchestrator._compute_importance(relevance, weights)
        
        # 1.0 * 0.5 + 0.0 * 0.2 + 0.0 * 0.2 + 0.0 * 0.1 = 0.5
        self.assertAlmostEqual(importance, 0.5, places=4)

    def test_partial_relevance_multiple_domains(self) -> None:
        """
        A task with partial relevance to multiple domains.
        """
        orchestrator = AIOrchestrator()
        
        relevance = {
            "work_bills": 0.8,
            "study": 0.6,
            "health": 0.0,
            "relationships": 0.2
        }
        weights = {
            "work_bills": 0.25,
            "study": 0.25,
            "health": 0.25,
            "relationships": 0.25
        }
        
        importance = orchestrator._compute_importance(relevance, weights)
        
        # 0.8 * 0.25 + 0.6 * 0.25 + 0.0 * 0.25 + 0.2 * 0.25
        # = 0.2 + 0.15 + 0.0 + 0.05 = 0.4
        self.assertAlmostEqual(importance, 0.4, places=4)

    def test_zero_relevance_returns_zero(self) -> None:
        """A task with zero relevance to all domains should have 0.0 importance."""
        orchestrator = AIOrchestrator()
        
        relevance = {
            "work_bills": 0.0,
            "study": 0.0,
            "health": 0.0,
            "relationships": 0.0
        }
        weights = {
            "work_bills": 0.25,
            "study": 0.25,
            "health": 0.25,
            "relationships": 0.25
        }
        
        importance = orchestrator._compute_importance(relevance, weights)
        
        self.assertEqual(importance, 0.0)

    def test_full_relevance_full_weight_returns_one(self) -> None:
        """Full relevance (1.0) to a domain with full weight (1.0) = 1.0."""
        orchestrator = AIOrchestrator()
        
        relevance = {"single_domain": 1.0}
        weights = {"single_domain": 1.0}
        
        importance = orchestrator._compute_importance(relevance, weights)
        
        self.assertEqual(importance, 1.0)

    def test_importance_is_clamped(self) -> None:
        """Importance should be clamped to [0.0, 1.0] even with edge values."""
        orchestrator = AIOrchestrator()
        
        # Edge case: weights don't sum to 1 (hypothetical misconfiguration)
        relevance = {"a": 1.0, "b": 1.0}
        weights = {"a": 0.8, "b": 0.8}  # Sum > 1
        
        importance = orchestrator._compute_importance(relevance, weights)
        
        # Raw: 1.0 * 0.8 + 1.0 * 0.8 = 1.6 → clamped to 1.0
        self.assertEqual(importance, 1.0)


# ===========================================================================
# QUADRANT ASSIGNMENT TESTS
# ===========================================================================


class TestQuadrantAssignment(TestCase):
    """
    Test suite for Eisenhower Matrix quadrant assignment.
    
    Quadrant logic:
    - Q1: Urgent AND Important (both >= 0.5)
    - Q2: Important but NOT Urgent (importance >= 0.5, urgency < 0.5)
    - Q3: Urgent but NOT Important (urgency >= 0.5, importance < 0.5)
    - Q4: Neither Urgent nor Important (both < 0.5)
    """

    def setUp(self) -> None:
        self.patcher = patch("tasks.ai_engine.orchestrator.ExternalAIScorer")
        self.mock_ai = self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()

    def test_q1_urgent_and_important(self) -> None:
        """High urgency + high importance → Q1 (Do Now)."""
        orchestrator = AIOrchestrator()
        
        quadrant = orchestrator._compute_quadrant(importance=0.8, urgency=0.9)
        
        self.assertEqual(quadrant, "Q1")

    def test_q2_important_not_urgent(self) -> None:
        """High importance + low urgency → Q2 (Schedule)."""
        orchestrator = AIOrchestrator()
        
        quadrant = orchestrator._compute_quadrant(importance=0.7, urgency=0.3)
        
        self.assertEqual(quadrant, "Q2")

    def test_q3_urgent_not_important(self) -> None:
        """Low importance + high urgency → Q3 (Delegate)."""
        orchestrator = AIOrchestrator()
        
        quadrant = orchestrator._compute_quadrant(importance=0.2, urgency=0.8)
        
        self.assertEqual(quadrant, "Q3")

    def test_q4_neither(self) -> None:
        """Low importance + low urgency → Q4 (Delete/Drop)."""
        orchestrator = AIOrchestrator()
        
        quadrant = orchestrator._compute_quadrant(importance=0.3, urgency=0.2)
        
        self.assertEqual(quadrant, "Q4")

    def test_boundary_at_half(self) -> None:
        """Exactly 0.5 on both dimensions → Q1 (inclusive boundary)."""
        orchestrator = AIOrchestrator()
        
        quadrant = orchestrator._compute_quadrant(importance=0.5, urgency=0.5)
        
        self.assertEqual(quadrant, "Q1")

    def test_importance_boundary(self) -> None:
        """Importance exactly at 0.5 with low urgency → Q2."""
        orchestrator = AIOrchestrator()
        
        quadrant = orchestrator._compute_quadrant(importance=0.5, urgency=0.4)
        
        self.assertEqual(quadrant, "Q2")

    def test_urgency_boundary(self) -> None:
        """Urgency exactly at 0.5 with low importance → Q3."""
        orchestrator = AIOrchestrator()
        
        quadrant = orchestrator._compute_quadrant(importance=0.4, urgency=0.5)
        
        self.assertEqual(quadrant, "Q3")
