"""Merge the capacity and availability-exception migration branches."""

from django.db import migrations


class Migration(migrations.Migration):
    """Record that both independent migration branches have been applied."""

    dependencies = [
        ("planning", "0012_alter_capacityrule_min_required_fte"),
        ("planning", "0013_rename_availability_exception_note_prefix"),
    ]

    operations = []
