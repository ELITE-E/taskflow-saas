# goals/tests.py
"""
Goals App Test Suite
====================

Tests for Goals and Strategic Weights API endpoints.

Test Categories:
----------------
1. GoalWeights Model Tests - Validation logic
2. GoalWeights Serializer Tests - Data transformation
3. Weights API Tests - HTTP endpoints
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Goal, GoalWeights
from .serializers import GoalWeightsSerializer

User = get_user_model()


# ===========================================================================
# MODEL TESTS
# ===========================================================================

class GoalWeightsModelTest(TestCase):
    """Tests for the GoalWeights model validation logic."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_valid_weights_save_successfully(self):
        """Weights that sum to 1.0 should save without error."""
        weights = GoalWeights(
            user=self.user,
            work_bills=0.4,
            study=0.3,
            health=0.2,
            relationships=0.1
        )
        
        # Should not raise
        weights.full_clean()
        weights.save()
        
        self.assertEqual(GoalWeights.objects.count(), 1)
        saved = GoalWeights.objects.first()
        self.assertAlmostEqual(saved.work_bills, 0.4, places=4)

    def test_equal_weights_are_valid(self):
        """Default equal weights (0.25 each) should be valid."""
        weights = GoalWeights(
            user=self.user,
            work_bills=0.25,
            study=0.25,
            health=0.25,
            relationships=0.25
        )
        
        weights.full_clean()
        weights.save()
        
        total = weights.work_bills + weights.study + weights.health + weights.relationships
        self.assertAlmostEqual(total, 1.0, places=3)

    def test_weights_below_one_raises_validation_error(self):
        """Weights summing to less than 1.0 should raise ValidationError."""
        weights = GoalWeights(
            user=self.user,
            work_bills=0.2,
            study=0.2,
            health=0.2,
            relationships=0.2  # Sum = 0.8
        )
        
        with self.assertRaises(ValidationError) as ctx:
            weights.full_clean()
        
        self.assertIn('1.0', str(ctx.exception))

    def test_weights_above_one_raises_validation_error(self):
        """Weights summing to more than 1.0 should raise ValidationError."""
        weights = GoalWeights(
            user=self.user,
            work_bills=0.5,
            study=0.5,
            health=0.2,
            relationships=0.1  # Sum = 1.3
        )
        
        with self.assertRaises(ValidationError) as ctx:
            weights.full_clean()
        
        self.assertIn('1.0', str(ctx.exception))

    def test_edge_case_0_999_total(self):
        """Weights summing to 0.999 should be accepted (within epsilon)."""
        weights = GoalWeights(
            user=self.user,
            work_bills=0.333,
            study=0.333,
            health=0.333,
            relationships=0.0  # Sum = 0.999
        )
        
        # Should be accepted due to epsilon tolerance
        weights.full_clean()

    def test_edge_case_1_001_total(self):
        """Weights summing to 1.001 should be accepted (within epsilon)."""
        weights = GoalWeights(
            user=self.user,
            work_bills=0.334,
            study=0.333,
            health=0.334,
            relationships=0.0  # Sum = 1.001
        )
        
        # Should be accepted due to epsilon tolerance
        weights.full_clean()

    def test_negative_weight_raises_error(self):
        """Negative weights should raise ValidationError."""
        weights = GoalWeights(
            user=self.user,
            work_bills=-0.1,  # Negative!
            study=0.5,
            health=0.3,
            relationships=0.3
        )
        
        with self.assertRaises(ValidationError):
            weights.full_clean()

    def test_weight_above_one_raises_error(self):
        """Individual weight > 1.0 should raise ValidationError."""
        weights = GoalWeights(
            user=self.user,
            work_bills=1.5,  # > 1.0
            study=0.0,
            health=0.0,
            relationships=0.0
        )
        
        with self.assertRaises(ValidationError):
            weights.full_clean()


# ===========================================================================
# SERIALIZER TESTS
# ===========================================================================

