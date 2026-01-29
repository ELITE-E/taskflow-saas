# tasks/tests.py
"""
Legacy test module redirect.

Tests have been reorganized into the tasks/tests/ package.
See:
    - tasks/tests/test_engine.py - AI Engine unit tests (urgency, importance, quadrant)

To run all task tests:
    python manage.py test tasks

To run specific test module:
    python manage.py test tasks.tests.test_engine
"""

# Re-export tests for backward compatibility with Django's test discovery
from tasks.tests.test_engine import *  # noqa: F401, F403
