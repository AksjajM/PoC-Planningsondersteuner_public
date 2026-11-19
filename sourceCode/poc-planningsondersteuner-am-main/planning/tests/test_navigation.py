"""Tests for the basic layout and navigation."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class NavigationTests(TestCase):
    def setUp(self):
        """PLON-22: maakt testgebruikers aan voor navigatietests."""
        self.user = get_user_model().objects.create_user(
            username="employee1",
            password="test-password",
        )
        self.staff_user = get_user_model().objects.create_user(
            username="planner1",
            password="test-password",
            is_staff=True,
        )

    def test_authenticated_user_sees_main_navigation_links(self):
        """PLON-22: controleert dat een ingelogde gebruiker de hoofdnavigatie ziet."""
        self.client.login(username="employee1", password="test-password")

        response = self.client.get(reverse("planning:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "Standard availability")
        self.assertContains(response, "Request leave")
        self.assertContains(response, "Week overview")

    def test_staff_user_sees_admin_navigation_link(self):
        """PLON-22: controleert dat een staff-gebruiker de beheerlink ziet."""
        self.client.login(username="planner1", password="test-password")

        response = self.client.get(reverse("planning:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Beheer")
        self.assertContains(response, reverse("admin:index"))

    def test_planner_does_not_see_employee_only_navigation_links(self):
        self.client.login(username="planner1", password="test-password")

        response = self.client.get(reverse("planning:home"))

        self.assertNotContains(response, "Request leave")
        self.assertNotContains(response, "Vacation request")
        self.assertNotContains(response, "Standard availability")
        self.assertNotContains(response, "Week overview")

    def test_non_staff_user_does_not_see_admin_navigation_link(self):
        """PLON-22: controleert dat een gewone gebruiker geen beheerlink ziet."""
        self.client.login(username="employee1", password="test-password")

        response = self.client.get(reverse("planning:home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Beheer")

    def test_staff_user_sees_approve_requests_navigation_link(self):
        """PLON-39: controleert dat een staff-gebruiker de goedkeurlink ziet."""
        self.client.login(username="planner1", password="test-password")

        response = self.client.get(reverse("planning:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Approve requests")
        self.assertContains(response, reverse("planning:approve_requests"))

    def test_non_staff_user_does_not_see_approve_requests_navigation_link(self):
        """PLON-39: controleert dat een gewone gebruiker de goedkeurlink niet ziet."""
        self.client.login(username="employee1", password="test-password")

        response = self.client.get(reverse("planning:home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Approve requests")

    def test_navigation_pages_are_accessible_for_authenticated_user(self):
        """PLON-22: controleert dat de basisnavigatiepagina's bereikbaar zijn."""
        self.client.login(username="employee1", password="test-password")

        pages = [
            ("planning:availability", "Standard availability"),
            ("planning:absence", "Employee exceptions"),
            ("planning:week_overview", "Weekly overview Employee"),
        ]

        for url_name, expected_title in pages:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected_title)

    def test_navigation_pages_require_login(self):
        """PLON-22: controleert dat navigatiepagina's afgeschermd zijn voor anonieme gebruikers."""
        login_url = reverse("login")

        url_names = [
            "planning:availability",
            "planning:absence",
            "planning:week_overview",
        ]

        for url_name in url_names:
            with self.subTest(url_name=url_name):
                page_url = reverse(url_name)
                response = self.client.get(page_url)

                self.assertRedirects(response, f"{login_url}?next={page_url}")
