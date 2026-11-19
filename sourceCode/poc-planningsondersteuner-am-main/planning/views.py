import datetime
import csv

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from .forms import (
    AvailabilityExceptionNoteForm,
    DefaultAvailabilityForm,
    VacationRequestForm,
)
from .models import Role, VacationRequest
from .services import (
    apply_action_to_requests,
    apply_submitted_roles,
    build_approval_request_overview,
    build_availability_exception_week,
    build_capacity_overview,
    build_weekly_planning_csv_rows,
    create_vacation_request,
    build_employee_week_overview,
    build_planning_table,
    build_readonly_weekly_planning,
    CSV_HEADERS,
    get_employees,
    get_next_iso_week,
    get_planning_employees,
    get_user_vacation_request_groups,
    get_vacation_conflict_summary,
    get_week_dates,
    parse_capacity_input,
    parse_availability_exception_input,
    parse_planning_input,
    save_capacity_minimums,
    save_availability_exceptions,
    save_weekly_planning,
    validate_year_week,
)


@login_required
def planning_home(request):
    """PLON-119: toont readonly opgeslagen weekplanning op het dashboard."""
    today = datetime.date.today()
    current_year, current_week, _day = today.isocalendar()
    input_year = request.GET.get("year", str(current_year))
    input_week = request.GET.get("week", str(current_week))
    year, week_number, validation_error = validate_year_week(
        input_year,
        input_week,
        language="en",
    )
    if validation_error:
        year, week_number = current_year, current_week

    users = get_planning_employees()
    week_dates, planning_rows = build_readonly_weekly_planning(
        year,
        week_number,
        users,
    )
    next_year, next_week = get_next_iso_week(current_year, current_week)

    return render(
        request,
        "planning/home.html",
        {
            "year": year,
            "week_number": week_number,
            "week_dates": week_dates,
            "planning_rows": planning_rows,
            "validation_error": validation_error,
            "current_year": current_year,
            "current_week": current_week,
            "next_year": next_year,
            "next_week": next_week,
        },
    )


@login_required
def availability(request):
    """PLON-25: formulier voor standaardbeschikbaarheid."""
    if request.user.is_staff and not request.user.is_superuser:
        raise PermissionDenied

    if request.method == "POST":
        form = DefaultAvailabilityForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Standaardbeschikbaarheid opgeslagen.")
            return redirect("planning:availability")
    else:
        form = DefaultAvailabilityForm(user=request.user)

    return render(
        request,
        "planning/availability.html",
        {
            "form": form,
            "page_title": "Standaardbeschikbaarheid",
        },
    )


@login_required
def absence(request):
    """PLON-54: laat medewerkers tijdelijke beschikbaarheidsafwijkingen beheren."""
    if request.user.is_staff and not request.user.is_superuser:
        raise PermissionDenied

    today = datetime.date.today()
    iso_year, iso_week, _iso_day = today.isocalendar()
    validation_error = None
    assignments = []

    if request.method == "POST":
        input_year = request.POST.get("year", str(iso_year))
        input_week = request.POST.get("week_number", str(iso_week))
        year, week_number, validation_error = validate_year_week(
            input_year,
            input_week,
            language="en",
        )
        form = AvailabilityExceptionNoteForm(request.POST)

        if not validation_error:
            week_dates = get_week_dates(year, week_number)
            try:
                assignments = parse_availability_exception_input(request.POST)
                if form.is_valid():
                    changed_count = save_availability_exceptions(
                        request.user,
                        week_dates,
                        assignments,
                        form.cleaned_data["note"],
                    )
                    if changed_count:
                        messages.success(
                            request,
                            "Availability exception saved.",
                        )
                        return redirect(
                            f"{reverse('planning:absence')}?year={year}&week={week_number}"
                        )
                    form.add_error(None, "Change at least one part of the day before saving.")
            except ValueError as error:
                form.add_error(None, str(error))
    else:
        input_year = request.GET.get("year", str(iso_year))
        input_week = request.GET.get("week", str(iso_week))
        year, week_number, validation_error = validate_year_week(
            input_year,
            input_week,
            language="en",
        )
        form = AvailabilityExceptionNoteForm()

    if validation_error:
        year, week_number = iso_year, iso_week

    week_dates = get_week_dates(year, week_number)
    cells = build_availability_exception_week(request.user, week_dates)
    if assignments:
        apply_submitted_roles(cells, assignments)

    return render(
        request,
        "planning/availability_exception.html",
        {
            "form": form,
            "year": year,
            "week_number": week_number,
            "input_year": input_year,
            "input_week": input_week,
            "validation_error": validation_error,
            "current_year": iso_year,
            "current_week": iso_week,
            "week_dates": week_dates,
            "cells": cells,
            "roles": Role.objects.all(),
            "page_title": "Employee exceptions",
        },
    )


@login_required
def week_overview(request):
    """PLON-26: View voor beschikbaarheidsoverzicht maken (Employee Dashboard)."""
    if request.user.is_staff and not request.user.is_superuser:
        raise PermissionDenied

    current_year = datetime.date.today().year
    current_week_num = datetime.date.today().isocalendar()[1]
    weeks_data = build_employee_week_overview(
        request.user,
        current_year,
        current_week_num,
    )

    return render(
        request,
        "planning/week_overview.html",
        {
            "weeks_data": weeks_data,
            "page_title": "Week overview",
        },
    )


