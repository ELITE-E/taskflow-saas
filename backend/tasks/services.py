# tasks/services.py

import json
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from openai import OpenAI, APIError, APIConnectionError, RateLimitError

# Configure logging
logger = logging.getLogger(__name__)

class ExternalAIScorer:
    """
    Service layer for AI-assisted task scoring.
    
    Responsibility:
    - Interface with OpenAI Chat Completions API.
    - specialized prompt engineering for alignment scoring.
    - JSON validation and strictly typed output.
    - Error handling and retries.

    Constraints:
    - Pure service: No Django ORM or business logic dependencies.
    - Deterministic JSON output.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo-0125"):
        """
        Initialize the OpenAI client.
        
        Args:
            api_key: Optional API key. Defaults to settings.OPENAI_API_KEY.
            model: The OpenAI model to use (default: gpt-3.5-turbo-0125 for JSON mode support).
        """
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None)
        self.model = model
        
        if not self.api_key:
            logger.warning("ExternalAIScorer initialized without an API key.")
        
        self.client = OpenAI(api_key=self.api_key, max_retries=3)

    def score_task(
        self, 
        task_title: str, 
        task_description: str, 
        user_weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Scoring task relevance against user-defined strategic goals.
        
        Args:
            task_title: The title of the task.
            task_description: The description of the task.
            user_weights: A dictionary of strategic goals (keys are categories). 
                          Note: The VALUES (weights) are ignored by the AI. 
                          Only keys are used to define the domains.

        Returns:
            Dict containing 'relevance_scores' (dict of floats 0-1) and 'confidence' (float).
            Returns default zero-scores structure on failure.
        """
        
        # 1. Extract domains from input (ignoring the weight values)
        domains = list(user_weights.keys())
        
        # 2. Build the strict prompt
        messages = self._build_messages(task_title, task_description, domains)

        try:
            # 3. Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2, # Low temperature for deterministic behavior
                max_tokens=200,
                response_format={"type": "json_object"}, # Enforce JSON mode
                timeout=10.0 # Strict timeout
            )
            
            raw_content = response.choices[0].message.content
            
            # 4. Parse and Validate
            parsed_data = self._validate_and_parse_response(raw_content, domains)
            return parsed_data

        except (APIError, APIConnectionError, RateLimitError) as e:
            logger.error(f"OpenAI API failed: {str(e)}")
            return self._get_fallback_response(domains)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode AI response: {str(e)}")
            return self._get_fallback_response(domains)
        except Exception as e:
            logger.exception(f"Unexpected error in ExternalAIScorer: {str(e)}")
            return self._get_fallback_response(domains)

    def _build_messages(self, title: str, description: str, domains: list) -> list:
        """Constructs the system and user messages for the LLM."""
        
        # Explicitly define the JSON structure in the prompt
        json_structure_example = json.dumps({
            "relevance_scores": {domain: 0.5 for domain in domains},
            "confidence": 0.9
        })

        system_prompt = (
            "You are a strict strategic categorization engine. "
            "Your ONLY job is to score how well a task aligns with specific life domains. "
            "\n\n"
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
            {"role": "user", "content": user_content}
        ]

    def _validate_and_parse_response(self, raw_json: str, domains: list) -> Dict[str, Any]:
        """Parses JSON and ensures it meets the output contract."""
        if not raw_json:
            raise ValueError("Empty response from AI")

        data = json.loads(raw_json)
        
        # Ensure top-level keys
        if "relevance_scores" not in data or "confidence" not in data:
            raise ValueError("Missing required top-level keys in JSON response")

        # Validate scores
        scores = data["relevance_scores"]
        cleaned_scores = {}
        
        for domain in domains:
            score = scores.get(domain, 0.0)
            # Enforce float type and bounds
            try:
                clean_val = float(score)
                clean_val = max(0.0, min(1.0, clean_val)) # Clamp between 0 and 1
            except (ValueError, TypeError):
                clean_val = 0.0
            
            cleaned_scores[domain] = clean_val

        # Validate confidence
        try:
            confidence = float(data.get("confidence", 0.0))
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.0

        return {
            "relevance_scores": cleaned_scores,
            "confidence": confidence
        }

    def _get_fallback_response(self, domains: list) -> Dict[str, Any]:
        """Returns a safe default structure in case of failure."""
        return {
            "relevance_scores": {domain: 0.0 for domain in domains},
            "confidence": 0.0
        }