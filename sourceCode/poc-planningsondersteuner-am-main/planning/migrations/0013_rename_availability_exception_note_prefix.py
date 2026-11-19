from django.db import migrations


OLD_PREFIX = "Availability exception: "
NEW_PREFIX = "Availability exception ingevoerd door medewerker: "


def rename_note_prefix(apps, schema_editor):
    """Vervangt de oude vaste prefix in bestaande medewerkersuitzonderingen."""
    availability_exception = apps.get_model("planning", "AvailabilityException")
    for exception in availability_exception.objects.filter(note__startswith=OLD_PREFIX):
        exception.note = f"{NEW_PREFIX}{exception.note.removeprefix(OLD_PREFIX)}"
        exception.save(update_fields=["note"])


class Migration(migrations.Migration):

    dependencies = [
        ("planning", "0012_availabilityexception_note_and_more"),
    ]

    operations = [
        migrations.RunPython(rename_note_prefix, migrations.RunPython.noop),
    ]
