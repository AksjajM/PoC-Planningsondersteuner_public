from django.contrib.auth import get_user_model
from django.test import TestCase

from planning.models import VacationRequest
from planning.services.vacation_requests import (
    build_approval_request_overview,
    create_vacation_request,
    get_overlapping_vacation_requests,
    get_user_vacation_request_groups,
    get_vacation_conflict_summary,
)

User = get_user_model()


class VacationConflictServiceTest(TestCase):
    def setUp(self):
        self.employee1 = User.objects.create_user(username="employee1", password="x")
        self.employee2 = User.objects.create_user(username="employee2", password="x")
        self.employee3 = User.objects.create_user(username="employee3", password="x")
        self.request = VacationRequest.objects.create(
            user=self.employee1,
            start_date="2026-09-10",
            end_date="2026-09-15",
        )

    def test_finds_inclusive_date_overlap_for_active_requests(self):
        overlapping = VacationRequest.objects.create(
            user=self.employee2,
            start_date="2026-09-15",
            end_date="2026-09-20",
        )

        result = get_overlapping_vacation_requests(
            self.request.start_date, self.request.end_date
        )

        self.assertIn(overlapping, result)

    def test_ignores_declined_requests(self):
        declined = VacationRequest.objects.create(
            user=self.employee2,
            start_date="2026-09-12",
            end_date="2026-09-13",
            planning_status=VacationRequest.PlanningStatus.DECLINED,
        )

        result = get_overlapping_vacation_requests(
            self.request.start_date, self.request.end_date
        )

        self.assertNotIn(declined, result)

    def test_summary_counts_approved_and_pending_requests(self):
        VacationRequest.objects.create(
            user=self.employee2,
            start_date="2026-09-12",
            end_date="2026-09-13",
            planning_status=VacationRequest.PlanningStatus.APPROVED,
        )
        VacationRequest.objects.create(
            user=self.employee3,
            start_date="2026-09-14",
            end_date="2026-09-16",
        )

        summary = get_vacation_conflict_summary(
            self.request.start_date,
            self.request.end_date,
            exclude_request_id=self.request.id,
        )

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["approved_count"], 1)
        self.assertEqual(summary["pending_count"], 1)
        self.assertTrue(summary["has_conflict"])

    def test_summary_can_exclude_the_requesting_employee(self):
        own_request = VacationRequest.objects.create(
            user=self.employee1,
            start_date="2026-09-12",
            end_date="2026-09-13",
        )

        summary = get_vacation_conflict_summary(
            self.request.start_date,
            self.request.end_date,
            exclude_user_id=self.employee1.id,
        )

        self.assertEqual(summary["total"], 0)
        self.assertNotIn(own_request.user.username, summary["users"])

    def test_create_vacation_request_uses_default_status_and_note(self):
        created_request = create_vacation_request(
            self.employee2,
            "2026-10-01",
            "2026-10-03",
        )

        self.assertEqual(created_request.user, self.employee2)
        self.assertEqual(
            created_request.planning_status,
            VacationRequest.PlanningStatus.PENDING,
        )
        self.assertEqual(created_request.note, "Paid leave")

    def test_groups_employee_requests_by_status(self):
        approved_request = VacationRequest.objects.create(
            user=self.employee1,
            start_date="2026-10-01",
            end_date="2026-10-03",
            planning_status=VacationRequest.PlanningStatus.APPROVED,
        )

        groups = get_user_vacation_request_groups(self.employee1)

        self.assertEqual(list(groups["pending_requests"]), [self.request])
        self.assertEqual(list(groups["approved_requests"]), [approved_request])
        self.assertFalse(groups["declined_requests"].exists())

    def test_approval_overview_adds_conflicts_and_excludes_declined_requests(self):
        overlapping_request = VacationRequest.objects.create(
            user=self.employee2,
            start_date="2026-09-12",
            end_date="2026-09-13",
            planning_status=VacationRequest.PlanningStatus.APPROVED,
        )
        declined_request = VacationRequest.objects.create(
            user=self.employee3,
            start_date="2026-09-12",
            end_date="2026-09-13",
            planning_status=VacationRequest.PlanningStatus.DECLINED,
        )

        overview = build_approval_request_overview()

        self.assertEqual(overview["conflict_count"], 2)
        self.assertEqual(
            overview["requests"][0].conflict_summary["approved_count"],
            1,
        )
        declined_overview_request = next(
            request
            for request in overview["requests"]
            if request.id == declined_request.id
        )
        self.assertFalse(hasattr(declined_overview_request, "conflict_summary"))
        self.assertIn(overlapping_request, overview["approved_requests"])
