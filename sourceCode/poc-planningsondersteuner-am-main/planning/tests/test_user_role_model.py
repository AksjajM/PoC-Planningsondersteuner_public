from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from planning.models import Role, UserRole


class UserRoleModelTests(TestCase):
    def test_user_can_be_linked_to_role(self):
        """PLON-19: controleert dat een gebruiker aan een planbare rol gekoppeld kan worden."""
        user = get_user_model().objects.create_user(
            username="planner1",
            password="test-password",
        )
        role = Role.objects.create(name="Front Office")

        user_role = UserRole.objects.create(user=user, role=role)

        self.assertEqual(user_role.user, user)
        self.assertEqual(user_role.role, role)
        self.assertEqual(str(user_role), "planner1 - Front Office")

    def test_user_can_have_multiple_roles(self):
        """PLON-19: controleert dat één gebruiker meerdere planbare rollen kan hebben."""
        user = get_user_model().objects.create_user(
            username="employee1",
            password="test-password",
        )
        front_office = Role.objects.create(name="Front Office")
        back_office = Role.objects.create(name="Back Office")

        UserRole.objects.create(user=user, role=front_office)
        UserRole.objects.create(user=user, role=back_office)

        self.assertEqual(UserRole.objects.filter(user=user).count(), 2)

    def test_role_can_be_assigned_to_multiple_users(self):
        """PLON-19: controleert dat één rol aan meerdere gebruikers gekoppeld kan worden."""
        user_one = get_user_model().objects.create_user(
            username="employee1",
            password="test-password",
        )
        user_two = get_user_model().objects.create_user(
            username="employee2",
            password="test-password",
        )
        role = Role.objects.create(name="Front Office")

        UserRole.objects.create(user=user_one, role=role)
        UserRole.objects.create(user=user_two, role=role)

        self.assertEqual(UserRole.objects.filter(role=role).count(), 2)

    def test_duplicate_user_role_is_not_allowed(self):
        """PLON-19: controleert dat dezelfde gebruiker niet dubbel aan dezelfde rol gekoppeld kan worden."""
        user = get_user_model().objects.create_user(
            username="employee1",
            password="test-password",
        )
        role = Role.objects.create(name="Front Office")

        UserRole.objects.create(user=user, role=role)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserRole.objects.create(user=user, role=role)