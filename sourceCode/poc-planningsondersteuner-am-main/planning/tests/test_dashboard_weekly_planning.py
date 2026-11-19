"""Tests for the readonly saved weekly planning on the dashboard."""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from planning.models import Role, WeeklyPlanning
from planning.services import get_next_iso_week

User = get_user_model()


class DashboardWeeklyPlanningTest(TestCase):
    """Verifies the dashboard scope and readonly weekly planning data."""

    def setUp(self):
        self.url = reverse("planning:home")
        self.employee = User.objects.create_user(username="employee1", password="x")
        self.other_employee = User.objects.create_user(username="employee2", password="x")
        self.planner = User.objects.create_user(
            username="planner1",
            password="x",
            is_staff=True,
        )
        self.role_fo = Role.objects.get(name="FO")
        self.year, self.week_number, _day = datetime.date.today().isocalendar()

    def test_employee_sees_all_saved_planning_and_na_when_missing(self):
        WeeklyPlanning.objects.create(
            user=self.employee,
            year=self.year,
            week_number=self.week_number,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_fo,
        )
        WeeklyPlanning.objects.create(
            user=self.other_employee,
            year=self.year,
            week_number=self.week_number,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_fo,
        )
        self.client.login(username="employee1", password="x")

        response = self.client.get(self.url)

        rows = response.context["planning_rows"]
        self.assertEqual(
            [row["user"] for row in rows],
            [self.employee, self.other_employee],
        )
        self.assertEqual(rows[0]["cells"][0]["role"], self.role_fo)
        self.assertIsNone(rows[0]["cells"][1]["role"])
        self.assertEqual(rows[1]["cells"][0]["role"], self.role_fo)
        self.assertContains(response, "Saved weekly planning")
        self.assertContains(response, "N/A")

    def test_planner_sees_all_employee_rows(self):
        self.client.login(username="planner1", password="x")

        response = self.client.get(self.url)

        usernames = [row["user"].username for row in response.context["planning_rows"]]
        self.assertEqual(usernames, ["employee1", "employee2"])

    def test_current_and_next_week_buttons_are_available(self):
        next_year, next_week = get_next_iso_week(self.year, self.week_number)
        self.client.login(username="employee1", password="x")

        response = self.client.get(self.url)

        self.assertContains(response, "Current week")
        self.assertContains(response, "Next week")
        self.assertContains(response, f"?year={next_year}&amp;week={next_week}")
