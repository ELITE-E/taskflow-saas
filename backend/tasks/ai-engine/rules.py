# tasks/ai_engine/rules.py

import logging
from typing import Dict, Any, Tuple, Optional, List

# Configure logging for rule-engine auditing
logger = logging.getLogger(__name__)

class DecisionEngine:
    """
    A conservative rule-based engine to short-circuit AI scoring.
    
    This engine evaluates deterministic criteria to decide if a task's 
    relevance can be inferred without LLM intervention, reducing 
    latency and API costs.
    """

    # Keyword mappings for high-certainty domain detection
    DOMAIN_KEYWORDS = {
        "work_bills": ["invoice", "pay", "bill", "salary", "client", "meeting", "deadline"],
        "study": ["exam", "course", "assignment", "read", "lecture", "research", "thesis"],
        "health": ["gym", "workout", "doctor", "appointment", "medication", "run", "diet"],
        "relationships": ["date", "anniversary", "call mom", "dinner", "gift", "visit", "family"]
    }

    def __init__(self, dominance_threshold: float = 0.6, ceiling_others: float = 0.2):
        """
        Args:
            dominance_threshold: The weight required for a goal to be considered dominant.
            ceiling_others: The maximum weight allowed for non-dominant goals to skip AI.
        """
        self.dominance_threshold = dominance_threshold
        self.ceiling_others = ceiling_others

    def get_short_circuit_decision(
        self, 
        title: str, 
        description: str, 
        user_weights: Dict[str, float]
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Determines if AI scoring can be skipped based on deterministic axioms.

        Returns:
            Tuple: (should_skip: bool, precomputed_scores: Optional[dict])
        """
        title_lower = title.lower()
        desc_lower = description.lower()

        # Rule 1: Evaluate Dominant Weight Axiom
        # If one goal is heavily prioritized and others are negligible.
        is_dominant, dominant_domain = self._check_weight_dominance(user_weights)

        if is_dominant and dominant_domain:
            # Rule 2 & 3: Keyword-Goal Certainty / Single-Domain Tasks
            # Check if task content aligns strongly with the dominant domain.
            if self._has_keyword_match(title_lower, desc_lower, dominant_domain):
                logger.info(f"Short-circuit triggered for domain: {dominant_domain}")
                return True, self._generate_deterministic_scores(dominant_domain, user_weights)

        return False, None

    def _check_weight_dominance(self, weights: Dict[str, float]) -> Tuple[bool, Optional[str]]:
        """Identifies if a single weight exceeds the dominance threshold."""
        if not weights:
            return False, None

        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        max_domain, max_weight = sorted_weights[0]
        
        # Axiom check: Max weight >= threshold AND all others <= ceiling
        if max_weight >= self.dominance_threshold:
            others_under_ceiling = all(w <= self.ceiling_others for d, w in sorted_weights[1:])
            if others_under_ceiling:
                return True, max_domain
        
        return False, None

    def _has_keyword_match(self, title: str, description: str, domain: str) -> bool:
        """Checks if domain-specific keywords exist in title or description."""
        keywords = self.DOMAIN_KEYWORDS.get(domain, [])
        content = f"{title} {description}"
        return any(word in content for word in keywords)

    def _generate_deterministic_scores(
        self, 
        target_domain: str, 
        weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Produces the deterministic output contract.
        The target domain receives full relevance (1.0), others (0.0).
        """
        return {
            "relevance_scores": {
                domain: 1.0 if domain == target_domain else 0.0 
                for domain in weights.keys()
            },
            "confidence": 1.0
        }