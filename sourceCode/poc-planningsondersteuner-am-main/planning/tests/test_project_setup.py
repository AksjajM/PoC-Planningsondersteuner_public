"""Basic project setup tests for the Django PoC."""

from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase


class ProjectSetupTests(SimpleTestCase):
    def test_django_system_check_runs_without_errors(self):
        """PLON-15: controleert dat de Django-projectconfiguratie valide is."""
        call_command("check", stdout=StringIO())