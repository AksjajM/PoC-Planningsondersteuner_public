"""Tests voor het PLON-54-medewerkersuitzonderingenscherm."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from planning.models import AvailabilityException, Role
from planning.services import AVAILABILITY_EXCEPTION_PREFIX, get_week_dates

User = get_user_model()


class AvailabilityExceptionAccessTest(TestCase):
    def setUp(self):
        self.url = reverse("planning:absence")
        self.employee = User.objects.create_user(username="employee1", password="x")
        self.planner = User.objects.create_user(
            username="planner1", password="x", is_staff=True
        )
        self.admin = User.objects.create_superuser(
            username="admin", password="x", email="admin@example.com"
        )

    def test_login_is_required(self):
        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_employee_can_open_screen(self):
        self.client.login(username="employee1", password="x")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "planning/availability_exception.html")

    def test_planner_cannot_open_screen_or_see_link(self):
        self.client.login(username="planner1", password="x")

        screen = self.client.get(self.url)
        home = self.client.get(reverse("planning:home"))

        self.assertEqual(screen.status_code, 403)
        self.assertNotContains(home, "Request leave")

    def test_admin_can_open_screen_and_see_link(self):
        self.client.login(username="admin", password="x")

        screen = self.client.get(self.url)
        home = self.client.get(reverse("planning:home"))

        self.assertEqual(screen.status_code, 200)
        self.assertContains(home, "Request leave")


class AvailabilityExceptionContentTest(TestCase):
    def setUp(self):
        self.url = reverse("planning:absence")
        self.employee = User.objects.create_user(username="employee1", password="x")
        self.role_fo = Role.objects.get(name="FO")
        self.role_bo = Role.objects.get(name="BO")
        self.client.login(username="employee1", password="x")

    def _complete_post_data(self, year=2026, week=12, **overrides):
        data = {"year": year, "week_number": week, "note": "Training"}
        for day in range(1, 6):
            for part in AvailabilityException.PartOfDay.values:
                data[f"exception_{day}_{part}"] = ""
        data.update(overrides)
        return data

    def test_screen_has_week_controls_day_parts_roles_and_disabled_save(self):
        response = self.client.get(self.url, {"year": 2026, "week": 12})

        self.assertContains(response, "Current week")
        self.assertContains(response, "Morning", count=5)
        self.assertContains(response, "Afternoon", count=5)
        self.assertContains(response, 'class="exception-select"', count=10)
        self.assertContains(response, ">N/A</option>", count=10)
        self.assertContains(response, self.role_fo.name)
        self.assertContains(response, "Availability exception ingevoerd door medewerker:")
        self.assertContains(response, 'id="save-button"')
        self.assertContains(response, "disabled")

    def test_selected_week_loads_only_values_for_that_week(self):
        week_12_monday = get_week_dates(2026, 12)[0]
        AvailabilityException.objects.create(
            user=self.employee,
            date=week_12_monday,
            part_of_day="MORNING",
            role=self.role_fo,
            is_available=True,
            reason=AvailabilityException.Reason.AVAILABILITY_EXCEPTION,
            note=f"{AVAILABILITY_EXCEPTION_PREFIX}Training",
        )

        week_12 = self.client.get(self.url, {"year": 2026, "week": 12})
        week_13 = self.client.get(self.url, {"year": 2026, "week": 13})

        self.assertEqual(week_12.context["cells"][0]["role_id"], self.role_fo.id)
        self.assertIsNone(week_13.context["cells"][0]["role_id"])

    def test_screen_shows_current_weekly_planning_and_exception_indicator(self):
        from planning.models import WeeklyPlanning

        monday = get_week_dates(2026, 12)[0]
        WeeklyPlanning.objects.create(
            user=self.employee,
            year=2026,
            week_number=12,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_fo,
        )
        AvailabilityException.objects.create(
            user=self.employee,
            date=monday,
            part_of_day="AFTERNOON",
            role=None,
            is_available=False,
            reason=AvailabilityException.Reason.SICK,
        )

        response = self.client.get(self.url, {"year": 2026, "week": 12})

        self.assertEqual(response.context["cells"][0]["role_id"], self.role_fo.id)
        self.assertIsNotNone(response.context["cells"][1]["exception"])
        self.assertContains(response, 'title="Sick"')

    def test_post_saves_morning_and_afternoon_separately_with_prefix(self):
        data = self._complete_post_data()
        data["exception_1_MORNING"] = self.role_fo.id
        data["exception_1_AFTERNOON"] = self.role_bo.id

        response = self.client.post(self.url, data)

        monday = get_week_dates(2026, 12)[0]
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            AvailabilityException.objects.get(
                user=self.employee, date=monday, part_of_day="MORNING"
            ).role,
            self.role_fo,
        )
        afternoon = AvailabilityException.objects.get(
            user=self.employee, date=monday, part_of_day="AFTERNOON"
        )
        self.assertEqual(afternoon.role, self.role_bo)
        self.assertEqual(afternoon.note, f"{AVAILABILITY_EXCEPTION_PREFIX}Training")

    def test_empty_note_prevents_save_and_shows_warning(self):
        data = self._complete_post_data(note="", exception_1_MORNING=self.role_fo.id)

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a reason")
        self.assertFalse(AvailabilityException.objects.filter(user=self.employee).exists())

    def test_post_without_changes_does_not_create_exceptions(self):
        response = self.client.post(self.url, self._complete_post_data())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Change at least one part of the day")
        self.assertFalse(AvailabilityException.objects.filter(user=self.employee).exists())

    def test_invalid_week_disables_save_and_does_not_store(self):
        data = self._complete_post_data(week=54, exception_1_MORNING=self.role_fo.id)

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "invalid")
        self.assertContains(response, 'id="save-button"')
        self.assertFalse(AvailabilityException.objects.filter(user=self.employee).exists())
