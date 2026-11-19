"""Tests for Django Admin configuration of the planning app."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from planning.models import Role, UserRole


class PlanningAdminTests(TestCase):
    def setUp(self):
        """PLON-20: maakt een admingebruiker aan voor admin-tests."""
        self.admin_user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.admin_user)

    def test_default_user_admin_is_accessible(self):
        """PLON-20: controleert dat gebruikers via Django Admin beheerbaar zijn."""
        response = self.client.get(reverse("admin:auth_user_changelist"))

        self.assertEqual(response.status_code, 200)

    def test_role_admin_changelist_is_accessible(self):
        """PLON-20: controleert dat planbare rollen zichtbaar zijn in Django Admin."""
        Role.objects.create(name="Front Office")

        response = self.client.get(reverse("admin:planning_role_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Front Office")

    def test_user_role_admin_changelist_is_accessible(self):
        """PLON-20: controleert dat rolkoppelingen zichtbaar zijn in Django Admin."""
        user = get_user_model().objects.create_user(
            username="employee1",
            password="test-password",
        )
        role = Role.objects.create(name="Front Office")
        UserRole.objects.create(user=user, role=role)

        response = self.client.get(reverse("admin:planning_userrole_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "employee1")
        self.assertContains(response, "Front Office")