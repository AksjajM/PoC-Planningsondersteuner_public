"""Tests for Django user model configuration."""

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase


class UserModelConfigurationTests(SimpleTestCase):
    def test_default_django_user_model_is_configured(self):
        """PLON-17: controleert dat de PoC het standaard Django User-model gebruikt."""
        user_model = get_user_model()

        self.assertEqual(user_model._meta.app_label, "auth")
        self.assertEqual(user_model._meta.model_name, "user")