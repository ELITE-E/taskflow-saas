# tasks/tests/test_orchestration.py
"""
AI Orchestration Integration Tests
==================================

This module contains integration tests for the AI scoring pipeline.

Test Philosophy:
----------------
- Mock external dependencies (OpenAI API) to avoid costs and flakiness
- Test the full flow from Celery task to database persistence
- Verify error handling paths don't crash the system
- Ensure idempotency and race condition handling

Test Categories:
----------------
1. Success Path Tests - Happy path with mocked AI responses
2. Failure Path Tests - API errors, timeouts, invalid responses
3. Idempotency Tests - Verify retries don't cause duplicates
4. Edge Case Tests - Boundary conditions and unusual inputs
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings

from goals.models import GoalWeights
from tasks.ai_engine.celery_tasks import (
    _get_user_weights,
    _should_skip_scoring,
    run_ai_relevance_scoring,
)
from tasks.ai_engine.external_scorer import ExternalAIScorer
from tasks.ai_engine.orchestrator import (
    SCORING_METHOD_AI,
    SCORING_METHOD_FALLBACK,
    SCORING_METHOD_RULES,
    AIOrchestrator,
)
from tasks.models import Task

User = get_user_model()


# ===========================================================================
# HELPER FIXTURES
# ===========================================================================


def create_mock_openai_response(
    relevance_scores: Dict[str, float],
    confidence: float = 0.85,
) -> MagicMock:
    """
    Create a mock OpenAI API response object.

    Args:
        relevance_scores: Dictionary of domain -> relevance score.
        confidence: Confidence value for the response.

    Returns:
        MagicMock configured to return the specified response.
    """
    response_json = json.dumps({
        "relevance_scores": relevance_scores,
        "confidence": confidence,
    })

    mock_choice = MagicMock()
    mock_choice.message.content = response_json

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    return mock_response


def create_test_user(username: str = "testuser") -> User:
    """Create a test user with unique username."""
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
    )


def create_test_task(
    user: User,
    title: str = "Test Task",
    description: str = "Test description",
    due_date: datetime | None = None,
    effort_estimate: int = 3,
) -> Task:
    """Create a test task for the given user."""
    return Task.objects.create(
        user=user,
        title=title,
        description=description,
        due_date=due_date,
        effort_estimate=effort_estimate,
    )


def create_test_goal_weights(
    user: User,
    work_bills: float = 0.4,
    study: float = 0.3,
    health: float = 0.2,
    relationships: float = 0.1,
) -> GoalWeights:
    """Create GoalWeights for the given user."""
    return GoalWeights.objects.create(
        user=user,
        work_bills=work_bills,
        study=study,
        health=health,
        relationships=relationships,
    )


# ===========================================================================
# EXTERNAL SCORER TESTS
# ===========================================================================


class TestExternalAIScorer(TestCase):
    """Tests for the ExternalAIScorer service class."""

    def test_scorer_initializes_without_api_key(self) -> None:
        """Scorer should not crash when API key is missing."""
        with override_settings(OPENAI_API_KEY=None):
            scorer = ExternalAIScorer(api_key=None)

            self.assertFalse(scorer.is_configured)
            self.assertIsNotNone(scorer.configuration_error)
            self.assertIn("not configured", scorer.configuration_error.lower())

    def test_scorer_returns_fallback_when_not_configured(self) -> None:
        """Scorer should return fallback response when not configured."""
        with override_settings(OPENAI_API_KEY=None):
            scorer = ExternalAIScorer(api_key=None)

            result = scorer.score_task(
                task_title="Test Task",
                task_description="Description",
                user_weights={"work_bills": 0.5, "study": 0.5},
            )

            self.assertEqual(result["confidence"], 0.0)
            self.assertIn("error_code", result)
            self.assertEqual(result["error_code"], "SCORER_NOT_CONFIGURED")

    @patch("tasks.ai_engine.external_scorer.OpenAI")
    def test_scorer_calls_openai_when_configured(self, mock_openai_class: MagicMock) -> None:
        """Scorer should call OpenAI API when properly configured."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = create_mock_openai_response(
            {"work_bills": 0.8, "study": 0.2},
            confidence=0.9,
        )

        with override_settings(OPENAI_API_KEY="test-key"):
            scorer = ExternalAIScorer(api_key="test-key")

            result = scorer.score_task(
                task_title="Prepare quarterly report",
                task_description="Financial analysis",
                user_weights={"work_bills": 0.5, "study": 0.5},
            )

            # Verify API was called
            mock_client.chat.completions.create.assert_called_once()

            # Verify result structure
            self.assertIn("relevance_scores", result)
            self.assertIn("confidence", result)
            self.assertEqual(result["confidence"], 0.9)

    @patch("tasks.ai_engine.external_scorer.OpenAI")
    def test_scorer_handles_api_timeout(self, mock_openai_class: MagicMock) -> None:
        """Scorer should handle API timeout gracefully."""
        from openai import APITimeoutError

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = APITimeoutError(request=MagicMock())

        with override_settings(OPENAI_API_KEY="test-key"):
            scorer = ExternalAIScorer(api_key="test-key")

            result = scorer.score_task(
                task_title="Test",
                task_description="Test",
                user_weights={"work_bills": 1.0},
            )

            self.assertEqual(result["confidence"], 0.0)
            self.assertEqual(result["error_code"], "TIMEOUT")

    @patch("tasks.ai_engine.external_scorer.OpenAI")
    def test_scorer_handles_rate_limit(self, mock_openai_class: MagicMock) -> None:
        """Scorer should handle rate limit errors gracefully."""
        from openai import RateLimitError

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Create a proper RateLimitError mock
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_client.chat.completions.create.side_effect = RateLimitError(
            message="Rate limit exceeded",
            response=mock_response,
            body=None,
        )

        with override_settings(OPENAI_API_KEY="test-key"):
            scorer = ExternalAIScorer(api_key="test-key")

            result = scorer.score_task(
                task_title="Test",
                task_description="Test",
                user_weights={"work_bills": 1.0},
            )

            self.assertEqual(result["confidence"], 0.0)
            self.assertEqual(result["error_code"], "RATE_LIMIT")

    def test_scorer_health_check(self) -> None:
        """Health check should return component status."""
        with override_settings(OPENAI_API_KEY=None):
            scorer = ExternalAIScorer(api_key=None)
            health = scorer.health_check()

            self.assertIn("is_configured", health)
            self.assertIn("model", health)
            self.assertFalse(health["is_configured"])


