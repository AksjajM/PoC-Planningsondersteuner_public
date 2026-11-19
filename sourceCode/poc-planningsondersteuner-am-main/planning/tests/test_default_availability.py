from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from planning.models import DefaultAvailability, Role

User = get_user_model()


class DefaultAvailabilityModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testgebruiker",
            email="test@topdesk.com",
            password="testpassword123",
        )
        self.role_fo = Role.objects.get(name="FO")

    def test_create_default_availability(self):
        availability = DefaultAvailability.objects.create(
            user=self.user,
            day_of_week=DefaultAvailability.DayOfWeek.MONDAY,
            part_of_day=DefaultAvailability.PartOfDay.MORNING,
            role=self.role_fo,
        )
        self.assertEqual(availability.user, self.user)
        self.assertEqual(availability.day_of_week, 1)
        self.assertEqual(availability.part_of_day, "MORNING")
        self.assertEqual(availability.role, self.role_fo)
        self.assertIn("Maandag", str(availability))
        self.assertIn("Ochtend", str(availability))
        self.assertIn("FO", str(availability))


class DefaultAvailabilityViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testgebruiker",
            password="testpassword123",
        )
        self.url = reverse("planning:availability")
        self.role_fo = Role.objects.get(name="FO")
        self.role_bo = Role.objects.get(name="BO")

    def test_view_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/accounts/login/?next={self.url}")

    def test_get_availability_form(self):
        self.client.login(username="testgebruiker", password="testpassword123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "planning/availability.html")
        self.assertContains(response, "1_MORNING")

    def test_planner_cannot_open_availability_but_admin_can(self):
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

    def test_post_availability_form(self):
        self.client.login(username="testgebruiker", password="testpassword123")
        
        # Validation test: incomplete form should fail
        incomplete_data = {
            "1_MORNING": self.role_fo.id,
            # Missing other fields
        }
        response = self.client.post(self.url, incomplete_data)
        self.assertEqual(response.status_code, 200) # Form validation fails, returns 200 with form errors
        self.assertFormError(response.context['form'], '1_AFTERNOON', 'This field is required.')

        # Valid form data
        data = {
            "1_MORNING": self.role_fo.id,
            "1_AFTERNOON": self.role_bo.id,
            "2_MORNING": self.role_fo.id,
            "2_AFTERNOON": self.role_fo.id,
            "3_MORNING": self.role_bo.id,
            "3_AFTERNOON": self.role_bo.id,
            "4_MORNING": self.role_fo.id,
            "4_AFTERNOON": self.role_fo.id,
            "5_MORNING": self.role_fo.id,
            "5_AFTERNOON": self.role_fo.id,
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)
        
        # Check database
        mon_am = DefaultAvailability.objects.get(user=self.user, day_of_week=1, part_of_day="MORNING")
        mon_pm = DefaultAvailability.objects.get(user=self.user, day_of_week=1, part_of_day="AFTERNOON")
        self.assertEqual(mon_am.role, self.role_fo)
        self.assertEqual(mon_pm.role, self.role_bo)

        tue_am = DefaultAvailability.objects.get(user=self.user, day_of_week=2, part_of_day="MORNING")
        tue_pm = DefaultAvailability.objects.get(user=self.user, day_of_week=2, part_of_day="AFTERNOON")
        self.assertEqual(tue_am.role, self.role_fo)
        self.assertEqual(tue_pm.role, self.role_fo)

        wed_am = DefaultAvailability.objects.get(user=self.user, day_of_week=3, part_of_day="MORNING")
        wed_pm = DefaultAvailability.objects.get(user=self.user, day_of_week=3, part_of_day="AFTERNOON")
        self.assertEqual(wed_am.role, self.role_bo)
        self.assertEqual(wed_pm.role, self.role_bo)

        thu_am = DefaultAvailability.objects.get(user=self.user, day_of_week=4, part_of_day="MORNING")
        thu_pm = DefaultAvailability.objects.get(user=self.user, day_of_week=4, part_of_day="AFTERNOON")
        self.assertEqual(thu_am.role, self.role_fo)
        self.assertEqual(thu_pm.role, self.role_fo)

        fri_am = DefaultAvailability.objects.get(user=self.user, day_of_week=5, part_of_day="MORNING")
        fri_pm = DefaultAvailability.objects.get(user=self.user, day_of_week=5, part_of_day="AFTERNOON")
        self.assertEqual(fri_am.role, self.role_fo)
        self.assertEqual(fri_pm.role, self.role_fo)
