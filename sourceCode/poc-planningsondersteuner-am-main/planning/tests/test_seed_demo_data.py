"""Tests for the demo seed data command."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from planning.management.commands.seed_demo_data import (
    DEMO_ASSIGNMENTS,
    DEMO_USERS,
    DEMO_VACATION_REQUESTS,
)
from planning.models import Role, UserRole, VacationRequest


class SeedDemoDataCommandTests(TestCase):
    def test_seed_demo_data_creates_users_assignments_and_vacations(self):
        """PLON-42: controleert dat het vaste overlapscenario wordt aangemaakt."""
        output = StringIO()

        call_command("seed_demo_data", force=True, stdout=output)

        user_model = get_user_model()

        for user_data in DEMO_USERS:
            self.assertTrue(
                user_model.objects.filter(username=user_data["username"]).exists(),
                msg=f"Expected user '{user_data['username']}' to exist.",
            )

        for username, role_name in DEMO_ASSIGNMENTS:
            self.assertTrue(
                UserRole.objects.filter(
                    user__username=username,
                    role__name=role_name,
                ).exists(),
                msg=f"Expected assignment '{username} -> {role_name}' to exist.",
            )

        for request_data in DEMO_VACATION_REQUESTS:
            self.assertTrue(
                VacationRequest.objects.filter(
                    user__username=request_data["username"],
                    start_date=request_data["start_date"],
                    end_date=request_data["end_date"],
                    planning_status=request_data["planning_status"],
                ).exists(),
                msg=(
                    "Expected vacation request for "
                    f"'{request_data['username']}' to exist."
                ),
            )

        self.assertIn("Demo data created", output.getvalue())

    def test_seed_demo_data_reuses_existing_roles_without_duplicating(self):
        """PLON-103: controleert dat bestaande rollen hergebruikt worden i.p.v. gedupliceerd."""
        role_names_before = set(Role.objects.values_list("name", flat=True))

        call_command("seed_demo_data", force=True)

        role_names_after = set(Role.objects.values_list("name", flat=True))

        self.assertEqual(role_names_before, role_names_after)

    def test_seed_demo_data_is_idempotent(self):
        """PLON-23: controleert dat het command herhaalbaar is zonder dubbele data."""
        call_command("seed_demo_data", force=True)
        call_command("seed_demo_data", force=True)

        user_model = get_user_model()

        for user_data in DEMO_USERS:
            self.assertEqual(
                user_model.objects.filter(username=user_data["username"]).count(),
                1,
            )

        for username, role_name in DEMO_ASSIGNMENTS:
            self.assertEqual(
                UserRole.objects.filter(
                    user__username=username,
                    role__name=role_name,
                ).count(),
                1,
            )

        for request_data in DEMO_VACATION_REQUESTS:
            self.assertEqual(
                VacationRequest.objects.filter(
                    user__username=request_data["username"],
                    start_date=request_data["start_date"],
                    end_date=request_data["end_date"],
                ).count(),
                1,
            )

    def test_seed_demo_data_can_create_demo_admin_when_requested(self):
        """PLON-23: controleert dat een demo-admin alleen expliciet wordt aangemaakt."""
        user_model = get_user_model()

        call_command("seed_demo_data", force=True)

        self.assertFalse(user_model.objects.filter(username="admin").exists())

        call_command("seed_demo_data", force=True, with_admin=True)

        admin_user = user_model.objects.get(username="admin")

        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
