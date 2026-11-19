"""Services for persisting an employee's default availability."""

from ..models import DefaultAvailability


def save_default_availability(user, cleaned_data):
    """Store the validated default role for every weekday and part of the day."""
    for day_value, _day_name in DefaultAvailability.DayOfWeek.choices:
        if day_value > 5:
            continue
        for part_value, _part_name in DefaultAvailability.PartOfDay.choices:
            field_name = f"{day_value}_{part_value}"
            DefaultAvailability.objects.update_or_create(
                user=user,
                day_of_week=day_value,
                part_of_day=part_value,
                defaults={"role": cleaned_data[field_name]},
            )
