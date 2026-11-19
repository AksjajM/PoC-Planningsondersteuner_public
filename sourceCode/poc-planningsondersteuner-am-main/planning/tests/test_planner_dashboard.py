from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from planning.models import (
    AvailabilityException,
    CapacityRule,
    DefaultAvailability,
    Role,
    WeeklyPlanning,
)
from planning.services import AVAILABILITY_EXCEPTION_PREFIX
from planning.services.weekly_planning import get_week_dates

User = get_user_model()


class PlannerDashboardAccessTest(TestCase):
    def setUp(self):
        self.url = reverse("planning:planner_dashboard")
        self.employee = User.objects.create_user(username="employee1", password="x")
        self.planner = User.objects.create_user(
            username="planner1", password="x", is_staff=True
        )
        self.admin = User.objects.create_superuser(
            username="admin", password="x", email="admin@example.com"
        )

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_regular_employee_is_forbidden(self):
        self.client.login(username="employee1", password="x")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_planner_can_access(self):
        self.client.login(username="planner1", password="x")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "planning/planner_dashboard.html")

    def test_admin_can_access(self):
        self.client.login(username="admin", password="x")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class PlannerDashboardNavigationTest(TestCase):
    def setUp(self):
        self.employee = User.objects.create_user(username="employee1", password="x")
        self.planner = User.objects.create_user(
            username="planner1", password="x", is_staff=True
        )

    def test_staff_sees_the_planner_dashboard_link(self):
        self.client.login(username="planner1", password="x")

        response = self.client.get(reverse("planning:home"))

        self.assertContains(response, "Planner dashboard")

    def test_employee_does_not_see_the_planner_dashboard_link(self):
        self.client.login(username="employee1", password="x")

        response = self.client.get(reverse("planning:home"))

        self.assertNotContains(response, "Planner dashboard")

    def test_employee_still_sees_the_regular_dashboard_link(self):
        """De algemene 'Dashboard'-link (startpagina) blijft voor iedereen zichtbaar."""
        self.client.login(username="employee1", password="x")

        response = self.client.get(reverse("planning:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")


class PlannerDashboardContentTest(TestCase):
    def setUp(self):
        self.url = reverse("planning:planner_dashboard")
        self.planner = User.objects.create_user(
            username="planner1", password="x", is_staff=True
        )
        self.employee = User.objects.create_user(username="employee1", password="x")
        self.role_fo = Role.objects.get(name="FO")
        self.client.login(username="planner1", password="x")

    def test_shows_employees_but_not_staff(self):
        response = self.client.get(self.url, {"year": 2026, "week": 12})

        usernames = [row["user"].username for row in response.context["planning_rows"]]
        self.assertIn("employee1", usernames)
        self.assertNotIn("planner1", usernames)

    def test_shows_na_when_nothing_is_planned(self):
        response = self.client.get(self.url, {"year": 2026, "week": 12})

        self.assertContains(response, "N/A")

    def test_year_and_week_filter_change_week_dates(self):
        response = self.client.get(self.url, {"year": 2027, "week": 1})

        self.assertEqual(response.context["year"], 2027)
        self.assertEqual(response.context["week_number"], 1)
        self.assertEqual(response.context["week_dates"][0].year, 2027)

    def test_invalid_filter_shows_validation_error_in_red(self):
        response = self.client.get(self.url, {"year": 2041, "week": 54})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["validation_error"])
        self.assertContains(response, "niet geldig")
        self.assertContains(response, "color: #c0392b")
        self.assertContains(response, 'disabled title="Corrigeer eerst het jaar of de week."')
        self.assertContains(response, "background-color: #9ca3af")

    def test_invalid_post_does_not_save_and_shows_validation_error(self):
        response = self.client.post(
            self.url,
            {"year": 2019, "week_number": 1},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["validation_error"])
        self.assertFalse(WeeklyPlanning.objects.exists())

    def test_week_filter_loads_planning_for_requested_week(self):
        WeeklyPlanning.objects.create(
            user=self.employee,
            year=2026,
            week_number=12,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_fo,
        )

        week_12 = self.client.get(self.url, {"year": 2026, "week": 12})
        week_13 = self.client.get(self.url, {"year": 2026, "week": 13})

        self.assertEqual(week_12.context["planning_rows"][0]["cells"][0]["role"], self.role_fo)
        self.assertIsNone(week_13.context["planning_rows"][0]["cells"][0]["role"])

    def test_planner_sees_employee_exception_as_readonly_information(self):
        monday = get_week_dates(2026, 12)[0]
        DefaultAvailability.objects.create(
            user=self.employee,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_fo,
        )
        AvailabilityException.objects.create(
            user=self.employee,
            date=monday,
            part_of_day="MORNING",
            role=self.role_fo,
            is_available=True,
            reason=AvailabilityException.Reason.AVAILABILITY_EXCEPTION,
            note=f"{AVAILABILITY_EXCEPTION_PREFIX}Training",
        )

        response = self.client.get(self.url, {"year": 2026, "week": 12})

        cell = response.context["planning_rows"][0]["cells"][0]
        self.assertEqual(cell["role"], self.role_fo)
        self.assertIsNotNone(cell["availability_exception"])
        self.assertContains(response, f'title="{AVAILABILITY_EXCEPTION_PREFIX}Training"')
        self.assertNotContains(
            response, f'disabled title="{AVAILABILITY_EXCEPTION_PREFIX}Training"'
        )

    def test_dashboard_contains_dynamic_role_filter_and_capacity_dropdowns(self):
        response = self.client.get(self.url, {"year": 2026, "week": 12})

        self.assertContains(response, 'id="role-filter"')
        self.assertContains(response, 'class="capacity-cell')
        self.assertContains(response, 'class="planning-select"')
        self.assertContains(response, "Huidige week")
        self.assertContains(response, ">N/A</option>")

    def test_post_saves_planning_and_capacity(self):
        response = self.client.post(
            self.url,
            {
                "year": 2026,
                "week_number": 12,
                f"planning_{self.employee.id}_1_MORNING": self.role_fo.id,
                f"capacity_{self.role_fo.id}_1_MORNING": "2",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            WeeklyPlanning.objects.filter(
                user=self.employee,
                year=2026,
                week_number=12,
                day_of_week=1,
                part_of_day="MORNING",
                role=self.role_fo,
            ).exists()
        )

    def test_post_keeps_morning_and_afternoon_separate(self):
        self.client.post(
            self.url,
            {
                "year": 2026,
                "week_number": 12,
                f"planning_{self.employee.id}_1_MORNING": self.role_fo.id,
                f"planning_{self.employee.id}_1_AFTERNOON": "",
                f"capacity_{self.role_fo.id}_1_MORNING": "2",
                f"capacity_{self.role_fo.id}_1_AFTERNOON": "4",
            },
        )

        monday = get_week_dates(2026, 12)[0]
        self.assertEqual(
            CapacityRule.objects.get(
                role=self.role_fo, applies_from=monday, part_of_day="MORNING"
            ).min_required_fte,
            2,
        )
        self.assertEqual(
            CapacityRule.objects.get(
                role=self.role_fo, applies_from=monday, part_of_day="AFTERNOON"
            ).min_required_fte,
            4,
        )
        self.assertIsNone(
            WeeklyPlanning.objects.get(
                user=self.employee,
                year=2026,
                week_number=12,
                day_of_week=1,
                part_of_day="AFTERNOON",
            ).role
        )

    def test_saved_capacity_is_selected_after_redirect(self):
        response = self.client.post(
            self.url,
            {
                "year": 2026,
                "week_number": 12,
                f"capacity_{self.role_fo.id}_1_MORNING": "2",
            },
            follow=True,
        )

        self.assertContains(response, '<option value="2" selected>2 FTE</option>')
        self.assertTrue(
            CapacityRule.objects.filter(
                role=self.role_fo,
                part_of_day="MORNING",
                min_required_fte=2,
            ).exists()
        )