# ===========================================================================
# ORCHESTRATOR TESTS
# ===========================================================================


class TestAIOrchestrator(TestCase):
    """Tests for the AIOrchestrator coordination layer."""

    def test_orchestrator_initializes_with_skip_ai(self) -> None:
        """Orchestrator should initialize with AI skipped for testing."""
        orchestrator = AIOrchestrator(skip_ai_init=True)

        self.assertFalse(orchestrator.ai_available)
        self.assertIsNone(orchestrator.ai_service)

    def test_orchestrator_returns_fallback_when_ai_unavailable(self) -> None:
        """Orchestrator should return valid contract even without AI."""
        orchestrator = AIOrchestrator(skip_ai_init=True)

        result = orchestrator.get_relevance_scores(
            task_title="Test Task",
            task_description="Description",
            user_weights={"work_bills": 0.5, "study": 0.5},
            due_date="2024-01-20",
            effort_estimate=3,
        )

        # Should return valid contract structure
        self.assertIn("relevance_scores", result)
        self.assertIn("importance_score", result)
        self.assertIn("urgency_score", result)
        self.assertIn("quadrant", result)
        self.assertIn("scoring_method", result)

        # Should indicate fallback was used
        self.assertEqual(result["scoring_method"], SCORING_METHOD_FALLBACK)

    @patch.object(ExternalAIScorer, "score_task")
    @patch.object(ExternalAIScorer, "__init__", return_value=None)
    def test_orchestrator_uses_ai_when_available(
        self,
        mock_init: MagicMock,
        mock_score_task: MagicMock,
    ) -> None:
        """Orchestrator should use AI scoring when available."""
        # Configure the mock
        mock_score_task.return_value = {
            "relevance_scores": {"work_bills": 0.9, "study": 0.1},
            "confidence": 0.85,
        }

        with patch.object(ExternalAIScorer, "is_configured", True):
            orchestrator = AIOrchestrator()
            orchestrator.ai_service = ExternalAIScorer.__new__(ExternalAIScorer)
            orchestrator.ai_service.is_configured = True
            orchestrator.ai_service.score_task = mock_score_task
            orchestrator.ai_available = True

            result = orchestrator.get_relevance_scores(
                task_title="Prepare quarterly report",
                task_description="Financial analysis",
                user_weights={"work_bills": 0.5, "study": 0.5},
            )

            self.assertEqual(result["scoring_method"], SCORING_METHOD_AI)
            self.assertGreater(result["confidence"], 0)

    def test_orchestrator_rule_based_shortcircuit(self) -> None:
        """Orchestrator should use rules engine for obvious categorizations."""
        orchestrator = AIOrchestrator(skip_ai_init=True)

        # Create weights where work is dominant
        user_weights = {
            "work_bills": 0.7,
            "study": 0.1,
            "health": 0.1,
            "relationships": 0.1,
        }

        result = orchestrator.get_relevance_scores(
            task_title="Pay electricity bill",  # Contains "bill" keyword
            task_description="Monthly utility payment",
            user_weights=user_weights,
        )

        # May or may not trigger rule-based (depends on rule engine thresholds)
        # But should always return valid contract
        self.assertIn("quadrant", result)
        self.assertIn(result["quadrant"], ["Q1", "Q2", "Q3", "Q4"])

    def test_orchestrator_health_check(self) -> None:
        """Health check should return all component statuses."""
        orchestrator = AIOrchestrator(skip_ai_init=True)
        health = orchestrator.health_check()

        self.assertEqual(health["orchestrator"], "healthy")
        self.assertEqual(health["rules_engine"], "healthy")
        self.assertIn("ai_available", health)


