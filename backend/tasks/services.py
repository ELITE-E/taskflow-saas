# tasks/services.py

import time
import random

def external_ai_scoring(title: str, description: str) -> dict:
    """
    Simulates calling an external AI service API for relevance scores.
    This would typically involve an HTTP POST request to the external service.
    """
    print(f"--- Calling External AI for: {title} ---")
    time.sleep(random.uniform(1, 3)) # Simulate API latency (1 to 3 seconds)
    
    # Return a dummy score for "Relevance" (0.1 to 1.0)
    # In a real app, this would be complex JSON with scores for different categories.
    return {
        'Relevance': random.uniform(0.1, 1.0) 
    }