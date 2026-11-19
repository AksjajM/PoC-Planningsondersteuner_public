from django.contrib import admin
from planning.models import (
    Role,
    UserRole,
    DefaultAvailability,
    AvailabilityException,
    VacationRequest,
    CapacityRule,
    WeeklyPlanning,
)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Adminbeheer voor planbare supportrollen."""

    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    ordering = ("name",)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """Adminbeheer voor koppelingen tussen gebruikers en planbare rollen."""

    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "role__name",
    )
    autocomplete_fields = ("user", "role")
    ordering = ("user__username", "role__name")


@admin.register(DefaultAvailability)
class DefaultAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("user", "day_of_week", "part_of_day", "role")
    list_filter = ("day_of_week", "part_of_day", "role")
    search_fields = ("user__username", "user__first_name", "user__last_name")
    ordering = ("user", "day_of_week", "part_of_day")


@admin.register(AvailabilityException)
class AvailabilityExceptionAdmin(admin.ModelAdmin):
    list_display = (
        "user", "date", "part_of_day", "role", "is_available", "reason", "note"
    )
    list_filter = ("part_of_day", "role", "is_available", "reason")
    search_fields = ("user__username", "user__first_name", "user__last_name", "note")
    ordering = ("user", "date", "part_of_day")


@admin.register(VacationRequest)
class VacationRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "start_date", "end_date", "planning_status")
    list_filter = ("planning_status",)
    search_fields = ("user__username", "user__first_name", "user__last_name")
    ordering = ("user", "start_date")


@admin.register(CapacityRule)
class CapacityRuleAdmin(admin.ModelAdmin):
    list_display = ("role", "min_required_fte", "applies_from", "applies_to")
    list_filter = ("role",)
    search_fields = ("role__name",)
    ordering = ("role__name", "applies_from")


@admin.register(WeeklyPlanning)
class WeeklyPlanningAdmin(admin.ModelAdmin):
    list_display = ("user", "year", "week_number", "day_of_week", "part_of_day", "role")
    list_filter = ("year", "week_number", "day_of_week", "part_of_day", "role")
    search_fields = ("user__username", "user__first_name", "user__last_name")
    ordering = ("year", "week_number", "user__username", "day_of_week", "part_of_day")
