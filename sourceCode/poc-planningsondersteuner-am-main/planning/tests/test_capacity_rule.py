from django.test import TestCase

from planning.models import CapacityRule, Role


class CapacityRuleModelTest(TestCase):
    def setUp(self):
        self.role_fo = Role.objects.get(name="FO")

    def test_create_capacity_rule(self):
        rule = CapacityRule.objects.create(
            role=self.role_fo,
            part_of_day=CapacityRule.PartOfDay.MORNING,
            min_required_fte=2,
            applies_from="2026-01-01",
            applies_to="2026-12-31",
        )
        self.assertEqual(rule.role, self.role_fo)
        self.assertEqual(rule.part_of_day, "MORNING")
        self.assertEqual(rule.min_required_fte, 2)
        self.assertEqual(str(rule.applies_from), "2026-01-01")
        self.assertEqual(str(rule.applies_to), "2026-12-31")
        self.assertIn("FO", str(rule))
        self.assertIn("Ochtend", str(rule))
        self.assertIn("2", str(rule))

    def test_role_can_have_multiple_capacity_rules(self):
        CapacityRule.objects.create(
            role=self.role_fo,
            part_of_day=CapacityRule.PartOfDay.MORNING,
            min_required_fte=2,
            applies_from="2026-01-01",
            applies_to="2026-06-30",
        )
        CapacityRule.objects.create(
            role=self.role_fo,
            part_of_day=CapacityRule.PartOfDay.MORNING,
            min_required_fte=3,
            applies_from="2026-07-01",
            applies_to="2026-12-31",
        )

        self.assertEqual(self.role_fo.capacity_rules.count(), 2)

    def test_same_date_can_have_separate_morning_and_afternoon_rules(self):
        CapacityRule.objects.create(
            role=self.role_fo,
            part_of_day=CapacityRule.PartOfDay.MORNING,
            min_required_fte=2,
            applies_from="2026-03-16",
            applies_to="2026-03-16",
        )
        CapacityRule.objects.create(
            role=self.role_fo,
            part_of_day=CapacityRule.PartOfDay.AFTERNOON,
            min_required_fte=3,
            applies_from="2026-03-16",
            applies_to="2026-03-16",
        )

        self.assertEqual(self.role_fo.capacity_rules.count(), 2)
