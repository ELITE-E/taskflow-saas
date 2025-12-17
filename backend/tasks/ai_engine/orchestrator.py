# tasks/ai_engine/orchestrator.py

import logging
from typing import Dict, Any, Optional
from .rules import DecisionEngine
from .cache import AIScoringCache
from ..services import ExternalAIScorer

# Configure logging for pipeline auditing
logger = logging.getLogger(__name__)

class AIOrchestrator:
    """
    The central coordination layer for task relevance scoring.
    
    This orchestrator implements a tiered intelligence pipeline:
    1. Static Analysis: Rule-based engine to short-circuit deterministic tasks.
    2. Memoization: Cache lookup to avoid redundant external API latency.
    3. LLM Inference: Structured call to OpenAI as a final resort.
    
    The orchestrator ensures high performance, cost control, and a 
    consistent interface for the downstream Weighted Average Formula.
    """

    def __init__(self):
        """Initializes the three distinct components of the scoring pipeline."""
        self.rules_engine = DecisionEngine()
        self.cache_manager = AIScoringCache()
        self.ai_service = ExternalAIScorer()

    def get_relevance_scores(
        self, 
        task_title: str, 
        task_description: str, 
        user_weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Coordinates the flow of data to obtain task relevance scores.

        Args:
            task_title: Title of the task to be analyzed.
            task_description: Detailed description of the task.
            user_weights: Dictionary of strategic goals and their associated weights.

        Returns:
            A dictionary containing 'relevance_scores' and 'confidence'.
        """
        
        # --- LAYER 1: RULE-BASED SHORT-CIRCUIT ---
        # Checks for high-certainty deterministic outcomes (e.g., "Pay electricity bill")
        should_skip, deterministic_scores = self.rules_engine.get_short_circuit_decision(
            task_title, 
            task_description, 
            user_weights
        )
        
        if should_skip and deterministic_scores:
            logger.info(f"Orchestrator: Rule-based skip for '{task_title}'")
            return deterministic_scores

        # --- LAYER 2 & 3: CACHE-WRAPPED AI SCORING ---
        # The cache manager handles SHA256 hashing of inputs. If a cache miss occurs, 
        # it executes the lambda function calling the ExternalAIScorer.
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
            return final_scores

        except Exception as e:
            logger.exception(f"Orchestrator: Pipeline failure for '{task_title}': {str(e)}")
            # Fail-safe: Return a neutral relevance profile to prevent system-wide crashes
            return {
                "relevance_scores": {domain: 0.25 for domain in user_weights.keys()},
                "confidence": 0.0
            }