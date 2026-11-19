"""Tests voor de services achter het medewerkersuitzonderingenscherm."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from planning.models import AvailabilityException, Role
from planning.services import (
    AVAILABILITY_EXCEPTION_PREFIX,
    build_availability_exception_week,
    format_availability_exception_note,
    get_week_dates,
    save_availability_exceptions,
)

User = get_user_model()


class AvailabilityExceptionNoteTest(TestCase):
    def test_prefix_is_added_exactly_once(self):
        note = format_availability_exception_note("Training op locatie")
        prefixed = format_availability_exception_note(note)

        self.assertEqual(note, f"{AVAILABILITY_EXCEPTION_PREFIX}Training op locatie")
        self.assertEqual(prefixed, note)

    def test_empty_note_is_rejected(self):
        with self.assertRaisesMessage(ValueError, "Enter a reason"):
            format_availability_exception_note("  ")


class AvailabilityExceptionWeekServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="employee1", password="x")
        self.role_fo = Role.objects.get(name="FO")
        self.role_bo = Role.objects.get(name="BO")
        self.week_dates = get_week_dates(2026, 12)

    def test_week_builder_separates_morning_and_afternoon(self):
        AvailabilityException.objects.create(
            user=self.user,
            date=self.week_dates[0],
            part_of_day=AvailabilityException.PartOfDay.AFTERNOON,
            role=self.role_bo,
            is_available=True,
            reason=AvailabilityException.Reason.AVAILABILITY_EXCEPTION,
            note=f"{AVAILABILITY_EXCEPTION_PREFIX}Cursus",
        )

        cells = build_availability_exception_week(self.user, self.week_dates)

        self.assertEqual(len(cells), 10)
        self.assertIsNone(cells[0]["role_id"])
        self.assertEqual(cells[1]["role_id"], self.role_bo.id)

    def test_save_creates_prefixed_exceptions_per_day_part(self):
        changed = save_availability_exceptions(
            self.user,
            self.week_dates,
            [
                {"day_of_week": 1, "part_of_day": "MORNING", "role_id": self.role_fo.id},
                {"day_of_week": 1, "part_of_day": "AFTERNOON", "role_id": self.role_bo.id},
            ],
            "Andere inzet",
        )

        morning = AvailabilityException.objects.get(
            user=self.user,
            date=self.week_dates[0],
            part_of_day="MORNING",
        )
        afternoon = AvailabilityException.objects.get(
            user=self.user,
            date=self.week_dates[0],
            part_of_day="AFTERNOON",
        )
        self.assertEqual(changed, 2)
        self.assertEqual(morning.role, self.role_fo)
        self.assertEqual(afternoon.role, self.role_bo)
        self.assertEqual(morning.reason, AvailabilityException.Reason.AVAILABILITY_EXCEPTION)
        self.assertEqual(morning.note, f"{AVAILABILITY_EXCEPTION_PREFIX}Andere inzet")

    def test_unchanged_value_is_not_saved_again(self):
        exception = AvailabilityException.objects.create(
            user=self.user,
            date=self.week_dates[0],
            part_of_day="MORNING",
            role=self.role_fo,
            is_available=True,
            reason=AvailabilityException.Reason.AVAILABILITY_EXCEPTION,
            note=f"{AVAILABILITY_EXCEPTION_PREFIX}Oorspronkelijk",
        )

        changed = save_availability_exceptions(
            self.user,
            self.week_dates,
            [{"day_of_week": 1, "part_of_day": "MORNING", "role_id": self.role_fo.id}],
            "Nieuwe toelichting",
        )

        exception.refresh_from_db()
        self.assertEqual(changed, 0)
        self.assertEqual(exception.note, f"{AVAILABILITY_EXCEPTION_PREFIX}Oorspronkelijk")

    def test_changing_existing_role_to_na_stores_unavailability(self):
        AvailabilityException.objects.create(
            user=self.user,
            date=self.week_dates[0],
            part_of_day="MORNING",
            role=self.role_fo,
            is_available=True,
            reason=AvailabilityException.Reason.AVAILABILITY_EXCEPTION,
            note=f"{AVAILABILITY_EXCEPTION_PREFIX}Eerder",
        )

        changed = save_availability_exceptions(
            self.user,
            self.week_dates,
            [{"day_of_week": 1, "part_of_day": "MORNING", "role_id": None}],
            "Niet beschikbaar",
        )

        exception = AvailabilityException.objects.get(
            user=self.user,
            date=self.week_dates[0],
            part_of_day="MORNING",
        )
        self.assertEqual(changed, 1)
        self.assertFalse(exception.is_available)
        self.assertIsNone(exception.role)

    def test_unknown_role_is_rejected_without_saving(self):
        with self.assertRaisesMessage(ValueError, "selected role does not exist"):
            save_availability_exceptions(
                self.user,
                self.week_dates,
                [{"day_of_week": 1, "part_of_day": "MORNING", "role_id": 999999}],
                "Ongeldige rol",
            )

        self.assertFalse(AvailabilityException.objects.filter(user=self.user).exists())
