from django.contrib.auth import get_user_model
from django.test import TestCase

from planning.models import VacationRequest
from planning.services import (
    apply_action_to_requests,
    get_employees,
    get_filtered_vacation_requests,
)

User = get_user_model()


class GetEmployeesTest(TestCase):
    def setUp(self):
        self.employee1 = User.objects.create_user(username="employee1", password="x")
        self.employee2 = User.objects.create_user(username="employee2", password="x")
        self.planner = User.objects.create_user(
            username="planner1", password="x", is_staff=True
        )
        self.admin = User.objects.create_superuser(
            username="admin", password="x", email="admin@example.com"
        )

    def test_returns_only_non_staff_users(self):
        employees = list(get_employees())

        self.assertIn(self.employee1, employees)
        self.assertIn(self.employee2, employees)
        self.assertNotIn(self.planner, employees)
        self.assertNotIn(self.admin, employees)


class GetFilteredVacationRequestsTest(TestCase):
    def setUp(self):
        self.employee1 = User.objects.create_user(username="employee1", password="x")
        self.employee2 = User.objects.create_user(username="employee2", password="x")

        self.pending_request = VacationRequest.objects.create(
            user=self.employee1,
            start_date="2026-09-01",
            end_date="2026-09-05",
        )
        self.approved_request = VacationRequest.objects.create(
            user=self.employee2,
            start_date="2026-10-01",
            end_date="2026-10-05",
            planning_status=VacationRequest.PlanningStatus.APPROVED,
        )

    def test_no_filters_returns_all_requests(self):
        requests = get_filtered_vacation_requests()

        self.assertEqual(set(requests), {self.pending_request, self.approved_request})

    def test_filters_by_status(self):
        requests = get_filtered_vacation_requests(status="APPROVED")

        self.assertEqual(list(requests), [self.approved_request])

    def test_filters_by_user(self):
        requests = get_filtered_vacation_requests(user_id=self.employee1.id)

        self.assertEqual(list(requests), [self.pending_request])

    def test_invalid_status_is_ignored(self):
        requests = get_filtered_vacation_requests(status="NOT_A_REAL_STATUS")

        self.assertEqual(set(requests), {self.pending_request, self.approved_request})


class ApplyActionToRequestsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="employee1", password="x")
        self.request1 = VacationRequest.objects.create(
            user=self.user,
            start_date="2026-09-01",
            end_date="2026-09-05",
        )
        self.request2 = VacationRequest.objects.create(
            user=self.user,
            start_date="2026-10-01",
            end_date="2026-10-05",
        )

    def test_approve_action_updates_status(self):
        updated = apply_action_to_requests("approve", [self.request1.id])

        self.assertTrue(updated)
        self.request1.refresh_from_db()
        self.assertEqual(
            self.request1.planning_status, VacationRequest.PlanningStatus.APPROVED
        )

    def test_only_selected_requests_are_updated(self):
        apply_action_to_requests("approve", [self.request1.id])

        self.request2.refresh_from_db()
        self.assertEqual(
            self.request2.planning_status, VacationRequest.PlanningStatus.PENDING
        )

    def test_multiple_selected_requests_are_all_updated(self):
        updated = apply_action_to_requests(
            "approve", [self.request1.id, self.request2.id]
        )

        self.assertTrue(updated)
        self.request1.refresh_from_db()
        self.request2.refresh_from_db()
        self.assertEqual(
            self.request1.planning_status, VacationRequest.PlanningStatus.APPROVED
        )
        self.assertEqual(
            self.request2.planning_status, VacationRequest.PlanningStatus.APPROVED
        )

    def test_decline_action_updates_status(self):
        updated = apply_action_to_requests("decline", [self.request1.id])

        self.assertTrue(updated)
        self.request1.refresh_from_db()
        self.assertEqual(
            self.request1.planning_status, VacationRequest.PlanningStatus.DECLINED
        )

    def test_invalid_action_does_nothing(self):
        updated = apply_action_to_requests("delete", [self.request1.id])

        self.assertFalse(updated)
        self.request1.refresh_from_db()
        self.assertEqual(
            self.request1.planning_status, VacationRequest.PlanningStatus.PENDING
        )

    def test_no_selected_ids_does_nothing(self):
        updated = apply_action_to_requests("approve", [])

        self.assertFalse(updated)
        self.request1.refresh_from_db()
        self.assertEqual(
            self.request1.planning_status, VacationRequest.PlanningStatus.PENDING
        )
