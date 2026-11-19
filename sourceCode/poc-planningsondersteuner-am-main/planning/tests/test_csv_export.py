"""Tests for exporting saved weekly planning data as CSV."""

import csv
from io import StringIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from planning.models import Role, WeeklyPlanning
from planning.services import CSV_HEADERS, build_weekly_planning_csv_rows

User = get_user_model()


class WeeklyPlanningCsvExportServiceTest(TestCase):
    """Verifies the exported values originate from saved weekly planning."""

    def setUp(self):
        self.employee = User.objects.create_user(username="employee1", password="x")
        self.role_fo = Role.objects.get(name="FO")

    def test_rows_contain_saved_role_and_na_for_empty_time_slot(self):
        WeeklyPlanning.objects.create(
            user=self.employee,
            year=2026,
            week_number=12,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_fo,
        )

        rows = build_weekly_planning_csv_rows(2026, 12)

        self.assertEqual(rows[0], ["employee1", 2026, 12, "2026-03-16", "Monday", "Morning", "FO"])
        self.assertEqual(rows[1][-1], "N/A")


class WeeklyPlanningCsvExportViewTest(TestCase):
    """Verifies CSV download permissions and response contents."""

    def setUp(self):
        self.url = reverse("planning:export_weekly_planning_csv")
        self.employee = User.objects.create_user(username="employee1", password="x")
        self.planner = User.objects.create_user(
            username="planner1",
            password="x",
            is_staff=True,
        )
        self.role_fo = Role.objects.get(name="FO")

    def test_employee_cannot_export_weekly_planning(self):
        self.client.login(username="employee1", password="x")

        response = self.client.get(self.url, {"year": 2026, "week": 12})

        self.assertEqual(response.status_code, 403)

    def test_planner_downloads_csv_for_selected_week(self):
        WeeklyPlanning.objects.create(
            user=self.employee,
            year=2026,
            week_number=12,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_fo,
        )
        self.client.login(username="planner1", password="x")

        response = self.client.get(self.url, {"year": 2026, "week": 12})

        rows = list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("weekly-planning-2026-week-12.csv", response["Content-Disposition"])
        self.assertEqual(rows[0], CSV_HEADERS)
        self.assertEqual(rows[1][-1], "FO")

    def test_invalid_week_returns_bad_request(self):
        self.client.login(username="planner1", password="x")

        response = self.client.get(self.url, {"year": 2026, "week": 54})

        self.assertEqual(response.status_code, 400)
