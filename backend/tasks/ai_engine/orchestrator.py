# tasks/ai_engine/orchestrator.py

import logging
from typing import Dict, Any, Optional
from .rules import DecisionEngine
from .cache import AIScoringCache
from ..services import ExternalAIScorer
from .urgency import compute_urgency

# Configure logging for pipeline auditing
logger = logging.getLogger(__name__)

class AIOrchestrator:
    """
    The central coordination layer for task relevance scoring.
    Orchestrator now returns the full decision contract:
      {
        relevance_scores,
        confidence,
        importance_score,
        urgency_score,
        quadrant,
        rationale
      }
    """

    def __init__(self):
        """Initializes the three distinct components of the scoring pipeline."""
        self.rules_engine = DecisionEngine()
        self.cache_manager = AIScoringCache()
        self.ai_service = ExternalAIScorer()

    def _compute_importance(self, relevance: Dict[str, float], weights: Dict[str, float]) -> float:
        total = 0.0
        for k, v in relevance.items():
            w = weights.get(k, 0.0)
            total += float(v) * float(w)
        # clamp 0..1
        total = max(0.0, min(1.0, total))
        return round(total, 4)

    def _compute_quadrant(self, importance: float, urgency: float) -> str:
        if importance >= 0.5 and urgency >= 0.5:
            return 'Q1'
        if importance >= 0.5 and urgency < 0.5:
            return 'Q2'
        if importance < 0.5 and urgency >= 0.5:
            return 'Q3'
        return 'Q4'

    def _make_rationale(self, relevance: Dict[str, float], importance: float, urgency: float) -> str:
        if not relevance:
            return "No relevance data."
        dominant = max(relevance.items(), key=lambda x: x[1])
        domain, score = dominant[0], dominant[1]
        return f"Dominant: {domain} ({score:.2f}); importance {importance:.2f}, urgency {urgency:.2f}."

    def get_relevance_scores(
        self, 
        task_title: str, 
        task_description: str, 
        user_weights: Dict[str, float],
        due_date: Optional[str] = None,
        effort_estimate: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Coordinates the flow of data to obtain task relevance scores and compute
        the final decision contract values.
        """

        # --- LAYER 1: RULE-BASED SHORT-CIRCUIT ---
        should_skip, deterministic_scores = self.rules_engine.get_short_circuit_decision(
            task_title, 
            task_description, 
            user_weights
        )
        
        if should_skip and deterministic_scores:
            logger.info(f"Orchestrator: Rule-based skip for '{task_title}'")
            relevance = deterministic_scores.get("relevance_scores", deterministic_scores)
            confidence = deterministic_scores.get("confidence", 1.0)
        else:
            # --- LAYER 2 & 3: CACHE-WRAPPED AI SCORING ---
            try:
                final_scores = self.cache_manager.get_or_set_score(
                    task_title=task_title,
                    task_description=task_description,
                    user_weights=user_weights,
                    scoring_func=lambda: self.ai_service.score_task(
                        task_title, 
                        task_description, 
                        user_weights
                    )
                )
                relevance = final_scores.get("relevance_scores", final_scores)
                confidence = final_scores.get("confidence", 0.0)
            except Exception as e:
                logger.exception(f"Orchestrator: Pipeline failure for '{task_title}': {str(e)}")
                relevance = {k: 0.25 for k in user_weights.keys()}
                confidence = 0.0

        # Compute derived decision contract values
        importance = self._compute_importance(relevance, user_weights)
        urgency = compute_urgency(due_date, effort_estimate)
        quadrant = self._compute_quadrant(importance, urgency)
        rationale = self._make_rationale(relevance, importance, urgency)

        return {
            "relevance_scores": relevance,
            "confidence": float(confidence),
            "importance_score": importance,
            "urgency_score": urgency,
            "quadrant": quadrant,
            "rationale": rationale
        }