import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from planning.models import VacationRequest

User = get_user_model()


class VacationRequestModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testgebruiker",
            email="test@topdesk.com",
            password="testpassword123",
        )

    def test_create_vacation_request_defaults_to_pending(self):
        request = VacationRequest.objects.create(
            user=self.user,
            start_date="2026-08-10",
            end_date="2026-08-14",
        )
        self.assertEqual(request.user, self.user)
        self.assertEqual(str(request.start_date), "2026-08-10")
        self.assertEqual(str(request.end_date), "2026-08-14")
        self.assertEqual(request.planning_status, VacationRequest.PlanningStatus.PENDING)
        self.assertEqual(request.note, "Paid leave")
        self.assertIn("In behandeling", str(request))

    def test_created_on_is_set_automatically(self):
        request = VacationRequest.objects.create(
            user=self.user,
            start_date="2026-08-10",
            end_date="2026-08-14",
        )
        self.assertEqual(request.created_on, datetime.date.today())

    def test_create_vacation_request_with_explicit_status_and_note(self):
        request = VacationRequest.objects.create(
            user=self.user,
            start_date="2026-08-10",
            end_date="2026-08-14",
            planning_status=VacationRequest.PlanningStatus.APPROVED,
            note="Zomervakantie",
        )
        self.assertEqual(request.planning_status, "APPROVED")
        self.assertEqual(request.note, "Zomervakantie")
        self.assertIn("Goedgekeurd", str(request))

    def test_user_can_have_multiple_vacation_requests(self):
        VacationRequest.objects.create(
            user=self.user,
            start_date="2026-08-10",
            end_date="2026-08-14",
        )
        VacationRequest.objects.create(
            user=self.user,
            start_date="2026-12-24",
            end_date="2026-12-31",
        )

        self.assertEqual(VacationRequest.objects.filter(user=self.user).count(), 2)


class VacationRequestViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testgebruiker",
            password="testpassword123",
        )
        self.url = reverse("planning:vacation_request")

    def test_view_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/accounts/login/?next={self.url}")

    def test_get_vacation_request_form_has_no_note_field(self):
        self.client.login(username="testgebruiker", password="testpassword123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "planning/vacation_request.html")
        self.assertNotIn("note", response.context["form"].fields)

    def test_planner_cannot_open_vacation_request_but_admin_can(self):
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

    def test_post_vacation_request_creates_pending_request_with_default_note(self):
        self.client.login(username="testgebruiker", password="testpassword123")

        response = self.client.post(
            self.url,
            {"start_date": "2026-09-01", "end_date": "2026-09-05"},
        )

        self.assertRedirects(response, self.url)
        request = VacationRequest.objects.get(user=self.user)
        self.assertEqual(request.planning_status, VacationRequest.PlanningStatus.PENDING)
        self.assertEqual(request.note, "Paid leave")

    def test_post_vacation_request_is_submitted_with_conflict_warning(self):
        other_user = User.objects.create_user(username="employee2", password="x")
        VacationRequest.objects.create(
            user=other_user,
            start_date="2026-09-03",
            end_date="2026-09-07",
            planning_status=VacationRequest.PlanningStatus.APPROVED,
        )
        self.client.login(username="testgebruiker", password="testpassword123")

        response = self.client.post(
            self.url,
            {"start_date": "2026-09-05", "end_date": "2026-09-10"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(VacationRequest.objects.filter(user=self.user).exists())
        self.assertContains(response, "Let op: je aanvraag overlapt")

    def test_end_date_before_start_date_is_rejected(self):
        self.client.login(username="testgebruiker", password="testpassword123")

        response = self.client.post(
            self.url,
            {"start_date": "2026-09-05", "end_date": "2026-09-01"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(VacationRequest.objects.filter(user=self.user).exists())

    def test_requests_are_shown_in_matching_status_list(self):
        self.client.login(username="testgebruiker", password="testpassword123")
        VacationRequest.objects.create(
            user=self.user,
            start_date="2026-09-01",
            end_date="2026-09-05",
            planning_status=VacationRequest.PlanningStatus.APPROVED,
        )

        response = self.client.get(self.url)

        self.assertEqual(len(response.context["approved_requests"]), 1)
        self.assertEqual(len(response.context["pending_requests"]), 0)
        self.assertEqual(len(response.context["declined_requests"]), 0)
