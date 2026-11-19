from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthenticationTests(TestCase):
    def setUp(self):
        """PLON-21: maakt een testgebruiker aan voor login/logout-tests."""
        self.user = get_user_model().objects.create_user(
            username="employee1",
            password="test-password",
        )

    def test_login_page_is_accessible(self):
        """PLON-21: controleert dat de loginpagina bereikbaar is."""
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inloggen")

    def test_anonymous_user_is_redirected_from_planning_page_to_login(self):
        """PLON-21: controleert dat een niet-ingelogde gebruiker geen planningpagina kan bekijken."""
        planning_url = reverse("planning:home")
        login_url = reverse("login")

        response = self.client.get(planning_url)

        self.assertRedirects(response, f"{login_url}?next={planning_url}")

    def test_authenticated_user_can_access_planning_page(self):
        """PLON-21: controleert dat een ingelogde gebruiker de planningpagina kan openen."""
        self.client.login(username="employee1", password="test-password")

        response = self.client.get(reverse("planning:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "employee1")

    def test_user_can_logout_and_loses_access_to_planning_page(self):
        """PLON-21: controleert dat uitloggen werkt en toegang daarna opnieuw login vereist."""
        self.client.login(username="employee1", password="test-password")

        logout_response = self.client.post(reverse("logout"))

        self.assertRedirects(logout_response, reverse("login"))

        planning_response = self.client.get(reverse("planning:home"))

        self.assertEqual(planning_response.status_code, 302)