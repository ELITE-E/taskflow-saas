# tasks/ai_engine/cache.py

import json
import hashlib
import logging
from typing import Dict, Any, Optional, Callable
from django.core.cache import cache
from django.conf import settings

# Configure logging for distributed systems monitoring
logger = logging.getLogger(__name__)

class AIScoringCache:
    """
    Performance optimization layer for AI-driven task prioritization.
    
    Implements a deterministic caching strategy using SHA256 hashing to 
    prevent redundant, high-latency, and costly external LLM invocations.
    
    Features:
    - Redis-backed persistence via Django's cache framework.
    - Deterministic key derivation based on input state.
    - Failure-transparent design with fallback to original service.
    """

    def __init__(
        self, 
        ttl: int = 86400, 
        version: str = "v1",
        cache_alias: str = "default"
    ):
        """
        Args:
            ttl: Time-to-live in seconds (default: 24 hours).
            version: Cache versioning to invalidate schemas during deployments.
            cache_alias: The Django cache alias to utilize.
        """
        self.ttl = getattr(settings, 'AI_CACHE_TTL', ttl)
        self.version = version
        self.cache_alias = cache_alias

    def get_or_set_score(
        self,
        task_title: str,
        task_description: str,
        user_weights: Dict[str, float],
        scoring_func: Callable[[], Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Retrieves a cached AI score or executes the scoring function on cache miss.

        Args:
            task_title: Input title for hashing.
            task_description: Input description for hashing.
            user_weights: Dictionary of weight keys/values for hashing.
            scoring_func: The expensive OpenAI service call to wrap.

        Returns:
            The relevance score dictionary, either from cache or live service.
        """
        
        # 1. Derive deterministic cache key
        cache_key = self._generate_key(task_title, task_description, user_weights)

        # 2. Attempt cache retrieval with graceful failure handling
        try:
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"AI Cache Hit: {cache_key}")
                return cached_result
        except Exception as e:
            # Transparently handle Redis connectivity issues
            logger.error(f"Redis retrieval failure: {str(e)}")

        # 3. Cache Miss: Execute expensive scoring operation
        logger.info(f"AI Cache Miss: {cache_key}. Invoking AI Service.")
        result = scoring_func()

        # 4. Persistence: Attempt to update cache for future requests
        try:
            # Verify result is not a fallback/empty before caching to prevent poisoning
            if result.get("confidence", 0) > 0:
                cache.set(cache_key, result, timeout=self.ttl)
        except Exception as e:
            logger.error(f"Redis persistence failure: {str(e)}")

        return result

    def _generate_key(
        self, 
        title: str, 
        description: str, 
        weights: Dict[str, float]
    ) -> str:
        """
        Creates a stable SHA256 hash from input parameters.
        
        Keys are sorted to ensure that identical weight dictionaries 
        generate identical hashes regardless of insertion order.
        """
        # Create a stable, sorted representation of the input payload
        payload = {
            "title": title.strip().lower(),
            "description": description.strip().lower(),
            "weights": sorted(weights.items()),
            "version": self.version
        }
        
        serialized_payload = json.dumps(payload, sort_keys=True)
        hash_digest = hashlib.sha256(serialized_payload.encode()).hexdigest()
        
        return f"ai_score_{self.version}_{hash_digest}"