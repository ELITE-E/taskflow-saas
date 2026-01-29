# tasks/ai_engine/__init__.py
"""
AI Engine Package
=================

This package contains all the core mathematical and AI-driven logic
for the Strategic Task Prioritization System.

Modules:
--------
- orchestrator: Central coordination layer for scoring pipeline
- urgency: Deterministic urgency score computation
- external_scorer: OpenAI API integration for relevance scoring
- rules: Rule-based short-circuit engine
- cache: Redis-backed caching layer for AI responses
- celery_tasks: Asynchronous task processing via Celery

Architecture:
-------------
All prioritization logic flows through the AIOrchestrator, which
coordinates between rule-based shortcuts, cached responses, and
live AI scoring. The orchestrator returns a "decision contract":

    {
        "relevance_scores": {...},
        "confidence": float,
        "importance_score": float,
        "urgency_score": float,
        "quadrant": str,
        "rationale": str,
        "scoring_method": str,
        "error_code": str | None
    }

Scoring Methods:
----------------
- "rule_based": Deterministic rules engine (fast, no API call)
- "cached": Retrieved from Redis cache
- "ai_scored": Fresh AI scoring via OpenAI
- "fallback": Default values (AI unavailable or error)

Usage:
------
    from tasks.ai_engine import AIOrchestrator

    orchestrator = AIOrchestrator()
    result = orchestrator.get_relevance_scores(
        task_title="My Task",
        task_description="Description",
        user_weights={"work_bills": 0.5, "study": 0.5},
    )
"""

from .cache import AIScoringCache
from .celery_tasks import run_ai_relevance_scoring
from .external_scorer import ExternalAIScorer
from .orchestrator import (
    SCORING_METHOD_AI,
    SCORING_METHOD_CACHE,
    SCORING_METHOD_FALLBACK,
    SCORING_METHOD_RULES,
    AIOrchestrator,
)
from .rules import DecisionEngine
from .urgency import compute_urgency

__all__ = [
    # Core classes
    "AIOrchestrator",
    "ExternalAIScorer",
    "DecisionEngine",
    "AIScoringCache",
    # Functions
    "compute_urgency",
    "run_ai_relevance_scoring",
    # Constants
    "SCORING_METHOD_AI",
    "SCORING_METHOD_CACHE",
    "SCORING_METHOD_FALLBACK",
    "SCORING_METHOD_RULES",
]
