from django.test import TestCase

from planning.models import CapacityRule, Role
from planning.services.capacity import (
    build_capacity_overview,
    format_capacity_option,
    get_required_fte,
    is_understaffed,
    parse_capacity_input,
    save_capacity_minimums,
)
from planning.services.weekly_planning import get_week_dates


class FormatCapacityOptionTest(TestCase):
    def test_formats_integer_values_for_dropdowns(self):
        self.assertEqual(format_capacity_option(2), "2")

    def test_formats_empty_value_as_empty_option(self):
        self.assertEqual(format_capacity_option(None), "")


class ParseCapacityInputTest(TestCase):
    def test_parses_a_selected_fte_as_an_integer(self):
        week_dates = get_week_dates(2026, 12)

        minimums = parse_capacity_input(
            {"capacity_1_1_MORNING": "3", "capacity_1_1_AFTERNOON": ""},
            week_dates,
        )

        self.assertEqual(minimums[0]["min_required_fte"], 3)
        self.assertIsNone(minimums[1]["min_required_fte"])
class GetRequiredFteTest(TestCase):
    def setUp(self):
        self.role_fo = Role.objects.get(name="FO")
        self.week_dates = get_week_dates(2026, 12)
        self.monday = self.week_dates[0]

    def test_returns_none_without_a_capacity_rule(self):
        self.assertIsNone(get_required_fte(self.role_fo, self.monday, "MORNING"))

    def test_returns_the_minimum_for_the_exact_date_and_part_of_day(self):
        CapacityRule.objects.create(
            role=self.role_fo,
            part_of_day="MORNING",
            min_required_fte=2,
            applies_from=self.monday,
            applies_to=self.monday,
        )

        self.assertEqual(get_required_fte(self.role_fo, self.monday, "MORNING"), 2)

    def test_morning_and_afternoon_are_independent(self):
        CapacityRule.objects.create(
            role=self.role_fo,
            part_of_day="MORNING",
            min_required_fte=2,
            applies_from=self.monday,
            applies_to=self.monday,
        )

        self.assertIsNone(get_required_fte(self.role_fo, self.monday, "AFTERNOON"))

    def test_returns_none_for_a_different_date(self):
        CapacityRule.objects.create(
            role=self.role_fo,
            part_of_day="MORNING",
            min_required_fte=2,
            applies_from=self.monday,
            applies_to=self.monday,
        )

        self.assertIsNone(get_required_fte(self.role_fo, self.week_dates[1], "MORNING"))


class IsUnderstaffedTest(TestCase):
    def setUp(self):
        self.role_fo = Role.objects.get(name="FO")
        self.monday = get_week_dates(2026, 12)[0]

    def test_false_without_a_capacity_rule(self):
        self.assertFalse(is_understaffed(self.role_fo, self.monday, "MORNING", 0))

    def test_true_when_scheduled_count_is_below_the_minimum(self):
        CapacityRule.objects.create(
            role=self.role_fo,
            part_of_day="MORNING",
            min_required_fte=2,
            applies_from=self.monday,
            applies_to=self.monday,
        )

        self.assertTrue(is_understaffed(self.role_fo, self.monday, "MORNING", 1))

    def test_false_when_scheduled_count_meets_the_minimum(self):
        CapacityRule.objects.create(
            role=self.role_fo,
            part_of_day="MORNING",
            min_required_fte=2,
            applies_from=self.monday,
            applies_to=self.monday,
        )

        self.assertFalse(is_understaffed(self.role_fo, self.monday, "MORNING", 2))


