"""Tests for the Role model."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from planning.models import Role


class RoleModelTests(TestCase):
    def test_role_can_be_created_with_required_name(self):
        """PLON-18: controleert dat een planbare rol kan worden aangemaakt."""
        role = Role.objects.create(name="Front Office")

        self.assertEqual(role.name, "Front Office")
        self.assertEqual(str(role), "Front Office")
        self.assertTrue(role.is_active)

    def test_role_name_must_be_unique(self):
        """PLON-18: controleert dat dubbele rolnamen worden tegengehouden."""
        Role.objects.create(name="Front Office")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Role.objects.create(name="Front Office")

    def test_role_name_cannot_be_blank(self):
        """PLON-18: controleert dat een rolnaam verplicht is."""
        role = Role(name="")

        with self.assertRaises(ValidationError):
            role.full_clean()