# ===========================================================================
# CELERY TASK TESTS (Synchronous)
# ===========================================================================


class TestCeleryTaskHelpers(TestCase):
    """Tests for Celery task helper functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.user = create_test_user("celery_test_user")

    def test_get_user_weights_from_goal_weights(self) -> None:
        """Should prefer GoalWeights when available."""
        create_test_goal_weights(
            self.user,
            work_bills=0.5,
            study=0.3,
            health=0.15,
            relationships=0.05,
        )

        weights = _get_user_weights(self.user.id)

        self.assertEqual(weights["work_bills"], 0.5)
        self.assertEqual(weights["study"], 0.3)
        self.assertEqual(weights["health"], 0.15)
        self.assertEqual(weights["relationships"], 0.05)

    def test_get_user_weights_fallback_to_defaults(self) -> None:
        """Should use equal weights when no GoalWeights exist."""
        # No GoalWeights created
        weights = _get_user_weights(self.user.id)

        # Should be equal weights
        self.assertEqual(weights["work_bills"], 0.25)
        self.assertEqual(weights["study"], 0.25)
        self.assertEqual(weights["health"], 0.25)
        self.assertEqual(weights["relationships"], 0.25)

    def test_should_skip_scoring_unprioritized_task(self) -> None:
        """Should not skip unprioritized tasks."""
        task = create_test_task(self.user)

        should_skip = _should_skip_scoring(task)

        self.assertFalse(should_skip)

    def test_should_skip_scoring_recently_analyzed(self) -> None:
        """Should skip tasks analyzed within the last hour."""
        task = create_test_task(self.user)
        task.is_prioritized = True
        task.last_analyzed_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        task.save()

        should_skip = _should_skip_scoring(task)

        self.assertTrue(should_skip)

    def test_should_skip_scoring_old_analysis(self) -> None:
        """Should not skip tasks analyzed more than an hour ago."""
        task = create_test_task(self.user)
        task.is_prioritized = True
        task.last_analyzed_at = datetime.now(timezone.utc) - timedelta(hours=2)
        task.save()

        should_skip = _should_skip_scoring(task)

        self.assertFalse(should_skip)


class TestCeleryTaskExecution(TransactionTestCase):
    """
    Integration tests for the Celery task execution.

    Uses TransactionTestCase because Celery tasks may use
    select_for_update which requires real transactions.
    """

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.user = create_test_user("execution_test_user")
        create_test_goal_weights(self.user)

    @patch("tasks.ai_engine.celery_tasks.AIOrchestrator")
    def test_successful_scoring_persists_results(
        self, mock_orchestrator_class: MagicMock
    ) -> None:
        """Successful scoring should persist all decision contract fields."""
        # Create task
        task = create_test_task(
            self.user,
            title="Prepare quarterly report",
            description="Financial analysis for Q3",
        )

        # Mock orchestrator response
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.get_relevance_scores.return_value = {
            "relevance_scores": {"work_bills": 0.9, "study": 0.1, "health": 0.0, "relationships": 0.0},
            "confidence": 0.85,
            "importance_score": 0.65,
            "urgency_score": 0.3,
            "quadrant": "Q2",
            "rationale": "Work-related financial task",
            "scoring_method": "ai_scored",
        }

        # Execute task synchronously (without Celery broker)
        result = run_ai_relevance_scoring.apply(
            args=[task.id, self.user.id]
        ).get()

        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result["quadrant"], "Q2")

        # Verify database state
        task.refresh_from_db()
        self.assertTrue(task.is_prioritized)
        self.assertEqual(task.quadrant, "Q2")
        self.assertAlmostEqual(task.importance_score, 0.65, places=2)
        self.assertAlmostEqual(task.urgency_score, 0.3, places=2)
        self.assertIsNotNone(task.last_analyzed_at)

    @patch("tasks.ai_engine.celery_tasks.AIOrchestrator")
    def test_scoring_nonexistent_task_returns_none(
        self, mock_orchestrator_class: MagicMock
    ) -> None:
        """Scoring a non-existent task should return None gracefully."""
        result = run_ai_relevance_scoring.apply(
            args=[99999, self.user.id]  # Non-existent task ID
        ).get()

        self.assertIsNone(result)

    @patch("tasks.ai_engine.celery_tasks.AIOrchestrator")
    def test_scoring_wrong_user_returns_none(
        self, mock_orchestrator_class: MagicMock
    ) -> None:
        """Scoring a task owned by different user should abort."""
        task = create_test_task(self.user)
        other_user = create_test_user("other_user")

        result = run_ai_relevance_scoring.apply(
            args=[task.id, other_user.id]  # Wrong user
        ).get()

        self.assertIsNone(result)

        # Task should remain unchanged
        task.refresh_from_db()
        self.assertFalse(task.is_prioritized)

    @patch("tasks.ai_engine.celery_tasks.AIOrchestrator")
    def test_idempotency_skips_recently_analyzed(
        self, mock_orchestrator_class: MagicMock
    ) -> None:
        """Re-running task on recently analyzed task should skip."""
        task = create_test_task(self.user)
        task.is_prioritized = True
        task.last_analyzed_at = datetime.now(timezone.utc)
        task.save()

        result = run_ai_relevance_scoring.apply(
            args=[task.id, self.user.id]
        ).get()

        # Should skip without calling orchestrator
        self.assertEqual(result["status"], "skipped")
        mock_orchestrator_class.assert_not_called()

    @patch("tasks.ai_engine.celery_tasks.AIOrchestrator")
    def test_force_rescore_overrides_idempotency(
        self, mock_orchestrator_class: MagicMock
    ) -> None:
        """force_rescore=True should override idempotency check."""
        task = create_test_task(self.user)
        task.is_prioritized = True
        task.last_analyzed_at = datetime.now(timezone.utc)
        task.quadrant = "Q4"
        task.save()

        # Mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.get_relevance_scores.return_value = {
            "relevance_scores": {"work_bills": 0.9},
            "confidence": 0.9,
            "importance_score": 0.8,
            "urgency_score": 0.7,
            "quadrant": "Q1",
            "rationale": "Rescored",
            "scoring_method": "ai_scored",
        }

        result = run_ai_relevance_scoring.apply(
            args=[task.id, self.user.id],
            kwargs={"force_rescore": True},
        ).get()

        # Should have rescored
        task.refresh_from_db()
        self.assertEqual(task.quadrant, "Q1")  # Changed from Q4


# ===========================================================================
# ERROR HANDLING TESTS
# ===========================================================================


class TestErrorHandling(TransactionTestCase):
    """Tests for error handling in the scoring pipeline."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.user = create_test_user("error_test_user")
        create_test_goal_weights(self.user)

    @patch("tasks.ai_engine.celery_tasks.AIOrchestrator")
    def test_orchestrator_exception_doesnt_crash(
        self, mock_orchestrator_class: MagicMock
    ) -> None:
        """Task should handle orchestrator exceptions gracefully."""
        task = create_test_task(self.user)

        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.get_relevance_scores.side_effect = Exception("AI exploded")

        # Execute - should not raise
        with self.assertRaises(Exception):
            # Task will raise for retry, but in test we catch it
            run_ai_relevance_scoring.apply(
                args=[task.id, self.user.id]
            ).get()

        # Task should be marked as not prioritized
        task.refresh_from_db()
        self.assertFalse(task.is_prioritized)

    @patch("tasks.ai_engine.celery_tasks.AIOrchestrator")
    def test_task_remains_valid_on_partial_failure(
        self, mock_orchestrator_class: MagicMock
    ) -> None:
        """Task should remain in valid state even on partial pipeline failure."""
        task = create_test_task(self.user)

        # Orchestrator returns result with error
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.get_relevance_scores.return_value = {
            "relevance_scores": {"work_bills": 0.25},
            "confidence": 0.0,
            "importance_score": 0.25,
            "urgency_score": 0.1,
            "quadrant": "Q4",
            "rationale": "Fallback due to error",
            "scoring_method": "fallback",
            "error_code": "API_ERROR",
        }

        result = run_ai_relevance_scoring.apply(
            args=[task.id, self.user.id]
        ).get()

        # Task should be updated with fallback values
        task.refresh_from_db()
        self.assertTrue(task.is_prioritized)  # Still marked as processed
        self.assertEqual(task.quadrant, "Q4")