class BuildCapacityOverviewTest(TestCase):
    def setUp(self):
        self.role_fo = Role.objects.get(name="FO")
        self.week_dates = get_week_dates(2026, 12)
        self.monday = self.week_dates[0]
        CapacityRule.objects.create(
            role=self.role_fo,
            part_of_day="MORNING",
            min_required_fte=2,
            applies_from=self.monday,
            applies_to=self.monday,
        )

    def _get_cell(self, overview, date, part_of_day):
        role_overview = next(o for o in overview if o["role"] == self.role_fo)
        return next(
            c
            for c in role_overview["cells"]
            if c["date"] == date and c["part_of_day"] == part_of_day
        )

    def test_understaffed_when_no_one_is_scheduled(self):
        overview = build_capacity_overview([], self.week_dates)

        cell = self._get_cell(overview, self.monday, "MORNING")
        self.assertTrue(cell["understaffed"])
        self.assertEqual(cell["scheduled_count"], 0)
        self.assertEqual(cell["required_fte"], 2)

    def test_not_understaffed_when_enough_people_are_scheduled(self):
        planning_rows = [
            {
                "cells": [
                    {
                        "day_of_week": 1,
                        "part_of_day": "MORNING",
                        "date": self.monday,
                        "role": self.role_fo,
                        "on_leave": False,
                    }
                ]
            },
            {
                "cells": [
                    {
                        "day_of_week": 1,
                        "part_of_day": "MORNING",
                        "date": self.monday,
                        "role": self.role_fo,
                        "on_leave": False,
                    }
                ]
            },
        ]

        overview = build_capacity_overview(planning_rows, self.week_dates)

        cell = self._get_cell(overview, self.monday, "MORNING")
        self.assertFalse(cell["understaffed"])
        self.assertEqual(cell["scheduled_count"], 2)

    def test_cell_without_a_configured_minimum_has_required_fte_none(self):
        overview = build_capacity_overview([], self.week_dates)

        cell = self._get_cell(overview, self.monday, "AFTERNOON")
        self.assertIsNone(cell["required_fte"])
        self.assertFalse(cell["understaffed"])
        self.assertEqual(cell["required_fte_option"], "")

    def test_only_active_roles_are_included(self):
        Role.objects.filter(name="FO").update(is_active=False)

        overview = build_capacity_overview([], self.week_dates)

        role_names = [o["role"].name for o in overview]
        self.assertNotIn("FO", role_names)


class SaveCapacityMinimumsTest(TestCase):
    def setUp(self):
        self.role_fo = Role.objects.get(name="FO")
        self.monday = get_week_dates(2026, 12)[0]

    def test_creates_a_capacity_rule_for_the_exact_date_and_part_of_day(self):
        save_capacity_minimums(
            [
                {
                    "role_id": self.role_fo.id,
                    "date": self.monday,
                    "part_of_day": "MORNING",
                    "min_required_fte": 3,
                }
            ]
        )

        rule = CapacityRule.objects.get(
            role=self.role_fo,
            applies_from=self.monday,
            applies_to=self.monday,
            part_of_day="MORNING",
        )
        self.assertEqual(rule.min_required_fte, 3)

    def test_updates_an_existing_rule_for_the_same_date_and_part_of_day(self):
        CapacityRule.objects.create(
            role=self.role_fo,
            part_of_day="MORNING",
            min_required_fte=1,
            applies_from=self.monday,
            applies_to=self.monday,
        )

        save_capacity_minimums(
            [
                {
                    "role_id": self.role_fo.id,
                    "date": self.monday,
                    "part_of_day": "MORNING",
                    "min_required_fte": 4,
                }
            ]
        )

        rule = CapacityRule.objects.get(
            role=self.role_fo,
            applies_from=self.monday,
            applies_to=self.monday,
            part_of_day="MORNING",
        )
        self.assertEqual(rule.min_required_fte, 4)

    def test_empty_value_removes_an_existing_rule(self):
        CapacityRule.objects.create(
            role=self.role_fo,
            part_of_day="MORNING",
            min_required_fte=2,
            applies_from=self.monday,
            applies_to=self.monday,
        )

        save_capacity_minimums(
            [
                {
                    "role_id": self.role_fo.id,
                    "date": self.monday,
                    "part_of_day": "MORNING",
                    "min_required_fte": None,
                }
            ]
        )

        self.assertFalse(
            CapacityRule.objects.filter(
                role=self.role_fo,
                applies_from=self.monday,
                applies_to=self.monday,
                part_of_day="MORNING",
            ).exists()
        )

    def test_morning_and_afternoon_are_saved_independently(self):
        save_capacity_minimums(
            [
                {
                    "role_id": self.role_fo.id,
                    "date": self.monday,
                    "part_of_day": "MORNING",
                    "min_required_fte": 2,
                },
                {
                    "role_id": self.role_fo.id,
                    "date": self.monday,
                    "part_of_day": "AFTERNOON",
                    "min_required_fte": 5,
                },
            ]
        )

        self.assertEqual(
            CapacityRule.objects.get(
                role=self.role_fo,
                applies_from=self.monday,
                applies_to=self.monday,
                part_of_day="MORNING",
            ).min_required_fte,
            2,
        )
        self.assertEqual(
            CapacityRule.objects.get(
                role=self.role_fo,
                applies_from=self.monday,
                applies_to=self.monday,
                part_of_day="AFTERNOON",
            ).min_required_fte,
            5,
        )
