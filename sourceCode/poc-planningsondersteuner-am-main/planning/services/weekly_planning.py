"""Service voor het opbouwen en opslaan van de weekplanning per medewerker."""

import datetime

from django.contrib.auth import get_user_model

from ..models import (
    AvailabilityException,
    DefaultAvailability,
    Role,
    VacationRequest,
    WeeklyPlanning,
)

DAYS_PER_WEEK = 5
MIN_PLANNING_YEAR = 2020
MAX_PLANNING_YEAR = 2040


def validate_year_week(year_value, week_value, language="nl"):
    """Valideert jaar/week voor een planningsoverzicht."""
    is_english = language == "en"
    try:
        year = int(year_value)
        week_number = int(week_value)
    except (TypeError, ValueError):
        message = (
            "The entered date is invalid. Enter a valid year and week number."
            if is_english
            else "De ingevoerde datum is niet geldig. Voer een geldig jaartal en weeknummer in."
        )
        return None, None, message

    if not MIN_PLANNING_YEAR <= year <= MAX_PLANNING_YEAR:
        message = (
            f"The entered date is invalid. Choose a year from {MIN_PLANNING_YEAR} "
            f"to {MAX_PLANNING_YEAR}."
            if is_english
            else f"De ingevoerde datum is niet geldig. Kies een jaar van {MIN_PLANNING_YEAR} tot en met {MAX_PLANNING_YEAR}."
        )
        return None, None, message

    maximum_week = datetime.date(year, 12, 28).isocalendar().week
    if not 1 <= week_number <= maximum_week:
        message = (
            f"The entered date is invalid. Choose a week from 1 to {maximum_week} "
            f"for {year}."
            if is_english
            else f"De ingevoerde datum is niet geldig. Kies voor {year} een week van 1 tot en met {maximum_week}."
        )
        return None, None, message

    return year, week_number, None


def parse_planning_input(post_data):
    """Leest weekplanning per medewerker/dag/dagdeel uit dashboard-POST-data."""
    assignments = []
    for key, value in post_data.items():
        if not key.startswith("planning_"):
            continue
        user_id, day_of_week, part_of_day = key.removeprefix("planning_").split("_", 2)
        assignments.append(
            {
                "user_id": int(user_id),
                "day_of_week": int(day_of_week),
                "part_of_day": part_of_day,
                "role_id": value or None,
            }
        )
    return assignments


def get_monday_for_week(year, week_number):
    """Geeft de datum van de maandag van een ISO-week."""
    return datetime.datetime.strptime(f"{year}-W{week_number:02d}-1", "%G-W%V-%u").date()


def get_week_dates(year, week_number):
    """Geeft de vijf datums (maandag t/m vrijdag) van een ISO-week."""
    monday = get_monday_for_week(year, week_number)
    return [monday + datetime.timedelta(days=offset) for offset in range(DAYS_PER_WEEK)]


def get_next_iso_week(year, week_number):
    """Geeft het ISO-jaar en weeknummer van de week na de gekozen week terug."""
    next_monday = get_monday_for_week(year, week_number) + datetime.timedelta(days=7)
    next_year, next_week, _day = next_monday.isocalendar()
    return next_year, next_week


def get_planning_employees():
    """Alle medewerkers die in de planning voorkomen (geen planners/admins)."""
    user_model = get_user_model()
    return user_model.objects.filter(is_staff=False).order_by("username")


def is_on_approved_vacation(user, on_date):
    """Bepaalt of een medewerker op een datum een goedgekeurde vakantieaanvraag heeft."""
    return VacationRequest.objects.filter(
        user=user,
        planning_status=VacationRequest.PlanningStatus.APPROVED,
        start_date__lte=on_date,
        end_date__gte=on_date,
    ).exists()


def get_default_availability_role(user, day_of_week, part_of_day):
    """Geeft de standaardrol van een medewerker voor een dagdeel terug."""
    availability = DefaultAvailability.objects.filter(
        user=user,
        day_of_week=day_of_week,
        part_of_day=part_of_day,
    ).select_related("role").first()
    return availability.role if availability is not None else None


