from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from planning.models import AvailabilityException, DefaultAvailability, Role
import datetime

User = get_user_model()


class WeekOverviewViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testgebruiker",
            password="testpassword123",
        )
        self.url = reverse("planning:week_overview")
        self.role_fo = Role.objects.get(name="FO")

    def test_view_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/accounts/login/?next={self.url}")

    def test_week_overview_context(self):
        # Create some default availability
        DefaultAvailability.objects.create(
            user=self.user,
            day_of_week=DefaultAvailability.DayOfWeek.MONDAY,
            part_of_day=DefaultAvailability.PartOfDay.MORNING,
            role=self.role_fo,
        )

        self.client.login(username="testgebruiker", password="testpassword123")
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "planning/week_overview.html")
        
        weeks_data = response.context['weeks_data']
        self.assertEqual(len(weeks_data), 52)
        
        # Check current week contains FO
        current_week_num = datetime.date.today().isocalendar()[1]
        
        current_week_data = next((w for w in weeks_data if w['week_number'] == current_week_num), None)
        self.assertIsNotNone(current_week_data)
        
        # Monday is index 0
        monday_data = current_week_data['days'][0]
        self.assertEqual(monday_data['morning_role'], "FO")

    def test_planner_cannot_open_week_overview_but_admin_can(self):
        planner = User.objects.create_user(
            username="planner1",
            password="testpassword123",
            is_staff=True,
        )
        admin = User.objects.create_superuser(
            username="admin",
            password="testpassword123",
            email="admin@example.com",
        )

        self.client.login(username=planner.username, password="testpassword123")
        self.assertEqual(self.client.get(self.url).status_code, 403)

        self.client.login(username=admin.username, password="testpassword123")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_week_overview_shows_an_exception_separately_from_default_availability(self):
        year = datetime.date.today().year
        week_number = 1
        wednesday = datetime.date.fromisocalendar(year, week_number, 3)
        AvailabilityException.objects.create(
            user=self.user,
            date=wednesday,
            part_of_day=AvailabilityException.PartOfDay.MORNING,
            role=None,
            is_available=False,
            reason=AvailabilityException.Reason.SICK,
            note="Sick leave",
        )

        self.client.login(username="testgebruiker", password="testpassword123")
        response = self.client.get(self.url)

        current_week = next(
            week
            for week in response.context["weeks_data"]
            if week["week_number"] == week_number
        )
        wednesday_data = current_week["days"][2]
        self.assertIsNotNone(wednesday_data["morning_exception"])
        self.assertContains(response, 'title="Morning exception: Sick leave"')
