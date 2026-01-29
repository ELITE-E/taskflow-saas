# tasks/tests/__init__.py
"""
Task App Test Suite
===================

This package contains unit and integration tests for the tasks application.

Modules:
--------
- test_engine: Unit tests for the AI Engine mathematical logic (urgency, importance)
- test_orchestration: Integration tests for the AI scoring pipeline

Running Tests:
--------------
    # Run all task tests
    python manage.py test tasks

    # Run specific test module
    python manage.py test tasks.tests.test_engine
    python manage.py test tasks.tests.test_orchestration

    # Run with verbose output
    python manage.py test tasks -v 2
"""
