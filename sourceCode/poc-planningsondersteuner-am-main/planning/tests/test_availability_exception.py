from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from planning.models import AvailabilityException, Role

User = get_user_model()


class AvailabilityExceptionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testgebruiker",
            email="test@topdesk.com",
            password="testpassword123",
        )
        self.role_fo = Role.objects.get(name="FO")

    def test_create_availability_exception(self):
        exception = AvailabilityException.objects.create(
            user=self.user,
            role=self.role_fo,
            date="2026-08-10",
            part_of_day=AvailabilityException.PartOfDay.MORNING,
            is_available=False,
            reason=AvailabilityException.Reason.SICK,
        )
        self.assertEqual(exception.user, self.user)
        self.assertEqual(exception.role, self.role_fo)
        self.assertEqual(str(exception.date), "2026-08-10")
        self.assertEqual(exception.part_of_day, "MORNING")
        self.assertFalse(exception.is_available)
        self.assertEqual(exception.reason, "SICK")
        self.assertIn("Ochtend", str(exception))
        self.assertIn("Niet beschikbaar", str(exception))
        self.assertIn("Ziek", str(exception))

    def test_role_can_be_linked_to_multiple_availability_exceptions(self):
        AvailabilityException.objects.create(
            user=self.user,
            role=self.role_fo,
            date="2026-08-10",
            part_of_day=AvailabilityException.PartOfDay.MORNING,
            is_available=False,
            reason=AvailabilityException.Reason.SICK,
        )
        AvailabilityException.objects.create(
            user=self.user,
            role=self.role_fo,
            date="2026-08-11",
            part_of_day=AvailabilityException.PartOfDay.MORNING,
            is_available=False,
            reason=AvailabilityException.Reason.SICK,
        )

        self.assertEqual(self.role_fo.availability_exceptions.count(), 2)

    def test_role_is_optional(self):
        exception = AvailabilityException.objects.create(
            user=self.user,
            date="2026-08-10",
            part_of_day=AvailabilityException.PartOfDay.MORNING,
            is_available=False,
            reason=AvailabilityException.Reason.SICK,
        )

        self.assertIsNone(exception.role)

    def test_user_can_have_multiple_exceptions(self):
        AvailabilityException.objects.create(
            user=self.user,
            date="2026-08-10",
            part_of_day=AvailabilityException.PartOfDay.MORNING,
            is_available=False,
            reason=AvailabilityException.Reason.SICK,
        )
        AvailabilityException.objects.create(
            user=self.user,
            date="2026-08-10",
            part_of_day=AvailabilityException.PartOfDay.AFTERNOON,
            is_available=False,
            reason=AvailabilityException.Reason.PAID_LEAVE,
        )

        self.assertEqual(
            AvailabilityException.objects.filter(user=self.user).count(), 2
        )

    def test_duplicate_exception_for_same_user_date_and_part_of_day_is_not_allowed(self):
        AvailabilityException.objects.create(
            user=self.user,
            date="2026-08-10",
            part_of_day=AvailabilityException.PartOfDay.MORNING,
            is_available=False,
            reason=AvailabilityException.Reason.SICK,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AvailabilityException.objects.create(
                    user=self.user,
                    date="2026-08-10",
                    part_of_day=AvailabilityException.PartOfDay.MORNING,
                    is_available=False,
                    reason=AvailabilityException.Reason.PAID_LEAVE,
                )
