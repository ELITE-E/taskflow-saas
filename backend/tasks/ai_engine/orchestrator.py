# tasks/ai_engine/orchestrator.py
"""
AI Orchestrator
===============

The central coordination layer for the Strategic Task Prioritization System.

This module is the SINGLE SOURCE OF TRUTH for the prioritization pipeline.
All task scoring flows through this orchestrator, which coordinates:

1. Rule-based short-circuits (deterministic, fast)
2. Cache lookups (Redis-backed, prevents redundant API calls)
3. AI scoring (OpenAI API for semantic relevance)
4. Mathematical computation (urgency, importance, quadrant assignment)

Pipeline Flow:
--------------
    Task Input
        │
        ▼
    [1] Rule Engine Check ─────► Short-circuit if deterministic
        │
        ▼
    [2] Cache Lookup ──────────► Return cached result if hit
        │
        ▼
    [3] AI Scorer ─────────────► Call OpenAI API
        │
        ▼
    [4] Compute Decision ──────► Urgency + Importance + Quadrant
        │
        ▼
    Decision Contract Output

Decision Contract:
------------------
    {
        "relevance_scores": Dict[str, float],  # Domain relevance (0-1)
        "confidence": float,                    # AI confidence (0=fallback)
        "importance_score": float,              # Weighted importance (0-1)
        "urgency_score": float,                 # Time-based urgency (0-1)
        "quadrant": str,                        # Q1/Q2/Q3/Q4
        "rationale": str,                       # Human-readable explanation
        "scoring_method": str,                  # How the score was derived
        "error_code": str | None               # Present if scoring failed
    }
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .cache import AIScoringCache
from .external_scorer import ExternalAIScorer
from .rules import DecisionEngine
from .urgency import compute_urgency

# Configure logging for pipeline auditing
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scoring Method Constants
# ---------------------------------------------------------------------------

SCORING_METHOD_RULES = "rule_based"
SCORING_METHOD_CACHE = "cached"
SCORING_METHOD_AI = "ai_scored"
SCORING_METHOD_FALLBACK = "fallback"


# ---------------------------------------------------------------------------
# Main Orchestrator Class
# ---------------------------------------------------------------------------


class AIOrchestrator:
    """
    The central coordination layer for task relevance scoring.

    This class orchestrates the entire prioritization pipeline, ensuring:
    - Deterministic fallbacks when AI is unavailable
    - Caching to reduce API costs
    - Graceful degradation on any failure
    - Complete audit trail via logging

    The orchestrator NEVER raises exceptions to callers. It always returns
    a valid decision contract, using fallback values when necessary.

    Attributes:
        rules_engine (DecisionEngine): Rule-based short-circuit engine.
        cache_manager (AIScoringCache): Redis-backed cache layer.
        ai_service (ExternalAIScorer): OpenAI API integration.
        ai_available (bool): Whether AI scoring is available.
    """

    def __init__(
        self,
        skip_ai_init: bool = False,
    ) -> None:
        """
        Initialize the orchestrator with all pipeline components.

        Args:
            skip_ai_init: If True, skip AI service initialization (for testing).
        """
        logger.debug("AIOrchestrator: Initializing pipeline components...")

        # Initialize rule engine (always available, no external deps)
        self.rules_engine = DecisionEngine()
        logger.debug("AIOrchestrator: Rule engine initialized")

        # Initialize cache manager (graceful fallback if Redis unavailable)
        self.cache_manager = AIScoringCache()
        logger.debug("AIOrchestrator: Cache manager initialized")

        # Initialize AI service with graceful handling
        if skip_ai_init:
            self.ai_service: Optional[ExternalAIScorer] = None
            self.ai_available = False
            logger.info("AIOrchestrator: AI service skipped (skip_ai_init=True)")
        else:
            self.ai_service = ExternalAIScorer()
            self.ai_available = self.ai_service.is_configured
            if self.ai_available:
                logger.info("AIOrchestrator: AI service initialized and available")
            else:
                logger.warning(
                    f"AIOrchestrator: AI service not available - "
                    f"{self.ai_service.configuration_error}"
                )

    def get_relevance_scores(
        self,
        task_title: str,
        task_description: str,
        user_weights: Dict[str, float],
        due_date: Optional[str] = None,
        effort_estimate: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Coordinate the full scoring pipeline and return a decision contract.

        This is the main entry point for task prioritization. It orchestrates
        all pipeline layers and ensures a valid contract is always returned.

        Pipeline Layers:
        1. Rule-based short-circuit (if applicable)
        2. Cache lookup
        3. AI scoring (if cache miss and AI available)
        4. Fallback scoring (if all else fails)
        5. Mathematical computation (urgency, importance, quadrant)

        Args:
            task_title: The title of the task being scored.
            task_description: Detailed description of the task.
            user_weights: Dictionary of domain weights (must sum to 1.0).
            due_date: Optional ISO date string (YYYY-MM-DD) for urgency calc.
            effort_estimate: Optional effort level (1-5) for urgency calc.

        Returns:
            Complete decision contract dictionary. Never raises exceptions.
        """
        logger.info(f"AIOrchestrator: Starting pipeline for '{task_title}'")

        # Track scoring metadata
        scoring_method: str = SCORING_METHOD_FALLBACK
        error_code: Optional[str] = None
        error_message: Optional[str] = None

        # Default relevance (used if all layers fail)
        domains = list(user_weights.keys())
        relevance: Dict[str, float] = {k: 0.25 for k in domains}
        confidence: float = 0.0

        # ─────────────────────────────────────────────────────────────────────
        # LAYER 1: RULE-BASED SHORT-CIRCUIT
        # ─────────────────────────────────────────────────────────────────────
        try:
            should_skip, deterministic_scores = self.rules_engine.get_short_circuit_decision(
                task_title,
                task_description,
                user_weights,
            )

            if should_skip and deterministic_scores:
                logger.info(
                    f"AIOrchestrator: Rule-based short-circuit for '{task_title}'"
                )
                relevance = deterministic_scores.get("relevance_scores", relevance)
                confidence = deterministic_scores.get("confidence", 1.0)
                scoring_method = SCORING_METHOD_RULES

        except Exception as e:
            logger.warning(f"AIOrchestrator: Rule engine failed: {e}")
            # Continue to next layer

        # ─────────────────────────────────────────────────────────────────────
        # LAYER 2 & 3: CACHE-WRAPPED AI SCORING
        # ─────────────────────────────────────────────────────────────────────
        if scoring_method == SCORING_METHOD_FALLBACK:
            try:
                # Define the AI scoring function for cache wrapper
                def ai_scoring_func() -> Dict[str, Any]:
                    if not self.ai_available or self.ai_service is None:
                        logger.warning(
                            "AIOrchestrator: AI service not available, returning fallback"
                        )
                        return {
                            "relevance_scores": {k: 0.25 for k in domains},
                            "confidence": 0.0,
                            "error_code": "AI_NOT_CONFIGURED",
                            "error_message": "AI service is not configured",
                        }

                    return self.ai_service.score_task(
                        task_title,
                        task_description,
                        user_weights,
                    )

                # Attempt cache lookup, then AI scoring on miss
                final_scores = self.cache_manager.get_or_set_score(
                    task_title=task_title,
                    task_description=task_description,
                    user_weights=user_weights,
                    scoring_func=ai_scoring_func,
                )

                relevance = final_scores.get("relevance_scores", relevance)
                confidence = final_scores.get("confidence", 0.0)
                error_code = final_scores.get("error_code")
                error_message = final_scores.get("error_message")

                # Determine scoring method from results
                if error_code:
                    scoring_method = SCORING_METHOD_FALLBACK
                    logger.warning(
                        f"AIOrchestrator: Scoring returned error: {error_code}"
                    )
                elif confidence > 0:
                    # Check if this was a cache hit or fresh AI score
                    # (Cache manager doesn't distinguish, so we mark as AI)
                    scoring_method = SCORING_METHOD_AI
                    logger.info(
                        f"AIOrchestrator: AI scoring successful "
                        f"(confidence={confidence:.2f})"
                    )
                else:
                    scoring_method = SCORING_METHOD_FALLBACK
                    logger.warning(
                        "AIOrchestrator: AI returned zero confidence, using fallback"
                    )

            except Exception as e:
                logger.exception(
                    f"AIOrchestrator: Pipeline failure for '{task_title}': {e}"
                )
                error_code = "PIPELINE_ERROR"
                error_message = str(e)
                scoring_method = SCORING_METHOD_FALLBACK

        # ─────────────────────────────────────────────────────────────────────
        # LAYER 4: COMPUTE DERIVED VALUES
        # ─────────────────────────────────────────────────────────────────────
        importance = self._compute_importance(relevance, user_weights)
        urgency = compute_urgency(due_date, effort_estimate)
        quadrant = self._compute_quadrant(importance, urgency)
        rationale = self._make_rationale(relevance, importance, urgency, scoring_method)

        # ─────────────────────────────────────────────────────────────────────
        # BUILD FINAL CONTRACT
        # ─────────────────────────────────────────────────────────────────────
        contract: Dict[str, Any] = {
            "relevance_scores": relevance,
            "confidence": float(confidence),
            "importance_score": importance,
            "urgency_score": urgency,
            "quadrant": quadrant,
            "rationale": rationale,
            "scoring_method": scoring_method,
        }

        # Include error info if present
        if error_code:
            contract["error_code"] = error_code
        if error_message:
            contract["error_message"] = error_message

        logger.info(
            f"AIOrchestrator: Pipeline complete for '{task_title}' - "
            f"quadrant={quadrant}, importance={importance:.2f}, "
            f"urgency={urgency:.2f}, method={scoring_method}"
        )

        return contract

    def _compute_importance(
        self, relevance: Dict[str, float], weights: Dict[str, float]
    ) -> float:
        """
        Calculate weighted importance score from relevance and user weights.

        Formula: importance = Σ(relevance[domain] × weight[domain])

        Args:
            relevance: Dictionary of domain relevance scores (0-1).
            weights: Dictionary of user-defined domain weights (should sum to 1).

        Returns:
            Importance score in range [0.0, 1.0], rounded to 4 decimal places.
        """
        total: float = 0.0

        for domain, rel_score in relevance.items():
            weight = weights.get(domain, 0.0)
            total += float(rel_score) * float(weight)

        # Clamp to [0, 1] and round for consistency
        total = max(0.0, min(1.0, total))
        return round(total, 4)

    def _compute_quadrant(self, importance: float, urgency: float) -> str:
        """
        Assign Eisenhower Matrix quadrant based on importance and urgency.

        Quadrant Assignment:
        - Q1 (Do Now): Urgent AND Important (both >= 0.5)
        - Q2 (Schedule): Important but NOT Urgent (importance >= 0.5, urgency < 0.5)
        - Q3 (Delegate): Urgent but NOT Important (urgency >= 0.5, importance < 0.5)
        - Q4 (Delete): Neither Urgent nor Important (both < 0.5)

        Args:
            importance: Importance score (0-1).
            urgency: Urgency score (0-1).

        Returns:
            Quadrant identifier: 'Q1', 'Q2', 'Q3', or 'Q4'.
        """
        # Threshold is 0.5 (inclusive for "high" classification)
        is_important = importance >= 0.5
        is_urgent = urgency >= 0.5

        if is_important and is_urgent:
            return "Q1"  # Do Now
        elif is_important and not is_urgent:
            return "Q2"  # Schedule
        elif not is_important and is_urgent:
            return "Q3"  # Delegate
        else:
            return "Q4"  # Delete/Drop

    def _make_rationale(
        self,
        relevance: Dict[str, float],
        importance: float,
        urgency: float,
        scoring_method: str,
    ) -> str:
        """
        Generate human-readable explanation of the prioritization decision.

        Args:
            relevance: Dictionary of domain relevance scores.
            importance: Calculated importance score.
            urgency: Calculated urgency score.
            scoring_method: How the relevance was determined.

        Returns:
            Rationale string explaining the decision.
        """
        if not relevance:
            return "No relevance data available."

        # Find the dominant domain
        dominant = max(relevance.items(), key=lambda x: x[1])
        domain, score = dominant[0], dominant[1]

        # Build rationale based on scoring method
        method_label = {
            SCORING_METHOD_RULES: "rule-based",
            SCORING_METHOD_CACHE: "cached",
            SCORING_METHOD_AI: "AI-scored",
            SCORING_METHOD_FALLBACK: "fallback",
        }.get(scoring_method, "unknown")

        return (
            f"Primary domain: {domain} ({score:.2f}). "
            f"Importance: {importance:.2f}, Urgency: {urgency:.2f}. "
            f"Method: {method_label}."
        )

    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on all orchestrator components.

        Returns:
            Dictionary with component health status.
        """
        ai_health = (
            self.ai_service.health_check() if self.ai_service else {"status": "skipped"}
        )

        return {
            "orchestrator": "healthy",
            "rules_engine": "healthy",
            "cache_manager": "healthy",
            "ai_service": ai_health,
            "ai_available": self.ai_available,
        }