def get_effective_role_details(
    user, on_date, year, week_number, day_of_week, part_of_day
):
    """Geeft de effectieve beschikbaarheid van een medewerker terug.

    Deze functie is bedoeld voor medewerkersschermen. De prioriteit is
    goedgekeurd verlof, exception, opgeslagen weekplanning en ten slotte de
    standaardbeschikbaarheid.
    """
    if is_on_approved_vacation(user, on_date):
        return None, None, True

    exception = AvailabilityException.objects.filter(
        user=user,
        date=on_date,
        part_of_day=part_of_day,
    ).select_related("role").first()
    if exception is not None:
        role = exception.role if exception.is_available else None
        return role, exception, False

    planned = WeeklyPlanning.objects.filter(
        user=user,
        year=year,
        week_number=week_number,
        day_of_week=day_of_week,
        part_of_day=part_of_day,
    ).select_related("role").first()
    if planned is not None:
        return planned.role, None, False

    return get_default_availability_role(user, day_of_week, part_of_day), None, False


def get_planning_role_details(user, on_date, year, week_number, day_of_week, part_of_day):
    """Geeft de plannerrol met een eventuele exception als readonly informatie.

    Een planner ziet eerst de opgeslagen weekplanning. Bestaat die nog niet,
    dan dient de standaardbeschikbaarheid als startwaarde. Een exception wordt
    altijd meegegeven als informatie, maar verandert de plannerrol niet.
    """
    exception = AvailabilityException.objects.filter(
        user=user,
        date=on_date,
        part_of_day=part_of_day,
    ).select_related("role").first()

    if is_on_approved_vacation(user, on_date):
        return None, exception, True

    planned = WeeklyPlanning.objects.filter(
        user=user,
        year=year,
        week_number=week_number,
        day_of_week=day_of_week,
        part_of_day=part_of_day,
    ).select_related("role").first()
    if planned is not None:
        return planned.role, exception, False

    return get_default_availability_role(user, day_of_week, part_of_day), exception, False


def get_effective_role(user, on_date, year, week_number, day_of_week, part_of_day):
    """Bepaalt de effectieve rol van een medewerker voor een dag/dagdeel.

    Een plannerweergave toont alleen expliciet opgeslagen weekplanning. De
    standaardbeschikbaarheid is een invoerbron voor medewerkers, maar wordt
    niet als planning voor iedere historische of toekomstige week beschouwd.
    """
    role, _exception, _on_leave = get_effective_role_details(
        user, on_date, year, week_number, day_of_week, part_of_day
    )
    return role


def build_planning_table(year, week_number):
    """Bouwt de planningtabel voor alle medewerkers voor een week.

    Retourneert een lijst van dicts per medewerker met de cellen voor die week.
    """
    week_dates = get_week_dates(year, week_number)
    rows = []

    for employee in get_planning_employees():
        cells = []
        for day_index, date in enumerate(week_dates):
            day_of_week = day_index + 1
            for part_of_day in WeeklyPlanning.PartOfDay.values:
                role, exception, on_leave = get_planning_role_details(
                    employee, date, year, week_number, day_of_week, part_of_day
                )
                cells.append(
                    {
                        "day_of_week": day_of_week,
                        "part_of_day": part_of_day,
                        "date": date,
                        "role": role,
                        "on_leave": on_leave,
                        "availability_exception": exception,
                        "availability_exception_note": (
                            exception.note or exception.get_reason_display()
                            if exception is not None
                            else ""
                        ),
                    }
                )
        rows.append(
            {
                "user": employee,
                "cells": cells,
                "role_ids": sorted(
                    {cell["role"].id for cell in cells if cell["role"] is not None}
                ),
            }
        )

    return rows


