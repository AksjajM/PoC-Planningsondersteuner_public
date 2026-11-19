from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from planning.models import VacationRequest

User = get_user_model()


class ApproveRequestsAccessTest(TestCase):
    def setUp(self):
        self.url = reverse("planning:approve_requests")
        self.employee = User.objects.create_user(
            username="employee1",
            password="test-password",
        )
        self.planner = User.objects.create_user(
            username="planner1",
            password="test-password",
            is_staff=True,
        )

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_regular_employee_is_forbidden(self):
        self.client.login(username="employee1", password="test-password")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_staff_user_can_access(self):
        self.client.login(username="planner1", password="test-password")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "planning/approve_requests.html")


class ApproveRequestsListTest(TestCase):
    def setUp(self):
        self.url = reverse("planning:approve_requests")
        self.planner = User.objects.create_user(
            username="planner1",
            password="test-password",
            is_staff=True,
        )
        self.employee1 = User.objects.create_user(username="employee1", password="x")
        self.employee2 = User.objects.create_user(username="employee2", password="x")
        self.client.login(username="planner1", password="test-password")

        self.request1 = VacationRequest.objects.create(
            user=self.employee1,
            start_date="2026-09-01",
            end_date="2026-09-05",
        )
        self.request2 = VacationRequest.objects.create(
            user=self.employee2,
            start_date="2026-10-01",
            end_date="2026-10-05",
            planning_status=VacationRequest.PlanningStatus.APPROVED,
        )

    def test_shows_requests_from_all_users(self):
        response = self.client.get(self.url)

        self.assertContains(response, "employee1")
        self.assertContains(response, "employee2")

    def test_shows_overlap_explanation(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Wanneer is er sprake van overlap?")
        self.assertContains(response, "Afgewezen aanvragen worden niet meegerekend.")

    def test_shows_conflict_summary_for_overlapping_requests(self):
        VacationRequest.objects.create(
            user=self.employee2,
            start_date="2026-09-03",
            end_date="2026-09-04",
            planning_status=VacationRequest.PlanningStatus.APPROVED,
        )
        self.request1.start_date = "2026-09-01"
        self.request1.end_date = "2026-09-05"
        self.request1.save()

        response = self.client.get(self.url)

        request1 = next(
            item for item in response.context["requests"] if item.id == self.request1.id
        )
        self.assertEqual(request1.conflict_summary["approved_count"], 1)
        self.assertContains(response, "Conflict")
        self.assertContains(response, "Goedgekeurd: 1")

    def test_requests_are_split_into_status_lists(self):
        self.request1.planning_status = VacationRequest.PlanningStatus.DECLINED
        self.request1.save()

        response = self.client.get(self.url)

        self.assertEqual(response.context["pending_requests"], [])
        self.assertEqual(response.context["approved_requests"], [self.request2])
        self.assertEqual(response.context["declined_requests"], [self.request1])
        self.assertNotContains(response, "status-filter")

    def test_declined_requests_do_not_show_conflict_information(self):
        self.request1.planning_status = VacationRequest.PlanningStatus.DECLINED
        self.request1.save()
        VacationRequest.objects.create(
            user=self.employee2,
            start_date="2026-09-02",
            end_date="2026-09-04",
            planning_status=VacationRequest.PlanningStatus.APPROVED,
        )

        response = self.client.get(self.url)

        declined_position = response.content.decode().rindex("Declined requests")
        declined_section = response.content.decode()[declined_position:]
        self.assertNotIn("Conflict", declined_section)

    def test_user_filter(self):
        response = self.client.get(self.url, {"user": self.employee1.id})

        requests_shown = list(response.context["requests"])
        self.assertEqual(requests_shown, [self.request1])

    def test_approve_action_updates_selected_requests(self):
        response = self.client.post(
            self.url,
            {"action": "approve", "selected_requests": [self.request1.id]},
        )

        self.assertRedirects(response, self.url)
        self.request1.refresh_from_db()
        self.assertEqual(
            self.request1.planning_status, VacationRequest.PlanningStatus.APPROVED
        )

    def test_decline_action_updates_selected_requests(self):
        response = self.client.post(
            self.url,
            {"action": "decline", "selected_requests": [self.request1.id]},
        )

        self.assertRedirects(response, self.url)
        self.request1.refresh_from_db()
        self.request2.refresh_from_db()
        self.assertEqual(
            self.request1.planning_status, VacationRequest.PlanningStatus.DECLINED
        )
        self.assertEqual(
            self.request2.planning_status, VacationRequest.PlanningStatus.APPROVED,
            "niet-geselecteerde aanvraag mag niet wijzigen",
        )

    def test_multiple_selected_requests_are_all_updated(self):
        response = self.client.post(
            self.url,
            {
                "action": "decline",
                "selected_requests": [self.request1.id, self.request2.id],
            },
        )

        self.assertRedirects(response, self.url)
        self.request1.refresh_from_db()
        self.request2.refresh_from_db()
        self.assertEqual(
            self.request1.planning_status, VacationRequest.PlanningStatus.DECLINED
        )
        self.assertEqual(
            self.request2.planning_status, VacationRequest.PlanningStatus.DECLINED
        )

    def test_action_without_selection_changes_nothing(self):
        self.client.post(self.url, {"action": "approve", "selected_requests": []})

        self.request1.refresh_from_db()
        self.request2.refresh_from_db()
        self.assertEqual(
            self.request1.planning_status, VacationRequest.PlanningStatus.PENDING
        )
        self.assertEqual(
            self.request2.planning_status, VacationRequest.PlanningStatus.APPROVED
        )
