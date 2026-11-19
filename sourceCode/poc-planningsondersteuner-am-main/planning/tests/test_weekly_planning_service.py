from django.contrib.auth import get_user_model
from django.test import TestCase

from planning.models import (
    AvailabilityException,
    DefaultAvailability,
    Role,
    VacationRequest,
    WeeklyPlanning,
)
from planning.services import AVAILABILITY_EXCEPTION_PREFIX
from planning.services.weekly_planning import (
    build_planning_table,
    build_readonly_weekly_planning,
    get_effective_role,
    get_monday_for_week,
    get_next_iso_week,
    get_planning_role_details,
    get_planning_employees,
    get_week_dates,
    is_on_approved_vacation,
    save_weekly_planning,
    validate_year_week,
)

User = get_user_model()


class ValidateYearWeekTest(TestCase):
    def test_accepts_year_boundaries_and_valid_week(self):
        self.assertEqual(validate_year_week("2020", "53"), (2020, 53, None))
        self.assertEqual(validate_year_week("2040", "1"), (2040, 1, None))

    def test_rejects_year_outside_allowed_range(self):
        _year, _week, error = validate_year_week("2019", "1")
        self.assertIn("2020", error)
        self.assertIn("2040", error)

    def test_rejects_week_above_iso_maximum(self):
        _year, _week, error = validate_year_week("2021", "53")
        self.assertIn("1 tot en met 52", error)

    def test_rejects_non_numeric_input(self):
        _year, _week, error = validate_year_week("jaar", "week")
        self.assertIn("geldig", error)


class GetWeekDatesTest(TestCase):
    def test_get_monday_for_week_is_a_monday_in_the_right_week(self):
        monday = get_monday_for_week(2026, 12)

        self.assertEqual(monday.isoweekday(), 1)
        self.assertEqual(monday.isocalendar()[:2], (2026, 12))

    def test_get_week_dates_returns_five_consecutive_weekdays(self):
        dates = get_week_dates(2026, 12)

        self.assertEqual(len(dates), 5)
        self.assertEqual([date.isoweekday() for date in dates], [1, 2, 3, 4, 5])


class GetNextIsoWeekTest(TestCase):
    def test_returns_the_next_week_within_the_same_year(self):
        self.assertEqual(get_next_iso_week(2026, 32), (2026, 33))

    def test_returns_week_one_of_the_next_year_after_week_52(self):
        self.assertEqual(get_next_iso_week(2025, 52), (2026, 1))

    def test_returns_week_one_of_the_next_year_after_week_53(self):
        self.assertEqual(get_next_iso_week(2026, 53), (2027, 1))


class GetPlanningEmployeesTest(TestCase):
    def setUp(self):
        self.employee = User.objects.create_user(username="employee1", password="x")
        self.planner = User.objects.create_user(
            username="planner1", password="x", is_staff=True
        )

    def test_excludes_staff_users(self):
        employees = list(get_planning_employees())

        self.assertIn(self.employee, employees)
        self.assertNotIn(self.planner, employees)


class IsOnApprovedVacationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="employee1", password="x")
        self.week_dates = get_week_dates(2026, 12)
        self.monday = self.week_dates[0]

    def test_true_when_approved_vacation_covers_the_date(self):
        VacationRequest.objects.create(
            user=self.user,
            start_date=self.week_dates[0],
            end_date=self.week_dates[-1],
            planning_status=VacationRequest.PlanningStatus.APPROVED,
        )

        self.assertTrue(is_on_approved_vacation(self.user, self.monday))

    def test_false_when_vacation_is_still_pending(self):
        VacationRequest.objects.create(
            user=self.user,
            start_date=self.week_dates[0],
            end_date=self.week_dates[-1],
        )

        self.assertFalse(is_on_approved_vacation(self.user, self.monday))

    def test_false_when_date_is_outside_the_vacation_range(self):
        VacationRequest.objects.create(
            user=self.user,
            start_date=self.week_dates[0],
            end_date=self.week_dates[1],
            planning_status=VacationRequest.PlanningStatus.APPROVED,
        )

        self.assertFalse(is_on_approved_vacation(self.user, self.week_dates[-1]))


class GetEffectiveRoleTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="employee1", password="x")
        self.role_fo = Role.objects.get(name="FO")
        self.role_bo = Role.objects.get(name="BO")
        self.year, self.week_number = 2026, 12
        self.monday = get_monday_for_week(self.year, self.week_number)

    def test_returns_none_when_nothing_is_set(self):
        role = get_effective_role(
            self.user, self.monday, self.year, self.week_number, 1, "MORNING"
        )

        self.assertIsNone(role)

    def test_weekly_planning_is_used_for_the_requested_week(self):
        WeeklyPlanning.objects.create(
            user=self.user,
            year=self.year,
            week_number=self.week_number,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_bo,
        )

        role = get_effective_role(
            self.user, self.monday, self.year, self.week_number, 1, "MORNING"
        )

        self.assertEqual(role, self.role_bo)

    def test_default_availability_is_used_when_no_weekly_planning_exists(self):
        DefaultAvailability.objects.create(
            user=self.user, day_of_week=1, part_of_day="MORNING", role=self.role_fo,
        )

        role = get_effective_role(
            self.user, self.monday, self.year, self.week_number, 1, "MORNING"
        )

        self.assertEqual(role, self.role_fo)

    def test_approved_vacation_overrides_everything(self):
        WeeklyPlanning.objects.create(
            user=self.user,
            year=self.year,
            week_number=self.week_number,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_bo,
        )
        VacationRequest.objects.create(
            user=self.user,
            start_date=self.monday,
            end_date=self.monday,
            planning_status=VacationRequest.PlanningStatus.APPROVED,
        )

        role = get_effective_role(
            self.user, self.monday, self.year, self.week_number, 1, "MORNING"
        )

        self.assertIsNone(role)

    def test_availability_exception_overrides_weekly_planning(self):
        WeeklyPlanning.objects.create(
            user=self.user,
            year=self.year,
            week_number=self.week_number,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_bo,
        )
        AvailabilityException.objects.create(
            user=self.user,
            date=self.monday,
            part_of_day="MORNING",
            role=self.role_fo,
            is_available=True,
            reason=AvailabilityException.Reason.AVAILABILITY_EXCEPTION,
            note=f"{AVAILABILITY_EXCEPTION_PREFIX}Training",
        )

        role = get_effective_role(
            self.user, self.monday, self.year, self.week_number, 1, "MORNING"
        )

        self.assertEqual(role, self.role_fo)

    def test_unavailable_exception_overrides_weekly_planning_with_na(self):
        WeeklyPlanning.objects.create(
            user=self.user,
            year=self.year,
            week_number=self.week_number,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_bo,
        )
        AvailabilityException.objects.create(
            user=self.user,
            date=self.monday,
            part_of_day="MORNING",
            role=None,
            is_available=False,
            reason=AvailabilityException.Reason.AVAILABILITY_EXCEPTION,
            note=f"{AVAILABILITY_EXCEPTION_PREFIX}Niet beschikbaar",
        )

        role = get_effective_role(
            self.user, self.monday, self.year, self.week_number, 1, "MORNING"
        )

        self.assertIsNone(role)

    def test_planner_role_keeps_exception_readonly_and_uses_default_as_start_value(self):
        DefaultAvailability.objects.create(
            user=self.user,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_bo,
        )
        exception = AvailabilityException.objects.create(
            user=self.user,
            date=self.monday,
            part_of_day="MORNING",
            role=self.role_fo,
            is_available=True,
            reason=AvailabilityException.Reason.AVAILABILITY_EXCEPTION,
            note=f"{AVAILABILITY_EXCEPTION_PREFIX}Training",
        )

        role, returned_exception, on_leave = get_planning_role_details(
            self.user,
            self.monday,
            self.year,
            self.week_number,
            1,
            "MORNING",
        )

        self.assertEqual(role, self.role_bo)
        self.assertEqual(returned_exception, exception)
        self.assertFalse(on_leave)

    def test_planner_role_uses_saved_weekly_planning_over_default_availability(self):
        DefaultAvailability.objects.create(
            user=self.user,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_fo,
        )
        WeeklyPlanning.objects.create(
            user=self.user,
            year=self.year,
            week_number=self.week_number,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_bo,
        )

        role, exception, on_leave = get_planning_role_details(
            self.user,
            self.monday,
            self.year,
            self.week_number,
            1,
            "MORNING",
        )

        self.assertEqual(role, self.role_bo)
        self.assertIsNone(exception)
        self.assertFalse(on_leave)


class BuildPlanningTableTest(TestCase):
    def setUp(self):
        self.employee = User.objects.create_user(username="employee1", password="x")
        self.planner = User.objects.create_user(
            username="planner1", password="x", is_staff=True
        )
        self.year, self.week_number = 2026, 12
        self.monday = get_monday_for_week(self.year, self.week_number)

    def test_excludes_staff_from_the_rows(self):
        rows = build_planning_table(self.year, self.week_number)

        usernames = [row["user"].username for row in rows]
        self.assertIn("employee1", usernames)
        self.assertNotIn("planner1", usernames)

    def test_cell_has_no_role_and_is_not_on_leave_by_default(self):
        rows = build_planning_table(self.year, self.week_number)

        row = next(r for r in rows if r["user"] == self.employee)
        cell = next(
            c for c in row["cells"] if c["day_of_week"] == 1 and c["part_of_day"] == "MORNING"
        )

        self.assertIsNone(cell["role"])
        self.assertFalse(cell["on_leave"])

    def test_cell_uses_default_availability_when_weekly_planning_is_missing(self):
        DefaultAvailability.objects.create(
            user=self.employee,
            day_of_week=1,
            part_of_day="MORNING",
            role=Role.objects.get(name="FO"),
        )

        rows = build_planning_table(self.year, self.week_number)
        row = next(item for item in rows if item["user"] == self.employee)
        cell = next(
            item
            for item in row["cells"]
            if item["day_of_week"] == 1 and item["part_of_day"] == "MORNING"
        )

        self.assertEqual(cell["role"].name, "FO")

    def test_cell_marks_on_leave_for_approved_vacation(self):
        VacationRequest.objects.create(
            user=self.employee,
            start_date=self.monday,
            end_date=self.monday,
            planning_status=VacationRequest.PlanningStatus.APPROVED,
        )

        rows = build_planning_table(self.year, self.week_number)
        row = next(r for r in rows if r["user"] == self.employee)
        cell = next(
            c for c in row["cells"] if c["day_of_week"] == 1 and c["part_of_day"] == "MORNING"
        )

        self.assertTrue(cell["on_leave"])
        self.assertIsNone(cell["role"])