class GoalWeightsSerializerTest(TestCase):
    """Tests for the GoalWeightsSerializer."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='serializeruser',
            email='serializer@example.com',
            password='testpass123'
        )
        self.weights = GoalWeights.objects.create(
            user=self.user,
            work_bills=0.25,
            study=0.25,
            health=0.25,
            relationships=0.25
        )

    def test_serializer_output_format(self):
        """Serializer should output all expected fields."""
        serializer = GoalWeightsSerializer(self.weights)
        data = serializer.data
        
        self.assertIn('id', data)
        self.assertIn('work_bills', data)
        self.assertIn('study', data)
        self.assertIn('health', data)
        self.assertIn('relationships', data)
        self.assertIn('total_sum', data)
        self.assertIn('is_valid_sum', data)
        
        self.assertEqual(data['total_sum'], 1.0)
        self.assertTrue(data['is_valid_sum'])

    def test_serializer_validates_sum(self):
        """Serializer should reject invalid weight sums."""
        serializer = GoalWeightsSerializer(
            self.weights,
            data={'work_bills': 0.5, 'study': 0.5},  # Sum would be 1.25
            partial=True
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_serializer_accepts_valid_partial_update(self):
        """Serializer should accept partial updates that maintain sum."""
        serializer = GoalWeightsSerializer(
            self.weights,
            data={
                'work_bills': 0.4,
                'study': 0.3,
                'health': 0.2,
                'relationships': 0.1
            },
            partial=True
        )
        
        self.assertTrue(serializer.is_valid())


# ===========================================================================
# API ENDPOINT TESTS
# ===========================================================================

class WeightsAPITest(APITestCase):
    """Tests for the Weights API endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='apiuser',
            email='api@example.com',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.weights_url = '/api/v1/goals/weights/'

    def test_get_weights_creates_defaults_if_none_exist(self):
        """GET should create default weights if user has none."""
        response = self.client.get(self.weights_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['work_bills'], 0.25)
        self.assertEqual(response.data['study'], 0.25)
        self.assertEqual(response.data['health'], 0.25)
        self.assertEqual(response.data['relationships'], 0.25)
        self.assertEqual(response.data['total_sum'], 1.0)
        self.assertTrue(response.data['is_valid_sum'])

    def test_get_weights_returns_existing(self):
        """GET should return existing weights."""
        GoalWeights.objects.create(
            user=self.user,
            work_bills=0.5,
            study=0.3,
            health=0.15,
            relationships=0.05
        )
        
        response = self.client.get(self.weights_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['work_bills'], 0.5)
        self.assertEqual(response.data['study'], 0.3)

    def test_patch_weights_valid_update(self):
        """PATCH should update weights when sum is valid."""
        # Create initial weights
        self.client.get(self.weights_url)
        
        response = self.client.patch(
            self.weights_url,
            {
                'work_bills': 0.4,
                'study': 0.3,
                'health': 0.2,
                'relationships': 0.1
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['work_bills'], 0.4)
        self.assertEqual(response.data['total_sum'], 1.0)

    def test_patch_weights_invalid_sum_below_one(self):
        """PATCH should return 400 when weights sum to < 1.0."""
        # Create initial weights
        self.client.get(self.weights_url)
        
        response = self.client.patch(
            self.weights_url,
            {
                'work_bills': 0.2,
                'study': 0.2,
                'health': 0.2,
                'relationships': 0.2  # Sum = 0.8
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        # Check that error message mentions 0.8
        error_message = str(response.data['non_field_errors'][0])
        self.assertIn('0.8', error_message)

    def test_patch_weights_invalid_sum_above_one(self):
        """PATCH should return 400 when weights sum to > 1.0."""
        # Create initial weights
        self.client.get(self.weights_url)
        
        response = self.client.patch(
            self.weights_url,
            {
                'work_bills': 0.5,
                'study': 0.3,
                'health': 0.3,
                'relationships': 0.1  # Sum = 1.2
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        error_message = str(response.data['non_field_errors'][0])
        self.assertIn('1.2', error_message)

    def test_patch_weights_partial_update(self):
        """PATCH should work with partial data if sum remains valid."""
        GoalWeights.objects.create(
            user=self.user,
            work_bills=0.25,
            study=0.25,
            health=0.25,
            relationships=0.25
        )
        
        # Update only work_bills and relationships to maintain sum
        response = self.client.patch(
            self.weights_url,
            {
                'work_bills': 0.35,
                'relationships': 0.15  # 0.35 + 0.25 + 0.25 + 0.15 = 1.0
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['work_bills'], 0.35)
        self.assertEqual(response.data['relationships'], 0.15)
        self.assertEqual(response.data['total_sum'], 1.0)

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests should be rejected."""
        self.client.force_authenticate(user=None)
        
        response = self.client.get(self.weights_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_weights_precision_handling(self):
        """API should handle floating-point precision correctly."""
        # Create initial weights
        self.client.get(self.weights_url)
        
        # Use values that could cause floating-point issues
        response = self.client.patch(
            self.weights_url,
            {
                'work_bills': 0.333,
                'study': 0.333,
                'health': 0.334,
                'relationships': 0.0  # Sum = 1.0
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Ensure no floating-point display issues like 0.333000000001
        self.assertEqual(response.data['work_bills'], 0.333)

    def test_put_works_same_as_patch(self):
        """PUT should behave the same as PATCH."""
        # Create initial weights
        self.client.get(self.weights_url)
        
        response = self.client.put(
            self.weights_url,
            {
                'work_bills': 0.5,
                'study': 0.2,
                'health': 0.2,
                'relationships': 0.1
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['work_bills'], 0.5)


# ===========================================================================
# GOAL CRUD TESTS
# ===========================================================================

class GoalAPITest(APITestCase):
    """Tests for the Goal CRUD endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='goaluser',
            email='goal@example.com',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.goals_url = '/api/v1/goals/'

    def test_create_goal(self):
        """POST should create a new goal."""
        response = self.client.post(
            self.goals_url,
            {
                'title': 'Learn Python',
                'description': 'Master Python programming',
                'weight': 8
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Learn Python')
        self.assertEqual(Goal.objects.count(), 1)

    def test_list_goals(self):
        """GET should list user's goals."""
        Goal.objects.create(
            user=self.user,
            title='Goal 1',
            weight=5
        )
        Goal.objects.create(
            user=self.user,
            title='Goal 2',
            weight=7
        )
        
        response = self.client.get(self.goals_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_user_isolation(self):
        """Users should only see their own goals."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        Goal.objects.create(user=other_user, title='Other Goal', weight=5)
        Goal.objects.create(user=self.user, title='My Goal', weight=5)
        
        response = self.client.get(self.goals_url)
        
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'My Goal')
