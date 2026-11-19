"""Service voor het valideren van personeelsbezetting tegen capaciteitsregels."""

from collections import Counter

from ..models import CapacityRule, Role


def format_capacity_option(value):
    """Maakt een opgeslagen FTE-waarde geschikt voor dropdownvergelijking."""
    if value is None:
        return ""
    return str(value)


def parse_capacity_input(post_data, week_dates):
    """Leest minimale FTE per rol/dag/dagdeel uit dashboard-POST-data."""
    minimums = []
    for key, value in post_data.items():
        if not key.startswith("capacity_"):
            continue
        role_id, day_of_week, part_of_day = key.removeprefix("capacity_").split("_", 2)
        minimums.append(
            {
                "role_id": int(role_id),
                "date": week_dates[int(day_of_week) - 1],
                "part_of_day": part_of_day,
                "min_required_fte": int(value) if value else None,
            }
        )
    return minimums


def get_required_fte(role, on_date, part_of_day):
    """Geeft de ingestelde minimale FTE voor een rol op een specifieke datum en dagdeel.

    Retourneert None wanneer er voor die exacte datum/dagdeel nog geen
    capaciteitsregel is ingesteld.
    """
    rule = CapacityRule.objects.filter(
        role=role,
        applies_from=on_date,
        applies_to=on_date,
        part_of_day=part_of_day,
    ).first()
    return rule.min_required_fte if rule else None


def is_understaffed(role, on_date, part_of_day, scheduled_count):
    """Bepaalt of een rol op een datum/dagdeel onderbezet is t.o.v. de ingestelde minimale FTE.

    Zonder ingestelde minimale FTE is er geen norm om aan te toetsen, dus is
    er per definitie geen onderbezetting.
    """
    required = get_required_fte(role, on_date, part_of_day)
    if required is None:
        return False
    return scheduled_count < required


def count_scheduled_per_role(planning_rows):
    """Telt per (rol-id, datum, dagdeel) hoeveel medewerkers zijn ingepland.

    `planning_rows` is de output van weekly_planning.build_planning_table().
    """
    counts = Counter()
    for row in planning_rows:
        for cell in row["cells"]:
            if cell["role"] is not None:
                counts[(cell["role"].id, cell["date"], cell["part_of_day"])] += 1
    return counts


def build_capacity_overview(planning_rows, week_dates):
    """Bouwt het bezettingsoverzicht per actieve rol voor een week.

    Elke cel bevat het aantal ingeplande medewerkers, de huidige ingestelde
    minimale FTE voor precies die datum/dagdeel (of None als die nog niet is
    ingesteld) en of dat onderbezetting oplevert.
    """
    counts = count_scheduled_per_role(planning_rows)
    part_of_day_values = CapacityRule.PartOfDay.values

    overview = []
    for role in Role.objects.filter(is_active=True):
        cells = []
        for day_index, date in enumerate(week_dates):
            day_of_week = day_index + 1
            for part_of_day in part_of_day_values:
                scheduled_count = counts.get((role.id, date, part_of_day), 0)
                required_fte = get_required_fte(role, date, part_of_day)
                cells.append(
                    {
                        "day_of_week": day_of_week,
                        "date": date,
                        "part_of_day": part_of_day,
                        "scheduled_count": scheduled_count,
                        "required_fte": required_fte,
                        "required_fte_option": format_capacity_option(required_fte),
                        "understaffed": is_understaffed(
                            role, date, part_of_day, scheduled_count
                        ),
                    }
                )
        overview.append({"role": role, "cells": cells})

    return overview


def save_capacity_minimums(minimums):
    """Slaat de ingevoerde minimale FTE per rol/datum/dagdeel op.

    `minimums` is een lijst van dicts met role_id, date, part_of_day en
    min_required_fte.
    """
    for entry in minimums:
        role = Role.objects.get(pk=entry["role_id"])
        lookup = {
            "role": role,
            "applies_from": entry["date"],
            "applies_to": entry["date"],
            "part_of_day": entry["part_of_day"],
        }
        if entry["min_required_fte"] is None:
            CapacityRule.objects.filter(**lookup).delete()
            continue
        CapacityRule.objects.update_or_create(
            **lookup,
            defaults={"min_required_fte": entry["min_required_fte"]},
        )