class BuildReadonlyWeeklyPlanningTest(TestCase):
    def setUp(self):
        self.employee = User.objects.create_user(username="employee1", password="x")
        self.other_employee = User.objects.create_user(username="employee2", password="x")
        self.role_fo = Role.objects.get(name="FO")
        self.year, self.week_number = 2026, 12

    def test_includes_only_saved_weekly_planning_for_selected_users(self):
        WeeklyPlanning.objects.create(
            user=self.employee,
            year=self.year,
            week_number=self.week_number,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_fo,
        )
        DefaultAvailability.objects.create(
            user=self.employee,
            day_of_week=1,
            part_of_day="AFTERNOON",
            role=self.role_fo,
        )

        week_dates, rows = build_readonly_weekly_planning(
            self.year,
            self.week_number,
            [self.employee],
        )

        self.assertEqual(len(week_dates), 5)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["cells"][0]["role"], self.role_fo)
        self.assertIsNone(rows[0]["cells"][1]["role"])


class SaveWeeklyPlanningTest(TestCase):
    def setUp(self):
        self.employee = User.objects.create_user(username="employee1", password="x")
        self.role_fo = Role.objects.get(name="FO")
        self.role_bo = Role.objects.get(name="BO")
        self.year, self.week_number = 2026, 12
        self.monday = get_monday_for_week(self.year, self.week_number)

    def test_creates_a_weekly_planning_entry(self):
        save_weekly_planning(
            self.year,
            self.week_number,
            [
                {
                    "user_id": self.employee.id,
                    "day_of_week": 1,
                    "part_of_day": "MORNING",
                    "role_id": self.role_fo.id,
                }
            ],
        )

        entry = WeeklyPlanning.objects.get(
            user=self.employee,
            year=self.year,
            week_number=self.week_number,
            day_of_week=1,
            part_of_day="MORNING",
        )
        self.assertEqual(entry.role, self.role_fo)

    def test_updates_an_existing_entry(self):
        WeeklyPlanning.objects.create(
            user=self.employee,
            year=self.year,
            week_number=self.week_number,
            day_of_week=1,
            part_of_day="MORNING",
            role=self.role_fo,
        )

        save_weekly_planning(
            self.year,
            self.week_number,
            [
                {
                    "user_id": self.employee.id,
                    "day_of_week": 1,
                    "part_of_day": "MORNING",
                    "role_id": self.role_bo.id,
                }
            ],
        )

        entry = WeeklyPlanning.objects.get(
            user=self.employee,
            year=self.year,
            week_number=self.week_number,
            day_of_week=1,
            part_of_day="MORNING",
        )
        self.assertEqual(entry.role, self.role_bo)

    def test_skips_days_with_an_approved_vacation(self):
        VacationRequest.objects.create(
            user=self.employee,
            start_date=self.monday,
            end_date=self.monday,
            planning_status=VacationRequest.PlanningStatus.APPROVED,
        )

        save_weekly_planning(
            self.year,
            self.week_number,
            [
                {
                    "user_id": self.employee.id,
                    "day_of_week": 1,
                    "part_of_day": "MORNING",
                    "role_id": self.role_fo.id,
                }
            ],
        )

        self.assertFalse(
            WeeklyPlanning.objects.filter(
                user=self.employee,
                year=self.year,
                week_number=self.week_number,
                day_of_week=1,
                part_of_day="MORNING",
            ).exists()
        )

    def test_planner_saves_weekly_planning_without_changing_employee_exception(self):
        exception = AvailabilityException.objects.create(
            user=self.employee,
            date=self.monday,
            part_of_day="MORNING",
            role=None,
            is_available=False,
            reason=AvailabilityException.Reason.AVAILABILITY_EXCEPTION,
            note=f"{AVAILABILITY_EXCEPTION_PREFIX}Training",
        )

        save_weekly_planning(
            self.year,
            self.week_number,
            [
                {
                    "user_id": self.employee.id,
                    "day_of_week": 1,
                    "part_of_day": "MORNING",
                    "role_id": self.role_fo.id,
                }
            ],
        )

        exception.refresh_from_db()
        self.assertIsNone(exception.role)
        self.assertFalse(exception.is_available)
        self.assertEqual(exception.note, f"{AVAILABILITY_EXCEPTION_PREFIX}Training")
        self.assertEqual(
            WeeklyPlanning.objects.get(
                user=self.employee,
                year=self.year,
                week_number=self.week_number,
                day_of_week=1,
                part_of_day="MORNING",
            ).role,
            self.role_fo,
        )