@login_required
def vacation_request(request):
    """PLON-38: aanvraagformulier voor vakantieaanvragen."""
    if request.user.is_staff and not request.user.is_superuser:
        raise PermissionDenied

    if request.method == "POST":
        form = VacationRequestForm(request.POST)
        if form.is_valid():
            conflict_summary = get_vacation_conflict_summary(
                form.cleaned_data["start_date"],
                form.cleaned_data["end_date"],
                exclude_user_id=request.user.id,
            )
            create_vacation_request(
                request.user,
                form.cleaned_data["start_date"],
                form.cleaned_data["end_date"],
            )
            messages.success(request, "Vakantieaanvraag ingediend.")
            if conflict_summary["has_conflict"]:
                messages.warning(
                    request,
                    "Let op: je aanvraag overlapt met "
                    f"{conflict_summary['total']} actieve aanvraag/aanvragen "
                    f"({conflict_summary['approved_count']} goedgekeurd, "
                    f"{conflict_summary['pending_count']} in behandeling).",
                )
            return redirect("planning:vacation_request")
    else:
        form = VacationRequestForm()

    request_groups = get_user_vacation_request_groups(request.user)

    return render(
        request,
        "planning/vacation_request.html",
        {
            "form": form,
            **request_groups,
            "page_title": "Vacation request",
        },
    )


@login_required
def approve_requests(request):
    """PLON-39: overzicht voor planners/admins om vakantieaanvragen goed of af te keuren."""
    if not request.user.is_staff:
        raise PermissionDenied

    if request.method == "POST":
        action = request.POST.get("action")
        selected_ids = request.POST.getlist("selected_requests")

        if apply_action_to_requests(action, selected_ids):
            messages.success(request, "Vakantieaanvragen bijgewerkt.")

        return redirect("planning:approve_requests")

    selected_user = request.GET.get("user", "")

    request_overview = build_approval_request_overview(selected_user)

    return render(
        request,
        "planning/approve_requests.html",
        {
            **request_overview,
            "request_groups": [
                ("Pending requests", request_overview["pending_requests"], True),
                ("Approved requests", request_overview["approved_requests"], True),
                ("Declined requests", request_overview["declined_requests"], False),
            ],
            "users": get_employees(),
            "selected_user": selected_user,
            "page_title": "Approve requests",
        },
    )


@login_required
def planner_dashboard(request):
    """PLON-41: capaciteits- en planningsdashboard voor planners/admins."""
    if not request.user.is_staff:
        raise PermissionDenied

    today = datetime.date.today()
    iso_year, iso_week, _ = today.isocalendar()
    validation_error = None

    if request.method == "POST":
        input_year = request.POST.get("year", str(iso_year))
        input_week = request.POST.get("week_number", str(iso_week))
        year, week_number, validation_error = validate_year_week(input_year, input_week)
        if not validation_error:
            post_week_dates = get_week_dates(year, week_number)
            save_capacity_minimums(parse_capacity_input(request.POST, post_week_dates))
            save_weekly_planning(year, week_number, parse_planning_input(request.POST))

            messages.success(request, "Planning en capaciteit opgeslagen.")
            return redirect(f"{reverse('planning:planner_dashboard')}?year={year}&week={week_number}")
    else:
        input_year = request.GET.get("year", str(iso_year))
        input_week = request.GET.get("week", str(iso_week))
        year, week_number, validation_error = validate_year_week(input_year, input_week)

    if validation_error:
        year, week_number = iso_year, iso_week

    week_dates = get_week_dates(year, week_number)
    planning_rows = build_planning_table(year, week_number)
    capacity_overview = build_capacity_overview(planning_rows, week_dates)

    return render(
        request,
        "planning/planner_dashboard.html",
        {
            "year": year,
            "week_number": week_number,
            "input_year": input_year,
            "input_week": input_week,
            "validation_error": validation_error,
            "current_year": iso_year,
            "current_week": iso_week,
            "week_dates": week_dates,
            "planning_rows": planning_rows,
            "capacity_overview": capacity_overview,
            "roles": Role.objects.filter(is_active=True),
            "capacity_options": range(0, 11),
            "page_title": "Planner dashboard",
        },
    )


@login_required
def export_weekly_planning_csv(request):
    """PLON-62: exports saved weekly planning for planners and admins."""
    if not request.user.is_staff:
        raise PermissionDenied

    today = datetime.date.today()
    current_year, current_week, _day = today.isocalendar()
    input_year = request.GET.get("year", str(current_year))
    input_week = request.GET.get("week", str(current_week))
    year, week_number, validation_error = validate_year_week(input_year, input_week)
    if validation_error:
        return HttpResponseBadRequest(validation_error)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="weekly-planning-{year}-week-{week_number}.csv"'
    )
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(CSV_HEADERS)
    writer.writerows(build_weekly_planning_csv_rows(year, week_number))
    return response