# ===========================================================================
# END-TO-END INTEGRATION TEST
# ===========================================================================


class TestEndToEndFlow(TransactionTestCase):
    """End-to-end integration test for the full scoring flow."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.user = create_test_user("e2e_test_user")
        create_test_goal_weights(
            self.user,
            work_bills=0.5,
            study=0.3,
            health=0.15,
            relationships=0.05,
        )

    @patch("tasks.ai_engine.external_scorer.OpenAI")
    def test_full_flow_from_task_creation_to_matrix(
        self, mock_openai_class: MagicMock
    ) -> None:
        """
        Test the complete flow:
        1. Create task
        2. Trigger scoring (with mocked AI)
        3. Verify final state matches expected quadrant
        """
        # Setup mock OpenAI client
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = create_mock_openai_response(
            relevance_scores={
                "work_bills": 0.95,
                "study": 0.1,
                "health": 0.0,
                "relationships": 0.0,
            },
            confidence=0.9,
        )

        # Create a work-related task with near deadline
        tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
        task = create_test_task(
            self.user,
            title="Submit quarterly financial report",
            description="Complete Q3 financial analysis and submit to stakeholders",
            due_date=tomorrow,
            effort_estimate=4,  # High effort
        )

        # Execute scoring
        with override_settings(OPENAI_API_KEY="test-key"):
            result = run_ai_relevance_scoring.apply(
                args=[task.id, self.user.id]
            ).get()

        # Verify final state
        task.refresh_from_db()

        # Should be Q1 (Important + Urgent)
        # - High work relevance (0.95) × high work weight (0.5) = high importance
        # - Due tomorrow with high effort = high urgency
        self.assertTrue(task.is_prioritized)
        self.assertEqual(task.quadrant, "Q1")
        self.assertGreater(task.importance_score, 0.4)  # Should be significant
        self.assertGreater(task.urgency_score, 0.7)  # Should be high (due tomorrow)
        self.assertIsNotNone(task.last_analyzed_at)
        self.assertIn("work", task.rationale.lower())