def build_readonly_weekly_planning(year, week_number, users):
    """Bouwt readonly opgeslagen weekplanning voor de opgegeven medewerkers.

    Standaardbeschikbaarheid, exceptions, verlof en capaciteit zijn bewust
    uitgesloten. Een ontbrekende record wordt door de template als N/A getoond.
    """
    users = list(users)
    week_dates = get_week_dates(year, week_number)
    planning_entries = WeeklyPlanning.objects.filter(
        user__in=users,
        year=year,
        week_number=week_number,
    ).select_related("role")
    planning_by_cell = {
        (entry.user_id, entry.day_of_week, entry.part_of_day): entry
        for entry in planning_entries
    }

    rows = []
    for user in users:
        cells = []
        for day_index, on_date in enumerate(week_dates, start=1):
            for part_of_day in WeeklyPlanning.PartOfDay.values:
                entry = planning_by_cell.get((user.id, day_index, part_of_day))
                cells.append(
                    {
                        "date": on_date,
                        "day_of_week": day_index,
                        "part_of_day": part_of_day,
                        "role": entry.role if entry is not None else None,
                    }
                )
        rows.append({"user": user, "cells": cells})

    return week_dates, rows


def save_weekly_planning(year, week_number, assignments):
    """Slaat de weekplanning op.

    `assignments` is een lijst van dicts met user_id, day_of_week, part_of_day
    en role_id (of None voor N/A). Dagen waarop de medewerker een goedgekeurde
    vakantieaanvraag heeft, worden overgeslagen: die blijven vrij.
    """
    week_dates = get_week_dates(year, week_number)
    user_model = get_user_model()

    for assignment in assignments:
        day_of_week = assignment["day_of_week"]
        date = week_dates[day_of_week - 1]
        user = user_model.objects.get(pk=assignment["user_id"])

        if is_on_approved_vacation(user, date):
            continue

        role = None
        if assignment.get("role_id"):
            role = Role.objects.get(pk=assignment["role_id"])

        WeeklyPlanning.objects.update_or_create(
            user=user,
            year=year,
            week_number=week_number,
            day_of_week=day_of_week,
            part_of_day=assignment["part_of_day"],
            defaults={"role": role},
        )


def build_employee_week_overview(user, year, current_week_number):
    """Bouwt het medewerkerweekoverzicht met standaardrollen en exceptions."""
    default_roles = {
        (item.day_of_week, item.part_of_day): item.role
        for item in DefaultAvailability.objects.filter(user=user).select_related("role")
    }
    first_date = get_week_dates(year, 1)[0]
    last_date = get_week_dates(year, 52)[-1]
    exceptions = AvailabilityException.objects.filter(
        user=user,
        date__range=(first_date, last_date),
    ).select_related("role")
    exception_map = {
        (item.date, item.part_of_day): item
        for item in exceptions
    }

    weeks_data = []
    for week_number in range(1, 53):
        try:
            week_dates = get_week_dates(year, week_number)
        except ValueError:
            continue

        days = []
        for day_of_week, on_date in enumerate(week_dates, start=1):
            morning_exception = exception_map.get(
                (on_date, DefaultAvailability.PartOfDay.MORNING)
            )
            afternoon_exception = exception_map.get(
                (on_date, DefaultAvailability.PartOfDay.AFTERNOON)
            )
            show_default = week_number >= current_week_number
            days.append(
                {
                    "date": on_date.strftime("%d/%m"),
                    "morning_role": (
                        default_roles.get(
                            (day_of_week, DefaultAvailability.PartOfDay.MORNING)
                        ).name
                        if show_default
                        and default_roles.get(
                            (day_of_week, DefaultAvailability.PartOfDay.MORNING)
                        )
                        else "-"
                    ),
                    "afternoon_role": (
                        default_roles.get(
                            (day_of_week, DefaultAvailability.PartOfDay.AFTERNOON)
                        ).name
                        if show_default
                        and default_roles.get(
                            (day_of_week, DefaultAvailability.PartOfDay.AFTERNOON)
                        )
                        else "-"
                    ),
                    "morning_exception": morning_exception,
                    "afternoon_exception": afternoon_exception,
                    "morning_exception_note": (
                        morning_exception.note
                        or morning_exception.get_reason_display()
                        if morning_exception is not None
                        else ""
                    ),
                    "afternoon_exception_note": (
                        afternoon_exception.note
                        or afternoon_exception.get_reason_display()
                        if afternoon_exception is not None
                        else ""
                    ),
                }
            )
        weeks_data.append({"week_number": week_number, "days": days})

    return weeks_data
