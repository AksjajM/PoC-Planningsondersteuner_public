"""Tests for explanatory information shown on planning screens."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class PageInformationTest(TestCase):
    """Verifies each user role receives relevant screen guidance."""

    def setUp(self):
        self.employee = User.objects.create_user(username="employee1", password="x")
        self.planner = User.objects.create_user(
            username="planner1",
            password="x",
            is_staff=True,
        )

    def test_login_screen_explains_the_sign_in_purpose(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, "Sign in with your TOPdesk PoC account")

    def test_employee_screens_explain_their_purpose(self):
        self.client.login(username="employee1", password="x")
        expected_texts = {
            "planning:home": "saved weekly planning for all employees",
            "planning:availability": "Set your usual availability",
            "planning:absence": "Record a temporary change to your availability",
            "planning:vacation_request": "Submit a vacation request for a period.",
            "planning:week_overview": "does not show saved weekly planning",
        }

        for url_name, expected_text in expected_texts.items():
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertContains(response, expected_text)

    def test_planner_screens_explain_their_purpose(self):
        self.client.login(username="planner1", password="x")
        expected_texts = {
            "planning:approve_requests": "Review pending and approved vacation requests.",
            "planning:planner_dashboard": "Set the minimum required capacity",
        }

        for url_name, expected_text in expected_texts.items():
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertContains(response, expected_text)
