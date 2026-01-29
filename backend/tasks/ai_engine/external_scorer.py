# tasks/ai_engine/external_scorer.py
"""
External AI Scorer
==================

Service layer for AI-assisted task relevance scoring via OpenAI API.

This module is a pure service with NO Django ORM dependencies.
It handles prompt engineering, API communication, and response validation.

Design Principles:
------------------
1. Single Responsibility: Only handles OpenAI communication
2. Deterministic Output: Always returns a well-defined contract
3. Graceful Degradation: Returns safe fallbacks on any failure
4. Testable: Can be mocked without Django context
5. Fail-Safe Initialization: Never crashes on missing API key

Error Codes:
------------
- confidence: 0.0 indicates a fallback response (AI not available)
- confidence: > 0.0 indicates successful AI scoring
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from django.conf import settings

# ---------------------------------------------------------------------------
# OpenAI Imports with Graceful Handling
# ---------------------------------------------------------------------------
# Import all relevant exception types for comprehensive error handling
try:
    from openai import (
        APIConnectionError,
        APIError,
        APIStatusError,
        APITimeoutError,
        AuthenticationError,
        BadRequestError,
        ConflictError,
        InternalServerError,
        NotFoundError,
        OpenAI,
        PermissionDeniedError,
        RateLimitError,
        UnprocessableEntityError,
    )

    OPENAI_AVAILABLE = True
except ImportError:
    # OpenAI library not installed - system will use fallback mode
    OPENAI_AVAILABLE = False
    OpenAI = None  # type: ignore
    APIError = Exception  # type: ignore
    APIConnectionError = Exception  # type: ignore
    RateLimitError = Exception  # type: ignore
    APITimeoutError = Exception  # type: ignore
    AuthenticationError = Exception  # type: ignore
    APIStatusError = Exception  # type: ignore
    BadRequestError = Exception  # type: ignore
    ConflictError = Exception  # type: ignore
    InternalServerError = Exception  # type: ignore
    NotFoundError = Exception  # type: ignore
    PermissionDeniedError = Exception  # type: ignore
    UnprocessableEntityError = Exception  # type: ignore


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------


class ScorerNotConfiguredError(Exception):
    """Raised when the AI Scorer is used but not properly configured."""

    pass


class ScorerUnavailableError(Exception):
    """Raised when the AI Scorer encounters a transient failure."""

    pass


# ---------------------------------------------------------------------------
# Main Service Class
# ---------------------------------------------------------------------------


class ExternalAIScorer:
    """
    Service class for scoring task relevance against user-defined strategic domains.

    This class interfaces with the OpenAI Chat Completions API to analyze how well
    a task aligns with the user's life domains (work, study, health, relationships).

    The class uses DEFERRED INITIALIZATION - it will not raise errors during
    __init__ if the API key is missing. Instead, it tracks its availability
    state and returns fallback responses when scoring is attempted without
    proper configuration.

    Attributes:
        api_key (str | None): OpenAI API key for authentication.
        client (OpenAI | None): Initialized OpenAI client instance, or None if unavailable.
        model (str): The OpenAI model to use.
        is_configured (bool): Whether the scorer is properly configured and ready.
        configuration_error (str | None): Description of configuration issue, if any.

    Example:
        >>> scorer = ExternalAIScorer()
        >>> if scorer.is_configured:
        ...     result = scorer.score_task(...)
        ... else:
        ...     logger.warning(f"Scorer not available: {scorer.configuration_error}")
    """

    # Default model supporting JSON response format
    DEFAULT_MODEL: str = "gpt-3.5-turbo-0125"

    # API call configuration
    DEFAULT_TEMPERATURE: float = 0.2  # Low temperature for deterministic behavior
    DEFAULT_MAX_TOKENS: int = 200
    DEFAULT_TIMEOUT: float = 10.0  # Seconds

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        **client_kwargs: Any,
    ) -> None:
        """
        Initialize the ExternalAIScorer with graceful configuration handling.

        This initializer NEVER raises exceptions. Instead, it sets the
        `is_configured` flag to indicate whether the scorer is ready for use.

        Args:
            api_key: OpenAI API key. Falls back to settings.OPENAI_API_KEY.
            model: OpenAI model identifier. Defaults to gpt-3.5-turbo-0125.
            timeout: API call timeout in seconds. Defaults to 10.0.
            **client_kwargs: Additional keyword arguments passed to the OpenAI client.
        """
        self.model: str = model or self.DEFAULT_MODEL
        self.timeout: float = timeout or self.DEFAULT_TIMEOUT
        self._client_kwargs: Dict[str, Any] = client_kwargs

        # Deferred initialization state
        self.api_key: Optional[str] = None
        self.client: Optional[OpenAI] = None  # type: ignore
        self.is_configured: bool = False
        self.configuration_error: Optional[str] = None

        # Attempt graceful configuration
        self._configure(api_key)

    def _configure(self, api_key: Optional[str] = None) -> None:
        """
        Attempt to configure the OpenAI client gracefully.

        Sets `is_configured` to True only if all requirements are met.
        Otherwise, logs the issue and sets `configuration_error`.

        Args:
            api_key: Explicit API key to use, or None to read from settings.
        """
        # Check 1: Is the openai library installed?
        if not OPENAI_AVAILABLE:
            self.configuration_error = (
                "OpenAI library is not installed. Install with: pip install openai"
            )
            logger.critical(f"ExternalAIScorer: {self.configuration_error}")
            return

        # Check 2: Is an API key available?
        resolved_key = api_key or getattr(settings, "OPENAI_API_KEY", None) or ""
        if not resolved_key:
            self.configuration_error = (
                "OPENAI_API_KEY is not configured. "
                "Set the OPENAI_API_KEY environment variable or Django setting."
            )
            logger.warning(f"ExternalAIScorer: {self.configuration_error}")
            return

        # Check 3: Can we initialize the client?
        try:
            self.api_key = resolved_key
            self.client = OpenAI(api_key=self.api_key, **self._client_kwargs)
            self.is_configured = True
            self.configuration_error = None
            logger.info(
                f"ExternalAIScorer initialized successfully with model={self.model}"
            )
        except Exception as e:
            self.configuration_error = f"Failed to initialize OpenAI client: {str(e)}"
            logger.error(f"ExternalAIScorer: {self.configuration_error}")
            self.client = None
            self.is_configured = False

    def score_task(
        self,
        task_title: str,
        task_description: str,
        user_weights: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Score task relevance against user-defined strategic domains.

        This method sends the task content to OpenAI and receives relevance scores
        for each domain. The weights dictionary keys define the domains; the weight
        VALUES are NOT sent to the AI (to prevent bias).

        If the scorer is not configured, returns a fallback response with
        confidence=0.0 to indicate the scoring was not performed by AI.

        Args:
            task_title: The title/name of the task.
            task_description: Detailed description of the task.
            user_weights: Dictionary where keys are domain names (e.g., "work_bills")
                          and values are the user's strategic weights (ignored by AI).

        Returns:
            A dictionary with the following structure:
            {
                "relevance_scores": {
                    "domain1": float,  # 0.0 to 1.0
                    "domain2": float,
                    ...
                },
                "confidence": float,  # 0.0 to 1.0 (0.0 = fallback/error)
                "error_code": str | None,  # Present only on errors
                "error_message": str | None  # Present only on errors
            }
        """
        # Extract domain keys only (weights are intentionally not sent to AI)
        domains: List[str] = list(user_weights.keys())

        # Guard: Check if scorer is configured
        if not self.is_configured or self.client is None:
            logger.warning(
                f"ExternalAIScorer.score_task called but scorer not configured. "
                f"Reason: {self.configuration_error}"
            )
            return self._get_error_response(
                domains,
                error_code="SCORER_NOT_CONFIGURED",
                error_message=self.configuration_error or "Scorer not available",
            )

        # Build the prompt messages
        messages: List[Dict[str, str]] = self._build_messages(
            task_title, task_description, domains
        )

        logger.debug(
            f"ExternalAIScorer: Scoring task '{task_title}' against domains: {domains}"
        )

        try:
            # Make the API call with comprehensive error handling
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.DEFAULT_TEMPERATURE,
                max_tokens=self.DEFAULT_MAX_TOKENS,
                response_format={"type": "json_object"},
                timeout=self.timeout,
            )

            raw_content: str = response.choices[0].message.content or ""

            logger.debug(f"ExternalAIScorer: Raw response: {raw_content[:200]}...")

            # Parse and validate the response
            result = self._validate_and_parse_response(raw_content, domains)

            logger.info(
                f"ExternalAIScorer: Successfully scored '{task_title}' "
                f"(confidence={result.get('confidence', 0.0):.2f})"
            )

            return result

        # Handle specific OpenAI errors with appropriate error codes
        except AuthenticationError as e:
            logger.error(f"OpenAI authentication failed: {e}")
            return self._get_error_response(
                domains,
                error_code="AUTH_ERROR",
                error_message="Invalid API key or authentication failed",
            )

        except RateLimitError as e:
            logger.warning(f"OpenAI rate limit exceeded: {e}")
            return self._get_error_response(
                domains,
                error_code="RATE_LIMIT",
                error_message="API rate limit exceeded, please retry later",
            )

        except APITimeoutError as e:
            logger.warning(f"OpenAI API timeout: {e}")
            return self._get_error_response(
                domains,
                error_code="TIMEOUT",
                error_message="API request timed out",
            )

        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            return self._get_error_response(
                domains,
                error_code="CONNECTION_ERROR",
                error_message="Could not connect to OpenAI API",
            )

        except BadRequestError as e:
            logger.error(f"OpenAI bad request: {e}")
            return self._get_error_response(
                domains,
                error_code="BAD_REQUEST",
                error_message="Invalid request to OpenAI API",
            )

        except APIStatusError as e:
            logger.error(f"OpenAI API status error: {e.status_code} - {e}")
            return self._get_error_response(
                domains,
                error_code=f"API_ERROR_{e.status_code}",
                error_message=f"OpenAI API error (status {e.status_code})",
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode AI response as JSON: {e}")
            return self._get_error_response(
                domains,
                error_code="JSON_PARSE_ERROR",
                error_message="AI returned invalid JSON response",
            )

        except ValueError as e:
            logger.error(f"Response validation failed: {e}")
            return self._get_error_response(
                domains,
                error_code="VALIDATION_ERROR",
                error_message=str(e),
            )

        except Exception as e:
            logger.exception(f"Unexpected error in ExternalAIScorer: {e}")
            return self._get_error_response(
                domains,
                error_code="UNEXPECTED_ERROR",
                error_message=f"Unexpected error: {type(e).__name__}",
            )

    def _build_messages(
        self, title: str, description: str, domains: List[str]
    ) -> List[Dict[str, str]]:
        """
        Construct the system and user messages for the LLM prompt.

        The prompt is engineered to:
        1. Ignore urgency/deadline language (that's computed deterministically)
        2. Focus purely on semantic relevance to life domains
        3. Return strictly formatted JSON

        Args:
            title: Task title.
            description: Task description.
            domains: List of domain names to score against.

        Returns:
            List of message dictionaries for the Chat Completions API.
        """
        # Define the expected JSON schema in the prompt
        json_structure_example = json.dumps(
            {"relevance_scores": {domain: 0.5 for domain in domains}, "confidence": 0.9}
        )

        system_prompt = (
            "You are a strict strategic categorization engine. "
            "Your ONLY job is to score how well a task aligns with specific life domains.\n\n"
            "RULES:\n"
            "1. Ignore urgency, deadlines, or emotional language.\n"
            "2. Score alignment purely on semantic relevance (0.0 = Irrelevant, 1.0 = Highly Relevant).\n"
            "3. Normalize all scores to be between 0.0 and 1.0.\n"
            "4. Return ONLY valid JSON. No markdown, no commentary.\n"
            f"5. The output must strictly follow this schema: {json_structure_example}"
        )

        user_content = (
            f"Task Title: {title}\n"
            f"Task Description: {description}\n\n"
            f"Score alignment for these domains: {', '.join(domains)}"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def _validate_and_parse_response(
        self, raw_json: str, domains: List[str]
    ) -> Dict[str, Any]:
        """
        Parse and validate the JSON response from OpenAI.

        Applies defensive validation:
        - Ensures required keys exist
        - Clamps all scores to [0.0, 1.0]
        - Provides default values for missing domains

        Args:
            raw_json: Raw JSON string from the API response.
            domains: Expected domain keys.

        Returns:
            Validated dictionary with relevance_scores and confidence.

        Raises:
            ValueError: If the response is empty or missing required keys.
        """
        if not raw_json:
            raise ValueError("Empty response from AI")

        data = json.loads(raw_json)

        # Ensure top-level keys exist
        if "relevance_scores" not in data or "confidence" not in data:
            raise ValueError("Missing required top-level keys in JSON response")

        scores: Dict[str, Any] = data["relevance_scores"]
        cleaned_scores: Dict[str, float] = {}

        # Validate and clamp each domain score
        for domain in domains:
            raw_score = scores.get(domain, 0.0)
            try:
                clean_val = float(raw_score)
                # Clamp to [0.0, 1.0] range
                clean_val = max(0.0, min(1.0, clean_val))
            except (ValueError, TypeError):
                clean_val = 0.0

            cleaned_scores[domain] = clean_val

        # Validate and clamp confidence
        try:
            confidence = float(data.get("confidence", 0.0))
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.0

        return {
            "relevance_scores": cleaned_scores,
            "confidence": confidence,
        }

    def _get_error_response(
        self,
        domains: List[str],
        error_code: str,
        error_message: str,
    ) -> Dict[str, Any]:
        """
        Generate a structured error response.

        This ensures the downstream pipeline always receives a valid
        contract structure, even when the AI service fails.

        Args:
            domains: List of domain names.
            error_code: Machine-readable error code.
            error_message: Human-readable error description.

        Returns:
            Dictionary with fallback scores and error information.
        """
        return {
            "relevance_scores": {domain: 0.0 for domain in domains},
            "confidence": 0.0,
            "error_code": error_code,
            "error_message": error_message,
        }

    def _get_fallback_response(self, domains: List[str]) -> Dict[str, Any]:
        """
        Generate a safe fallback response structure (legacy method).

        Maintained for backward compatibility.

        Args:
            domains: List of domain names.

        Returns:
            Dictionary with all relevance scores set to 0.0 and confidence 0.0.
        """
        return {
            "relevance_scores": {domain: 0.0 for domain in domains},
            "confidence": 0.0,
        }

    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the AI Scorer.

        Returns:
            Dictionary with health status information.
        """
        return {
            "is_configured": self.is_configured,
            "model": self.model,
            "timeout": self.timeout,
            "openai_library_available": OPENAI_AVAILABLE,
            "configuration_error": self.configuration_error,
        }
