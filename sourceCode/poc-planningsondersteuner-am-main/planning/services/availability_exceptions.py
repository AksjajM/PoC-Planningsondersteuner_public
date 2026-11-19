"""Services voor tijdelijke beschikbaarheidsafwijkingen van medewerkers."""

from django.db import transaction

from ..models import AvailabilityException, Role

AVAILABILITY_EXCEPTION_PREFIX = "Availability exception entered by employee: "
PREVIOUS_AVAILABILITY_EXCEPTION_PREFIX = "Availability exception ingevoerd door medewerker: "
LEGACY_AVAILABILITY_EXCEPTION_PREFIX = "Availability exception: "
EXCEPTION_REASON_LABELS = {
    AvailabilityException.Reason.SICK: "Sick",
    AvailabilityException.Reason.PAID_LEAVE: "Paid leave",
    AvailabilityException.Reason.AVAILABILITY_EXCEPTION: "Availability exception",
}


def format_availability_exception_note(note):
    """Voegt de vaste prefix precies eenmaal toe aan een geldige toelichting."""
    text = (note or "").strip()
    for prefix in (
        AVAILABILITY_EXCEPTION_PREFIX,
        PREVIOUS_AVAILABILITY_EXCEPTION_PREFIX,
        LEGACY_AVAILABILITY_EXCEPTION_PREFIX,
    ):
        if text.startswith(prefix):
            text = text.removeprefix(prefix).strip()
    if not text:
        raise ValueError("Enter a reason before saving.")
    return f"{AVAILABILITY_EXCEPTION_PREFIX}{text}"


def get_exception_note(exception):
    """Geeft de exceptiontoelichting in het Engels terug voor de medewerkers-UI."""
    if exception.note:
        return format_availability_exception_note(exception.note)
    return EXCEPTION_REASON_LABELS[exception.reason]


def parse_availability_exception_input(post_data):
    """Leest de tien rolkeuzes uit de POST-data van het weekscherm."""
    assignments = []
    for key, value in post_data.items():
        if not key.startswith("exception_"):
            continue
        day_of_week, part_of_day = key.removeprefix("exception_").split("_", 1)
        assignments.append(
            {
                "day_of_week": int(day_of_week),
                "part_of_day": part_of_day,
                "role_id": value or None,
            }
        )
    return assignments


def build_availability_exception_week(user, week_dates):
    """Bouwt de actuele planning en uitzonderingen voor één medewerker en week."""
    from .weekly_planning import get_effective_role_details

    year, week_number, _day = week_dates[0].isocalendar()
    exceptions = AvailabilityException.objects.filter(
        user=user,
        date__range=(week_dates[0], week_dates[-1]),
    ).select_related("role")
    exception_map = {
        (exception.date, exception.part_of_day): exception
        for exception in exceptions
    }

    cells = []
    for day_of_week, date in enumerate(week_dates, start=1):
        for part_of_day in AvailabilityException.PartOfDay.values:
            exception = exception_map.get((date, part_of_day))
            role, _effective_exception, _on_leave = get_effective_role_details(
                user, date, year, week_number, day_of_week, part_of_day
            )
            role_id = role.id if role is not None else None
            cells.append(
                {
                    "date": date,
                    "day_of_week": day_of_week,
                    "part_of_day": part_of_day,
                    "role_id": role_id,
                    "initial_role_id": role_id,
                    "exception": exception,
                    "exception_note": (
                        get_exception_note(exception)
                        if exception is not None
                        else ""
                    ),
                }
            )
    return cells


def apply_submitted_roles(cells, assignments):
    """Behoudt ingevulde dropdownwaarden wanneer het formulier fouten bevat."""
    submitted = {
        (item["day_of_week"], item["part_of_day"]): item["role_id"]
        for item in assignments
    }
    for cell in cells:
        key = (cell["day_of_week"], cell["part_of_day"])
        if key in submitted:
            cell["role_id"] = submitted[key]
    return cells


def _validate_assignment(assignment, week_dates, roles):
    day_of_week = assignment["day_of_week"]
    part_of_day = assignment["part_of_day"]
    role_id = assignment.get("role_id")

    if not 1 <= day_of_week <= len(week_dates):
        raise ValueError("The selected day is not in the selected week.")
    if part_of_day not in AvailabilityException.PartOfDay.values:
        raise ValueError("The selected part of the day is invalid.")
    if role_id is not None and str(role_id) not in roles:
        raise ValueError("The selected role does not exist.")


@transaction.atomic
def save_availability_exceptions(user, week_dates, assignments, note):
    """Slaat uitsluitend gewijzigde dagdelen als beschikbaarheidsafwijking op."""
    prefixed_note = format_availability_exception_note(note)
    role_ids = {str(item["role_id"]) for item in assignments if item.get("role_id")}
    roles = {str(role_id): role for role_id, role in Role.objects.in_bulk(role_ids).items()}

    from .weekly_planning import get_effective_role

    existing = AvailabilityException.objects.filter(
        user=user,
        date__range=(week_dates[0], week_dates[-1]),
    )
    existing_map = {
        (exception.date, exception.part_of_day): exception
        for exception in existing
    }

    changed_count = 0
    for assignment in assignments:
        _validate_assignment(assignment, week_dates, roles)
        date = week_dates[assignment["day_of_week"] - 1]
        key = (date, assignment["part_of_day"])
        exception = existing_map.get(key)
        year, week_number, _day = date.isocalendar()
        current_role = get_effective_role(
            user,
            date,
            year,
            week_number,
            assignment["day_of_week"],
            assignment["part_of_day"],
        )
        current_role_id = str(current_role.id) if current_role is not None else None
        desired_role_id = (
            str(assignment["role_id"])
            if assignment.get("role_id") is not None
            else None
        )

        if current_role_id == desired_role_id:
            continue

        role = roles.get(desired_role_id)
        defaults = {
            "role": role,
            "is_available": role is not None,
            "reason": AvailabilityException.Reason.AVAILABILITY_EXCEPTION,
            "note": prefixed_note,
        }
        saved, _created = AvailabilityException.objects.update_or_create(
            user=user,
            date=date,
            part_of_day=assignment["part_of_day"],
            defaults=defaults,
        )
        existing_map[key] = saved
        changed_count += 1

    return changed_count
