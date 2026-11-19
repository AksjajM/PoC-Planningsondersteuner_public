
from django.conf import settings
from django.db import models


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name}"
    

class UserRole(models.Model):
    """Model representing the assignment of a role to a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="user_assignments",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                name="unique_user_role",
            )
        ]
        ordering = ["user__username", "role__name"]

    def __str__(self) -> str:
        return f"{self.user} - {self.role}"


class DefaultAvailability(models.Model):
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 1, "Maandag"
        TUESDAY = 2, "Dinsdag"
        WEDNESDAY = 3, "Woensdag"
        THURSDAY = 4, "Donderdag"
        FRIDAY = 5, "Vrijdag"
        SATURDAY = 6, "Zaterdag"
        SUNDAY = 7, "Zondag"

    class PartOfDay(models.TextChoices):
        MORNING = "MORNING", "Ochtend"
        AFTERNOON = "AFTERNOON", "Middag"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="default_availabilities",
        verbose_name="Gebruiker",
    )
    day_of_week = models.IntegerField(
        choices=DayOfWeek.choices,
        verbose_name="Dag van de week",
    )
    part_of_day = models.CharField(
        max_length=20,
        choices=PartOfDay.choices,
        verbose_name="Dagdeel",
    )
    role = models.ForeignKey(
        'Role',
        on_delete=models.RESTRICT,
        related_name="default_availabilities",
        verbose_name="Rol",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Standaard beschikbaarheid"
        verbose_name_plural = "Standaard beschikbaarheden"
        unique_together = ("user", "day_of_week", "part_of_day")

    def __str__(self) -> str:
        return f"{self.user} - {self.get_day_of_week_display()} ({self.get_part_of_day_display()}): {self.role.name}"


class AvailabilityException(models.Model):
    """Tijdelijke afwijking op de standaardbeschikbaarheid voor een specifieke datum."""

    class PartOfDay(models.TextChoices):
        MORNING = "MORNING", "Ochtend"
        AFTERNOON = "AFTERNOON", "Middag"

    class Reason(models.TextChoices):
        SICK = "SICK", "Ziek"
        PAID_LEAVE = "PAID_LEAVE", "Betaald verlof"
        AVAILABILITY_EXCEPTION = "EXCEPTION", "Availability exception"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availability_exceptions",
        verbose_name="Gebruiker",
    )
    date = models.DateField(
        verbose_name="Datum",
    )
    role = models.ForeignKey(
        'Role',
        on_delete=models.RESTRICT,
        related_name="availability_exceptions",
        verbose_name="Rol",
        null=True,
        blank=True,
    )
    part_of_day = models.CharField(
        max_length=20,
        choices=PartOfDay.choices,
        verbose_name="Dagdeel",
    )
    is_available = models.BooleanField(
        verbose_name="Is beschikbaar",
    )
    reason = models.CharField(
        max_length=20,
        choices=Reason.choices,
        verbose_name="Reden",
    )
    note = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Toelichting",
    )

    class Meta:
        verbose_name = "Beschikbaarheidsuitzondering"
        verbose_name_plural = "Beschikbaarheidsuitzonderingen"
        unique_together = ("user", "date", "part_of_day")
        ordering = ["user__username", "date", "part_of_day"]

    def __str__(self) -> str:
        status = "Beschikbaar" if self.is_available else "Niet beschikbaar"
        return f"{self.user} - {self.date} ({self.get_part_of_day_display()}): {status} ({self.get_reason_display()})"


class VacationRequest(models.Model):
    """Verlofaanvraag van een gebruiker voor een aaneengesloten periode."""

    class PlanningStatus(models.TextChoices):
        APPROVED = "APPROVED", "Goedgekeurd"
        DECLINED = "DECLINED", "Afgewezen"
        PENDING = "PENDING", "In behandeling"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vacation_requests",
        verbose_name="Gebruiker",
    )
    start_date = models.DateField(
        verbose_name="Startdatum",
    )
    end_date = models.DateField(
        verbose_name="Einddatum",
    )
    planning_status = models.CharField(
        max_length=20,
        choices=PlanningStatus.choices,
        default=PlanningStatus.PENDING,
        verbose_name="Status",
    )
    note = models.CharField(
        max_length=255,
        blank=True,
        default="Paid leave",
        verbose_name="Notitie",
    )
    created_on = models.DateField(
        auto_now_add=True,
        verbose_name="Aangemaakt op",
    )

    class Meta:
        verbose_name = "Verlofaanvraag"
        verbose_name_plural = "Verlofaanvragen"
        ordering = ["user__username", "start_date"]

    def __str__(self) -> str:
        return f"{self.user} - {self.start_date} t/m {self.end_date} ({self.get_planning_status_display()})"


class CapacityRule(models.Model):
    """Minimaal vereiste personeelsbezetting (FTE) voor een rol binnen een geldigheidsperiode."""

    class PartOfDay(models.TextChoices):
        MORNING = "MORNING", "Ochtend"
        AFTERNOON = "AFTERNOON", "Middag"

    role = models.ForeignKey(
        Role,
        on_delete=models.RESTRICT,
        related_name="capacity_rules",
        verbose_name="Rol",
    )
    part_of_day = models.CharField(
        max_length=20,
        choices=PartOfDay.choices,
        verbose_name="Dagdeel",
    )
    min_required_fte = models.PositiveIntegerField(
        verbose_name="Minimaal vereiste FTE",
    )
    applies_from = models.DateField(
        verbose_name="Geldig vanaf",
    )
    applies_to = models.DateField(
        verbose_name="Geldig tot",
    )

    class Meta:
        verbose_name = "Capaciteitsregel"
        verbose_name_plural = "Capaciteitsregels"
        unique_together = ("role", "applies_from", "applies_to", "part_of_day")
        ordering = ["role__name", "applies_from", "part_of_day"]

    def __str__(self) -> str:
        return (
            f"{self.role} - {self.get_part_of_day_display()} min {self.min_required_fte} FTE "
            f"({self.applies_from} t/m {self.applies_to})"
        )


class WeeklyPlanning(models.Model):
    """Door de planner vastgestelde planning voor een specifieke week.

    Overschrijft de standaardbeschikbaarheid van een medewerker voor die week,
    maar niet een goedgekeurde vakantieaanvraag.
    """

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 1, "Maandag"
        TUESDAY = 2, "Dinsdag"
        WEDNESDAY = 3, "Woensdag"
        THURSDAY = 4, "Donderdag"
        FRIDAY = 5, "Vrijdag"

    class PartOfDay(models.TextChoices):
        MORNING = "MORNING", "Ochtend"
        AFTERNOON = "AFTERNOON", "Middag"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_plannings",
        verbose_name="Gebruiker",
    )
    year = models.IntegerField(
        verbose_name="Jaar",
    )
    week_number = models.IntegerField(
        verbose_name="Weeknummer",
    )
    day_of_week = models.IntegerField(
        choices=DayOfWeek.choices,
        verbose_name="Dag van de week",
    )
    part_of_day = models.CharField(
        max_length=20,
        choices=PartOfDay.choices,
        verbose_name="Dagdeel",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.RESTRICT,
        related_name="weekly_plannings",
        verbose_name="Rol",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Weekplanning"
        verbose_name_plural = "Weekplanningen"
        unique_together = ("user", "year", "week_number", "day_of_week", "part_of_day")
        ordering = ["year", "week_number", "user__username", "day_of_week", "part_of_day"]

    def __str__(self) -> str:
        role_name = self.role.name if self.role else "-"
        return (
            f"{self.user} - {self.year} week {self.week_number} "
            f"{self.get_day_of_week_display()} ({self.get_part_of_day_display()}): {role_name}"
        )
