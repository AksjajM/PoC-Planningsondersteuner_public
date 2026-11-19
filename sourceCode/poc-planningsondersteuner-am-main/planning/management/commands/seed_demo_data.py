"""Management command for creating local demo data for the planning PoC."""

import os
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from planning.models import Role, UserRole, VacationRequest


DEMO_USERS = [
    {
        "username": "planner1",
        "email": "planner1@example.com",
        "first_name": "Demo",
        "last_name": "Planner",
        "is_staff": True,
    },
    {
        "username": "employee1",
        "email": "employee1@example.com",
        "first_name": "Demo",
        "last_name": "Employee One",
        "is_staff": False,
    },
    {
        "username": "employee2",
        "email": "employee2@example.com",
        "first_name": "Demo",
        "last_name": "Employee Two",
        "is_staff": False,
    },
    {
        "username": "employee3",
        "email": "employee3@example.com",
        "first_name": "Demo",
        "last_name": "Employee Three",
        "is_staff": False,
    },
    {
        "username": "employee4",
        "email": "employee4@example.com",
        "first_name": "Demo",
        "last_name": "Employee Four",
        "is_staff": False,
    },
]

DEMO_ASSIGNMENTS = [
    ("planner1", "FO"),
    ("planner1", "BO"),
    ("employee1", "FO"),
    ("employee2", "BO"),
    ("employee3", "FO"),
    ("employee4", "BO"),
]

DEMO_VACATION_REQUESTS = [
    {
        "username": "employee1",
        "start_date": date(2026, 9, 10),
        "end_date": date(2026, 9, 15),
        "planning_status": VacationRequest.PlanningStatus.PENDING,
    },
    {
        "username": "employee2",
        "start_date": date(2026, 9, 12),
        "end_date": date(2026, 9, 13),
        "planning_status": VacationRequest.PlanningStatus.APPROVED,
    },
    {
        "username": "employee3",
        "start_date": date(2026, 9, 13),
        "end_date": date(2026, 9, 16),
        "planning_status": VacationRequest.PlanningStatus.PENDING,
    },
    {
        "username": "employee4",
        "start_date": date(2026, 9, 14),
        "end_date": date(2026, 9, 15),
        "planning_status": VacationRequest.PlanningStatus.DECLINED,
    },
]


class Command(BaseCommand):
    """Create demo users, role assignments and vacation requests for local testing."""

    help = "Seed local demo data for the PoC Planningsondersteuner."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow running the command when DEBUG=False.",
        )
        parser.add_argument(
            "--with-admin",
            action="store_true",
            help="Create a local demo superuser.",
        )
        parser.add_argument(
            "--password",
            default=os.getenv("DEMO_USER_PASSWORD", "ChangeMe123!"),
            help="Password used for demo users. Default is for local demo only.",
        )

    def handle(self, *args, **options):
        """PLON-23: create reproducible demo data for local development and testing."""
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "Refusing to seed demo data when DEBUG=False. "
                "Use --force only when this is an intentional non-production action."
            )

        password = options["password"]
        user_model = get_user_model()

        users = self._create_users(user_model, password)
        self._assign_roles(users)
        self._create_vacation_requests(users)

        if options["with_admin"]:
            self._create_demo_admin(user_model, password)

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data created: users, user-role assignments and vacation requests "
                "are available."
            )
        )

    def _create_users(self, user_model, password):
        users = {}

        for user_data in DEMO_USERS:
            user, _created = user_model.objects.get_or_create(
                username=user_data["username"],
                defaults={
                    "email": user_data["email"],
                    "first_name": user_data["first_name"],
                    "last_name": user_data["last_name"],
                    "is_staff": user_data["is_staff"],
                },
            )

            user.email = user_data["email"]
            user.first_name = user_data["first_name"]
            user.last_name = user_data["last_name"]
            user.is_staff = user_data["is_staff"]
            user.set_password(password)
            user.save()

            users[user.username] = user

        return users

    def _assign_roles(self, users):
        for username, role_name in DEMO_ASSIGNMENTS:
            role = Role.objects.get(name=role_name)
            UserRole.objects.get_or_create(
                user=users[username],
                role=role,
            )

    def _create_vacation_requests(self, users):
        """Create a fixed, overlapping vacation scenario without duplicates."""
        for request_data in DEMO_VACATION_REQUESTS:
            VacationRequest.objects.get_or_create(
                user=users[request_data["username"]],
                start_date=request_data["start_date"],
                end_date=request_data["end_date"],
                defaults={
                    "planning_status": request_data["planning_status"],
                    "note": "Demo conflict scenario",
                },
            )

    def _create_demo_admin(self, user_model, password):
        admin_user, _created = user_model.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "first_name": "Demo",
                "last_name": "Admin",
            },
        )

        admin_user.email = "admin@example.com"
        admin_user.first_name = "Demo"
        admin_user.last_name = "Admin"
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.set_password(password)
        admin_user.save()
