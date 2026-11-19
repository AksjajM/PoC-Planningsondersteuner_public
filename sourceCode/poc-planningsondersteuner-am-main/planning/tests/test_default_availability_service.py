"""Tests for default availability persistence services."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from planning.models import DefaultAvailability, Role
from planning.services import save_default_availability

User = get_user_model()


class DefaultAvailabilityServiceTest(TestCase):
    """Verifies default availability is saved independently of the form."""

    def setUp(self):
        self.user = User.objects.create_user(username="employee1", password="x")
        self.role_fo = Role.objects.get(name="FO")
        self.role_bo = Role.objects.get(name="BO")

    def test_saves_all_weekday_parts_and_updates_existing_value(self):
        cleaned_data = {
            f"{day}_{part}": self.role_fo
            for day in range(1, 6)
            for part in ("MORNING", "AFTERNOON")
        }
        cleaned_data["1_AFTERNOON"] = self.role_bo

        save_default_availability(self.user, cleaned_data)
        save_default_availability(self.user, cleaned_data)

        self.assertEqual(DefaultAvailability.objects.filter(user=self.user).count(), 10)
        monday_afternoon = DefaultAvailability.objects.get(
            user=self.user,
            day_of_week=1,
            part_of_day="AFTERNOON",
        )
        self.assertEqual(monday_afternoon.role, self.role_bo)
